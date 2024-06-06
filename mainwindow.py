import sys
import configparser
import requests
import subprocess
import os
import ctypes

from steam_web_api import Steam as steam_api
from PIL import Image
from PIL.ImageQt import ImageQt
from winotify import Notification
from ctypes import wintypes

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QSystemTrayIcon, QMenu, QSizePolicy, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage, QCursor, QIcon, QAction
from PySide6.QtCore import QThread, Signal, QRect, Qt, QSize, QTimer

from Steam import Steam
from Epic import Epic
from database import Database

from layout.ui_form import Ui_MainWindow
from layout.FlowLayout import FlowLayout
from layout.RichTextPushButton import RichTextPushButton
from layout.CircularAvatar import mask_image
from desktop_widget import DesktopWidget

# Windows taskbar and task manager process name config
myappid = u'GamesVault_v1.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
kernel32.SetConsoleTitleW.restype = wintypes.BOOL
kernel32.SetConsoleTitleW("Games Vault")


# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']


class MainWindow(QMainWindow):

    steam = steam_api(STEAM_API_KEY)
    container_id = 0
    games = None
    threads = []
    installed_games_providers = []

    def __init__(self, parent=None):
        super().__init__(parent)

        # Connect database
        self.database = Database()

        # Initialize gui
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.flow_layout_recent_games = FlowLayout(self.ui.Steam_recent_games)
        self.flow_layout_installed_games = FlowLayout(self.ui.Installed_games_content)
        self.flow_layout_owned_games = FlowLayout(self.ui.Owned_games_content)

        self.change_steam_id = RichTextPushButton()
        self.change_steam_id.setFlat(True)
        self.change_steam_id.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.change_steam_id.setStyleSheet("color: rgb(255, 255, 255); font-size: 28px")
        self.change_steam_id.setText("Recent Games <span style='font-size: 12px; color: rgb(0, 255, 0);'>change steamID</span>")
        self.change_steam_id.setObjectName("change_steam_id_2")
        self.change_steam_id.setCursor(Qt.PointingHandCursor)

        self.ui.change_steam_id_container.layout().addWidget(self.change_steam_id)

        self.ui.tabWidget.setStyleSheet("""
            QTabBar::tab {
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 5px;
                margin: 5px;
            }

            QTabBar::tab:hover {
                background: darkgray;
            }

            QTabBar::tab:selected {
                background: rgba(0, 255, 0, 0);
                color: rgb(0, 255, 0);
            };
        """)

        # Desktop Widget
        # self.desktop_widget = DesktopWidget()
        # self.desktop_widget.show()
        # self.ui.installed_games_quantity.hide()
        # self.desktop_widget.ui.centralwidget.layout().addWidget(self.ui.installed_games_container)

        if self.database.conn:
            sql_user = "SELECT steam_id FROM User WHERE id = 1"
            user_info = self.database.execute_query(self.database.conn, sql_user).fetchone()
            steamid = user_info[0]

            if steamid != 0:
                self.timer_5min = QTimer()
                self.timer_5min.timeout.connect(self.RefreshRecentGames)
                self.timer_5min.start((5 * 60 * 1000)) # Refresh every 5 minutes

                self.timer_1sec = QTimer()
                self.timer_1sec.timeout.connect(self.UpdateRecentGamesRefreshTimer)
                self.timer_1sec.start(1000)


        # System tray menu and app icon
        self.tray_icon = QSystemTrayIcon()
        app_icon = QIcon(":/icons/resources\icons/app_icon.png")

        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("Games Vault")

        self.tray_menu = QMenu()
        self.restore_action = QAction("Open", self)
        self.hide_action = QAction("Hide", self)
        self.quit_action = QAction("Quit", self)

        self.tray_menu.setStyleSheet("QMenu::item { height: 50px; }")

        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.restore_action)
        self.tray_menu.addAction(self.hide_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)

        self.setWindowIcon(app_icon)


        # Initialize objects
        self.Steam = Steam()
        self.Epic = Epic()


        # Initialize buttons and actions
        self.ui.find_epic_games_directory.clicked.connect(lambda: self.Epic.FindEpicGames_Games(self))
        self.ui.find_steam_directory.clicked.connect(lambda: self.Steam.FindSteamGames(self))
        self.change_steam_id.clicked.connect(lambda: self.Steam.ChangeSteamID(self))
        self.ui.user_total_playtime.mousePressEvent = self.ChangeUserTotalPlaytimeDisplayMode

        self.ui.set_img_cover_width.valueChanged.connect(self.SetImageCoverWidth)
        self.ui.set_img_cover_width.sliderReleased.connect(lambda: self.UpdateImageCoverWidthInDatabase(self.ui.set_img_cover_width))

        self.ui.set_img_cover_width_owned.valueChanged.connect(self.SetImageCoverWidth)
        self.ui.set_img_cover_width_owned.sliderReleased.connect(lambda: self.UpdateImageCoverWidthInDatabase(self.ui.set_img_cover_width_owned))


        self.ui.search_games.textChanged.connect(self.SearchGameOnTextChanged)
        self.ui.search_games_owned.textChanged.connect(self.SearchGameOnTextChanged)

        self.tray_icon.activated.connect(self.ShowNormal)
        self.restore_action.triggered.connect(self.ShowNormal)
        self.hide_action.triggered.connect(self.HideApplication)
        self.quit_action.triggered.connect(self.QuitApplication)
        self.tray_icon.show()

        # Run checks on database items
        self.CheckDb()


    # System tray menu
    def closeEvent(self, event):
        event.ignore()
        self.hide()


    def ShowNormal(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == False:
            self.show()

        elif reason == QSystemTrayIcon.Context:
            pass


    def HideApplication(self):
        self.hide()


    def QuitApplication(self):
        QApplication.instance().quit()


    # GUI
    def resizeEvent(self, event):
        self.ui.search_widget_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.width_slider_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.search_widget_container_2.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.width_slider_container_2.setMaximumWidth((self.ui.centralwidget.width()/3)+15)

        try:
            if self.ui.Owned_games_content.children()[1].objectName() == "info_label":
                self.ui.Owned_games_content.children()[1].setMinimumHeight(self.ui.centralwidget.height()-125)
        except Exception:
            pass


    def UpdateRecentGamesRefreshTimer(self):
        total_seconds = self.timer_5min.remainingTime() // 1000
        minutes = int(self.timer_5min.remainingTime() // 60000)
        seconds = total_seconds % 60

        self.ui.recent_games_refresh_info.setText(f"Refresh in: {minutes}:{seconds}m")


    def RefreshRecentGames(self):
        if self.database.conn:
            sql_user = "SELECT steam_id FROM User WHERE id = 1"
            user_info = self.database.execute_query(self.database.conn, sql_user).fetchone()
            steamid = user_info[0]
            self.UpdateRecentGamesGUI(self.Steam.FetchRecentSteamGames(self, steamid))

    def ChangeUserTotalPlaytimeDisplayMode(self, event):
        if self.database.conn:
            try:
                query = "SELECT total_user_playtime_in_minutes FROM User WHERE id = 1"
                result = self.database.execute_query(self.database.conn, query).fetchone()
                total_user_playtime_in_minutes = result[0]
                display_modes = [(f"Total playtime: {total_user_playtime_in_minutes//60}h {total_user_playtime_in_minutes%60}m"), (f"Total playtime: {total_user_playtime_in_minutes//1440} days")]

                i = 0

                while self.ui.user_total_playtime.text() == display_modes[i]:
                    i += 1

                self.ui.user_total_playtime.setText(display_modes[i])
            except Exception as e:
                print(e)



    def SearchGameOnTextChanged(self, text):
        sender = self.sender().objectName()

        if sender == "search_games":
            games = self.ui.Installed_games_content.children()[1:]
        elif sender == "search_games_owned":
            games = self.ui.Owned_games_content.children()[1:]

        for game in games:
            if text.lower() not in (game.objectName()).lower():
                game.hide()
            else:
                game.show()


    def SetImageCoverWidth(self, value, from_db=None):
        fit_width = value

        if self.sender() or from_db:
            try:
                sender = self.sender().objectName()
            except Exception:
                sender = None

            if sender == "set_img_cover_width" or from_db == "set_img_cover_width":
                games = self.ui.Installed_games_content.children()
                self.ui.img_cover_width_info.setText(f'{value}px')

                for game in games:
                    if game.children():
                        game.setProperty('minimumWidth', fit_width)
                        game.setProperty('maximumWidth', fit_width)
                        game.children()[0].setProperty('minimumWidth', fit_width)
                        game.children()[0].setProperty('maximumWidth', fit_width)

                        game.children()[0].setProperty('minimumHeight', fit_width*1.5)
                        game.children()[0].setProperty('maximumHeight', fit_width*1.5)
                        game.setProperty('minimumHeight', fit_width*1.5)
                        game.setProperty('maximumHeight', fit_width*1.5)


                        game.children()[1].setProperty('geometry', QRect( 0, 0, game.children()[0].property('width'), game.children()[0].property('height')) )
                        game.children()[1].children()[0].setProperty('geometry', QRect( 0, 0, game.children()[0].property('width'), game.children()[0].property('height')) )

                        font = game.children()[1].font()
                        font.setPointSize(fit_width/10)
                        game.children()[0].setFont(font)
                        game.children()[1].setFont(font)

            elif sender == "set_img_cover_width_owned" or from_db == "set_img_cover_width_owned":
                games = self.ui.Owned_games_content.children()
                self.ui.img_cover_width_info_owned.setText(f'{value}px')

                for game in games:
                    if game.children():
                        game.setProperty('minimumWidth', fit_width)
                        game.setProperty('maximumWidth', fit_width)
                        game.children()[1].setProperty('maximumWidth', fit_width)



    def UpdateImageCoverWidthInDatabase(self, slider):
        if self.database.conn:
            if slider.objectName() == "set_img_cover_width":
                sql = "UPDATE user SET game_cover_img = ? WHERE id = 1;"
                self.database.execute_query(self.database.conn, sql, [slider.value()])

            elif slider.objectName() == "set_img_cover_width_owned":
                sql = "UPDATE user SET owned_game_cover_img = ? WHERE id = 1;"
                self.database.execute_query(self.database.conn, sql, [slider.value()])



    def UpdateRecentGamesGUI(self, game_icon_urls):
        for url_and_appid in game_icon_urls:
            try:
                image =  Image.open(requests.get(url_and_appid[0], stream=True).raw)
                q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)
            except Exception:
                q_image = None

            fit_width = 185
            container = QWidget()
            label = QLabel(container)
            btn_label = QLabel(container)
            play_button = QPushButton(btn_label)

            if q_image:
                pixmap = QPixmap.fromImage(q_image)
                label.setPixmap(pixmap)
            else:
                label.setAlignment(Qt.AlignCenter)
                font = label.font()
                font.setPointSize(fit_width/10)
                label.setFont(font)
                label.setWordWrap(True)
                label.setText(f'{url_and_appid[2]}')
                label.setStyleSheet("background-color: rgb(42, 42, 42);")


            container.setObjectName(f"{url_and_appid[2].encode().decode('unicode-escape')}")
            container.setFixedSize(fit_width, fit_width*1.5)

            label.setMinimumWidth(fit_width)
            label.setMinimumHeight(fit_width*1.5)
            label.setMaximumWidth(fit_width)
            label.setMaximumHeight(fit_width*1.5)
            label.setBaseSize(fit_width, fit_width*1.5)
            label.setScaledContents(True)

            play_button.setObjectName(f'play_button recent{self.container_id}')
            play_button.setProperty('geometry', QRect( 0, 0, fit_width, fit_width*1.5) )
            play_button.setFont('Inter')
            play_button.setCursor(QCursor(Qt.PointingHandCursor))
            play_button.setStyleSheet(
            """
                QPushButton {
                    background-color: rgba(0, 0, 0, 0);
                    color: transparent;
                }

                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.8);
                    color: transparent;
                }

            """
            )
            btn_label.setProperty('geometry', QRect( 0, 0, fit_width, fit_width*1.5) )
            btn_label.setAlignment(Qt.AlignCenter)
            btn_label.setWordWrap(True)
            font = label.font()
            font.setPointSize(fit_width/8)
            btn_label.setFont(font)
            btn_label.setText(f"▶\n{url_and_appid[2].encode().decode('unicode-escape')}")
            btn_label.setStyleSheet(
            """
                QLabel {
                    background-color: rgba(0, 0, 0, 0);
                    color: transparent;
                }
                QLabel:hover {
                    background-color: rgba(0, 0, 0, 0.5);
                    color: rgb(60, 255, 0);
                }

                QLabel:pressed {
                    background-color: rgba(0, 0, 0, 0.8);
                    color: transparent;
                }

            """
            )
            font = self.tray_menu.font()
            font.setPointSize(12)
            self.play_game = QAction(f"{url_and_appid[2]}", self)
            self.play_game.setFont(font)
            self.tray_menu.insertAction(self.tray_menu.actions()[0], self.play_game)
            self.play_game.triggered.connect(lambda sacrificial="", appid=url_and_appid[1], appname=url_and_appid[2]: self.LaunchGame(appid, appname, provider='steam'))
            play_button.clicked.connect(lambda sacrificial="", appid=url_and_appid[1], appname=url_and_appid[2]: self.LaunchGame(appid, appname, provider='steam'))

            url_and_appid.clear()
            self.ui.Steam_recent_games.layout().addWidget(container)
            self.ui.Steam_recent_games.update()


    def AddGameToGUI(self, launch_id, app_name, provider, image, *args):
        try:
            container = QWidget()
            label = QLabel(container)
            btn_label = QLabel(container)
            play_button = QPushButton(btn_label)
            fit_width = self.ui.set_img_cover_width.value()

            if image:
                q_image = QImage(image, 200, 500, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                label.setPixmap(pixmap)
            else:
                label.setAlignment(Qt.AlignCenter)
                font = label.font()
                font.setPointSize(fit_width/10)
                label.setFont(font)
                label.setWordWrap(True)
                label.setText(f'{app_name}')
                label.setStyleSheet("background-color: rgb(42, 42, 42);")

            container.setObjectName(f"{app_name.encode().decode('unicode-escape')}")
            container.setFixedSize(fit_width, fit_width*1.5)

            label.setMinimumWidth(fit_width)
            label.setMinimumHeight(fit_width*1.5)
            label.setMaximumWidth(fit_width)
            label.setMaximumHeight(fit_width*1.5)
            label.setBaseSize(fit_width, fit_width*1.5)
            label.setScaledContents(True)

            play_button.setObjectName(f'play_button {self.container_id}')
            play_button.setProperty('geometry', QRect( 0, 0, fit_width, fit_width*1.5) )
            play_button.setFont('Inter')
            play_button.setCursor(QCursor(Qt.PointingHandCursor))
            play_button.setStyleSheet(
            """
                QPushButton {
                    background-color: rgba(0, 0, 0, 0);
                    color: transparent;
                }

                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.8);
                    color: transparent;
                }

            """
            )
            btn_label.setProperty('geometry', QRect( 0, 0, fit_width, fit_width*1.5) )
            btn_label.setAlignment(Qt.AlignCenter)
            btn_label.setWordWrap(True)
            font = label.font()
            font.setPointSize(fit_width/8)
            btn_label.setFont(font)
            btn_label.setText(f"▶\n{app_name.encode().decode('unicode-escape')}")
            btn_label.setStyleSheet(
            """
                QLabel {
                    background-color: rgba(0, 0, 0, 0);
                    color: transparent;
                }
                QLabel:hover {
                    background-color: rgba(0, 0, 0, 0.5);
                    color: rgb(60, 255, 0);
                }

                QLabel:pressed {
                    background-color: rgba(0, 0, 0, 0.8);
                    color: transparent;
                }

            """
            )
            play_button.clicked.connect(lambda: self.LaunchGame(launch_id, app_name, provider))

            self.ui.Installed_games_content.layout().addWidget(container)

            if provider.capitalize() not in self.installed_games_providers:
                self.installed_games_providers.append(provider.capitalize())

            providers_text = ' + '.join(self.installed_games_providers)

            self.ui.installed_games_quantity.setText(f'{len(self.ui.Installed_games_content.children())-1} Games ({providers_text})')

        except Exception:
            pass


    def AddGameToGUI_Owned(self, launch_id, app_name, provider, image, playtime, *args):
        container = QWidget()
        container.setLayout(QHBoxLayout())
        label = QPushButton()
        container.layout().addWidget(label)

        if image:
            q_image = QImage(image, 32, 32, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            label.setIcon(QIcon(pixmap))
            label.setIconSize(QSize(32,32))

        font = label.font()
        font.setPointSize(12)
        label.setFont(font)

        if playtime == None:
            playtime = 0
        label.setText(f" {app_name}\n 🕑{playtime//60}h")
        label.setToolTip(app_name)
        container.setObjectName(f"{app_name.encode().decode('unicode-escape')}")

        label.setStyleSheet(
            """
                QPushButton {
                    text-align:left;
                }
                QPushButton:pressed {
                    color: rgb(0, 255, 0);
                }
            """
        )
        label.clicked.connect(lambda: self.LaunchGame(launch_id, app_name, provider))
        label.setMaximumWidth(200)
        container.setMinimumWidth(200)
        container.setMaximumWidth(200)
        container.setMinimumHeight(50)
        container.setMaximumHeight(label.height())
        container.setStyleSheet("padding: 20px;")
        label.setCursor(QCursor(Qt.PointingHandCursor))
        self.ui.Owned_games_content.layout().addWidget(container)

        self.ui.owned_games_quantity.setText(f'{len(self.ui.Owned_games_content.children())-1} Games (Only Steam)')



    # Database operations
    def CheckDb(self):
        if self.database.conn:
            sql_installed_games = "SELECT * FROM Installed_Games"
            sql_owned_games = "SELECT launch_id, app_name, provider, image, playtime FROM Owned_Games"
            sql_user = "SELECT * FROM User WHERE id = 1"

            installed_games = self.database.execute_query(self.database.conn, sql_installed_games).fetchall()
            owned_games = self.database.execute_query(self.database.conn, sql_owned_games).fetchall()
            user_info = self.database.execute_query(self.database.conn, sql_user).fetchone()

            steamid = user_info[1]
            img_cover_width = user_info[2]
            img_cover_width_owned = user_info[3]
            installed_epic_games = user_info[-3]
            installed_steam_games = user_info[-2]
            total_user_playtime_in_minutes = user_info[-1]

            if steamid != 0:
                info = self.steam.users.get_user_details(steamid)["player"]
                self.ui.user_display_name.setText(f"{info['personaname']}")

                response = requests.get(info['avatarfull'], stream=True)
                image =  Image.open(response.raw)
                q_image = QImage(ImageQt(image))
                pixmap = mask_image(q_image)

                self.ui.user_avatar.setPixmap(pixmap)
                self.UpdateRecentGamesGUI(self.Steam.FetchRecentSteamGames(self, steamid))


            if installed_steam_games != 0:
                self.ui.steam_dir_info.setText(f'✔ {installed_steam_games} Games installed')
                self.ui.steam_dir_info.setStyleSheet(
                    """
                        QLabel {
                            color: rgb(0, 255, 0);
                        }
                    """
                )

            if installed_epic_games != 0:
                self.ui.epic_dir_info.setText(f'✔ {installed_epic_games} Games installed')
                self.ui.epic_dir_info.setStyleSheet(
                    """
                        QLabel {
                            color: rgb(0, 255, 0);
                        }
                    """
                )
            if total_user_playtime_in_minutes != 0:
                self.ui.user_total_playtime.setText(f"Total playtime: {total_user_playtime_in_minutes//60}h {total_user_playtime_in_minutes%60}m")
                self.ui.user_total_playtime.setCursor(Qt.PointingHandCursor)

            if installed_games:
                for game in installed_games:
                    self.AddGameToGUI(*game[1:])
            else:
                self.Steam.FindSteamGames(self)
                self.Epic.FindEpicGames_Games(self)

            if owned_games:
                for game in owned_games:
                    self.AddGameToGUI_Owned(*game)
            else:
                if steamid != 0:
                    try:
                        self.ui.info_label.deleteLater()
                    except Exception:
                        pass
                    self.Steam.RunInThread(self, steamid=steamid, func="FindOwnedSteamGames")
                else:
                    info_label = QLabel()
                    info_label.setText("""Set your steam ID in the "Last Played" Tab""")
                    info_label.setStyleSheet("color: rgb(0, 255, 0);")
                    info_label.setAlignment(Qt.AlignCenter)
                    info_label.setMinimumHeight(self.ui.centralwidget.height())
                    info_label.setObjectName("info_label")
                    font = info_label.font()
                    font.setPointSize(14)
                    info_label.setFont(font)
                    self.ui.Owned_games_content.layout().addWidget(info_label)


            self.ui.set_img_cover_width.setValue(img_cover_width)
            self.ui.set_img_cover_width_owned.setValue(img_cover_width_owned)
            self.SetImageCoverWidth(img_cover_width, from_db="set_img_cover_width")
            self.SetImageCoverWidth(img_cover_width_owned, from_db="set_img_cover_width_owned")



    def UpdateDb(self, launch_id, app_name, provider, image, playtime, db_destination):
        if self.database.conn:
            if image:
                if playtime:
                    sql = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image, playtime) VALUES(?,?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, image, playtime))
                else:
                    sql = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image) VALUES(?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, image))
            else:
                if playtime:
                    sql = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image, playtime) VALUES(?,?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, None, playtime))
                else:
                    sql = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image) VALUES(?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, None))



    def LaunchGame(self, launch_id, app_name, provider):
        if provider == 'steam':
            command = f"start steam://rungameid/{launch_id}"
        elif provider == 'epic':
            command = f"start com.epicgames.launcher://apps/{launch_id}?action=launch"

        try:
            subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            Notification(
                app_id="Games Vault",
                title="Launching Game",
                msg=f'{app_name}',
                icon=os.path.join(os.path.dirname(__file__), "resources", "icons", "launch.png")
            ).show()

            self.showMinimized()

        except Exception:
            Notification(
                app_id="Games Vault",
                title='Error Ocurred',
                msg=f'Error occured while launching {app_name}'
            ).show()



    # Multi-threading
    def FetchInstalledGames(self, app_ids, app_names, provider):
        try:
            self.thread = QThread()
            self.worker = Worker(app_ids, app_names, provider)
            self.worker.setObjectName("installed_games")
            self.worker.moveToThread(self.thread)

            self.worker.progress.connect(self.UpdateDb)
            self.worker.progress.connect(self.AddGameToGUI)
            self.thread.started.connect(self.worker.FindGameCovers)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.threads.append(self.thread)
            self.thread.start()

        except Exception:
            pass


class Worker(QThread):
    finished = Signal()
    progress = Signal(str, str, str, bytes, int, str)

    def __init__(self, app_ids, app_names, provider, parent=None):
        super().__init__(parent)
        self.app_ids = app_ids
        self.app_names = app_names
        self.provider = provider

    def FindGameCovers(self):
        game_icon_urls = []

        for appid_and_name in zip(self.app_ids, self.app_names):
            try:
                game_icon_urls.append([f"https://steamcdn-a.akamaihd.net/steam/apps/{appid_and_name[0]}/library_600x900_2x.jpg", appid_and_name[0], appid_and_name[1]])
            except Exception:
                game_icon_urls.append([[], appid_and_name[0], appid_and_name[1]])

        for url_and_appid in game_icon_urls:
            try:
                response = requests.get(url_and_appid[0], stream=True)
                image =  Image.open(response.raw)
                image = image.resize((200, 500))
                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, image.tobytes(), None, "Installed_Games")

            except Exception:
                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, None, None, "Installed_Games")

        self.finished.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

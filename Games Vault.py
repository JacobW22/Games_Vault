import sys
import requests
import subprocess
import os
import platform

from steam_web_api import Steam as steam_api
from PIL import Image
from PIL.ImageQt import ImageQt
from notifypy import Notify
from pid import PidFile, PidFileError

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QSystemTrayIcon, QMenu, QSizePolicy, QHBoxLayout, QMessageBox
from PySide6.QtGui import QPixmap, QImage, QCursor, QIcon, QAction
from PySide6.QtCore import QThread, Signal, QRect, Qt, QSize, QTimer, QPointF, QSettings

from Steam import Steam
from Epic import Epic
from database import Database
from Logging import LoggingSetup

from layout.ui_form import Ui_MainWindow
from layout.FlowLayout import FlowLayout
from layout.RichTextPushButton import RichTextPushButton
from layout.CircularAvatar import mask_image
from desktop_widget import DesktopWidget


# Keys
settings = QSettings((os.path.join(os.path.dirname(__file__), "resources", "config", "config.ini")), QSettings.IniFormat)
STEAM_API_KEY = settings.value("API_KEYS/STEAM_API_KEY")


# Initialize the logger
logger = LoggingSetup.setup_logging()


# System notifications
notification = Notify()


# Force dark mode on Windows
if platform.system() == "Windows":
    sys.argv += ['-platform', 'windows:darkmode=2']


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

        self.ui.tabWidget.setStyleSheet(
        """
            QTabBar::tab {
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                color: rgb(255, 255, 255);
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
        """
        )

        btn_stylesheet = (
        """
            QPushButton {
                background-color: #424242;
                border: 2px solid #646464;
                padding: 5px;
                border-radius: 8px;
            }

            QPushButton:hover {
                background-color: rgba(60, 60, 60, 0.5);
                color: rgb(0, 255, 0);
            }

            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.5);
                color: rgb(0, 255, 0);
            }
        """
        )

        search_widget_stylesheet = (
        """
            QWidget {
                border: 2px solid white;
                border-radius: 8px;
                background-color: rgba(0, 0, 0, 0);
            };
        """
        )

        self.ui.search_widget.setStyleSheet(search_widget_stylesheet)
        self.ui.search_widget_2.setStyleSheet(search_widget_stylesheet)

        self.ui.find_steam_directory.setStyleSheet(btn_stylesheet)
        self.ui.find_epic_games_directory.setStyleSheet(btn_stylesheet)
        self.ui.open_widget.setStyleSheet(
        """
            QPushButton {
                background-color: #424242;
                border: 2px solid #646464;
                border-radius: 8px;
                padding-left: 8px;
                padding-right: 8px;
                color: rgb(0, 255, 0);
            }

            QPushButton:hover {
                background-color: rgba(60, 60, 60, 0.5);
            }

            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 0.5);
                color: rgb(0, 255, 0);
            }
        """
        )


        # System tray menu and app icon setup
        self.tray_icon = QSystemTrayIcon()

        self.tray_icon.setIcon(QIcon("resources/icons/app_icon.ico"))
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


        # Initialize objects
        self.Steam = Steam()
        self.Epic = Epic()


        # Initialize buttons connections and actions
        self.ui.find_epic_games_directory.clicked.connect(lambda: self.Epic.FindEpicGames(self))
        self.ui.find_steam_directory.clicked.connect(lambda: self.Steam.FindInstalledSteamGames(self))
        self.ui.open_widget.clicked.connect(self.OpenWidget)
        self.ui.launch_widget_on_start.clicked.connect(self.UpdateSettings)
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


        # Run checks on database
        self.CheckDb()



    # System tray menu operations
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



    # GUI operations
    def resizeEvent(self, event):
        self.ui.search_widget_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.search_widget_container_2.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.width_slider_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.width_slider_container_2.setMaximumWidth((self.ui.centralwidget.width()/3)+15)

        try:
            if self.ui.Owned_games_content.children()[1].objectName() == "info_label":
                self.ui.Owned_games_content.children()[1].setMinimumHeight(self.ui.centralwidget.height()-125)
        except Exception as e:
            logger.error(f"resizeEvent: {e}")



    def OpenWidget(self):
        self.desktop_widget = DesktopWidget()
        self.desktop_widget.show()

        if self.database.conn:
            query = "SELECT widget_last_pos_x, widget_last_pos_y, widget_last_width, widget_last_height FROM User WHERE id = 1"
            result = self.database.execute_query(self.database.conn, query).fetchall()
            pos_x, pos_y, width, height = result[0][0], result[0][1], result[0][2], result[0][3]
            self.desktop_widget.move(pos_x, pos_y)
            self.desktop_widget.resize(width, height)


        self.installed_games_container = self.ui.installed_games_container

        self.ui.open_widget.hide()
        self.ui.installed_games_quantity.hide()
        self.desktop_widget.ui.centralwidget.layout().addWidget(self.installed_games_container)

        self.close_widget_btn_container = QWidget()
        self.close_widget_btn_container.setLayout(QHBoxLayout())

        close_widget_btn = QPushButton()
        close_widget_btn.setText("Close Active Widget")
        close_widget_btn.setMaximumWidth(250)
        close_widget_btn.setStyleSheet(
        """
            QPushButton {
                font-size: 20px;
                background-color: #424242;
                border: 2px solid #646464;
                border-radius: 8px;
                padding: 15px;
            }

            QPushButton:hover {
                background-color: rgba(60, 60, 60, 0.5);
                color: rgb(0, 255,0);
            }
        """
        )
        close_widget_btn.setCursor(Qt.PointingHandCursor)

        close_widget_btn.clicked.connect(self.CloseWidget)
        self.desktop_widget.window_closed.connect(self.SaveWidgetInfo)
        self.desktop_widget.window_closed.connect(self.CloseWidget)
        self.close_widget_btn_container.layout().addWidget(close_widget_btn)
        self.ui.scrollAreaWidgetContents_2.layout().addWidget(self.close_widget_btn_container)



    def CloseWidget(self):
        self.close_widget_btn_container.deleteLater()
        self.ui.installed_games_quantity.show()
        self.ui.open_widget.show()
        self.ui.scrollAreaWidgetContents_2.layout().addWidget(self.installed_games_container)
        self.desktop_widget.close()



    def StartRefreshTimers(self):
        self.timer_5min = QTimer()
        self.timer_5min.timeout.connect(self.RefreshRecentGames)
        self.timer_5min.start((5 * 60 * 1000)) # Refresh every 5 minutes

        self.timer_1sec = QTimer()
        self.timer_1sec.timeout.connect(self.UpdateRecentGamesRefreshTimer)
        self.timer_1sec.start(1000)



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

                mode = 0

                while self.ui.user_total_playtime.text() == display_modes[mode]:
                    mode += 1
                self.ui.user_total_playtime.setText(display_modes[mode])

            except Exception as e:
                logger.error(f"ChangeUserTotalPlaytimeDisplayMode: {e}")



    def SearchGameOnTextChanged(self, text):
        match self.sender().objectName():
            case "search_games":
                games = self.ui.Installed_games_content.children()[1:]
            case "search_games_owned":
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
            except Exception as e:
                sender = None
                logger.error(f"SetImageCoverWidth: {e}")


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
            match slider.objectName():
                case  "set_img_cover_width":
                    query = "UPDATE user SET game_cover_img = ? WHERE id = 1;"
                    self.database.execute_query(self.database.conn, query, [slider.value()])

                case  "set_img_cover_width_owned":
                    query = "UPDATE user SET owned_game_cover_img = ? WHERE id = 1;"
                    self.database.execute_query(self.database.conn, query, [slider.value()])



    def UpdateRecentGamesGUI(self, game_icon_urls):
        for url_and_appid in game_icon_urls:
            try:
                image =  Image.open(requests.get(url_and_appid[0], stream=True).raw)
                q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)
            except Exception as e:
                q_image = None
                logger.error(f"UpdateRecentGamesGUI: {e}")


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
                label.setText(f"{url_and_appid[2]}")
                label.setStyleSheet("background-color: rgb(42, 42, 42);")


            container.setObjectName(f"{url_and_appid[2]}")
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
                    border: 0;
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

            btn_label.setText(f"▶\n{url_and_appid[2]}")
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
            self.play_game = QAction(f"{url_and_appid[2]}", self)
            font = self.tray_menu.font()
            font.setPointSize(12)
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
                    border: 0;
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

        except Exception as e:
            logger.error(f"AddGameToGUI: {e}")



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
                    text-align: left;
                    background-color: #424242;
                    border: 2px solid #646464;
                    border-radius: 8px;
                }

                QPushButton:hover {
                    background-color: rgba(60, 60, 60, 0.5);
                    color: rgb(0, 255, 0);
                }

                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.5);
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
            open_widget_on_start = settings.value("USER_SETTINGS/LAUNCH_WIDGET_ON_STARTUP", type=bool)
            img_cover_width = user_info[-6]
            img_cover_width_owned = user_info[-5]
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
                self.StartRefreshTimers()
                self.UpdateRecentGamesGUI(self.Steam.FetchRecentSteamGames(self, steamid))



            if open_widget_on_start == True:
                self.ui.launch_widget_on_start.setText("On")
                self.ui.launch_widget_on_start.setStyleSheet("color: rgb(0, 255, 0);")
                self.OpenWidget()



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
                self.Epic.closed_dialog.connect(lambda: self.Steam.FindInstalledSteamGames(self))
                self.Steam.closed_dialog.connect(lambda: self.Steam.ChangeSteamID(self))
                self.Epic.FindEpicGames(self)



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



    def UpdateGames(self, launch_id, app_name, provider, image, playtime, db_destination):
        if self.database.conn:
            if image:
                if playtime:
                    query = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image, playtime) VALUES(?,?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, query, (1, launch_id, app_name, provider, image, playtime))
                else:
                    query = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image) VALUES(?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, query, (1, launch_id, app_name, provider, image))
            else:
                if playtime:
                    query = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image, playtime) VALUES(?,?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, query, (1, launch_id, app_name, provider, None, playtime))
                else:
                    query = f"INSERT OR REPLACE INTO {db_destination}(user_id, launch_id, app_name, provider, image) VALUES(?,?,?,?,?)"
                    self.database.execute_query(self.database.conn, query, (1, launch_id, app_name, provider, None))



    def UpdateSettings(self):
            match self.sender().text():
                case "Off":
                    self.sender().setText("On")
                    self.sender().setStyleSheet("color: rgb(0, 255, 0);")
                    settings.setValue("USER_SETTINGS/LAUNCH_WIDGET_ON_STARTUP", True)
                    settings.sync()
                case "On":
                    self.sender().setText("Off")
                    self.sender().setStyleSheet("color: rgb(255, 0, 0);")
                    settings.setValue("USER_SETTINGS/LAUNCH_WIDGET_ON_STARTUP", False)
                    settings.sync()



    def SaveWidgetInfo(self):
        if self.database.conn:
            query = "UPDATE user SET widget_last_pos_x = ?, widget_last_pos_y = ?, widget_last_width = ?, widget_last_height = ? WHERE id = 1;"
            widget_pos = self.desktop_widget.pos()
            widget_pos_float = QPointF(widget_pos)
            self.database.execute_query(self.database.conn, query, [widget_pos_float.x(), widget_pos_float.y(), self.desktop_widget.width(), self.desktop_widget.height()])



    def LaunchGame(self, launch_id, app_name, provider):
        match provider:
            case 'steam':
                command = f"start steam://rungameid/{launch_id}"
            case 'epic':
                command = f"start com.epicgames.launcher://apps/{launch_id}?action=launch"

        try:
            subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            notification.application_name = "Games Vault"
            notification.title = "Launching Game"
            notification.message = f"{app_name}"
            notification.icon = os.path.join(os.path.dirname(__file__), "resources", "icons", "launch.png")
            notification.send()

            self.showMinimized()

        except Exception as e:
            notification.application_name = "Games Vault"
            notification.title = 'Error occured while launching'
            notification.message = f"{app_name}"
            notification.send()
            logger.error(f"LaunchGame: {e}")



    # Multi-threading
    def FetchInstalledGames(self, app_ids, app_names, provider):
        try:
            self.thread = QThread()
            self.worker = Worker(self, app_ids, app_names, provider)
            self.worker.setObjectName("installed_games")
            self.worker.moveToThread(self.thread)

            self.worker.progress.connect(self.UpdateGames)
            self.worker.progress.connect(self.AddGameToGUI)
            self.thread.started.connect(self.worker.FindGameCovers)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.threads.append(self.thread)
            self.thread.start()

        except Exception as e:
            logger.error(f"FetchInstalledGames: {e}")



class Worker(QThread):

    finished = Signal()
    progress = Signal(str, str, str, bytes, int, str)


    def __init__(self, main_window, app_ids, app_names, provider, parent=None):
        super().__init__(parent)
        self.app_ids = app_ids
        self.app_names = app_names
        self.provider = provider
        self.main_window = main_window



    def FindGameCovers(self):
        game_icon_urls = []
        games_in_gui = []

        for item in self.main_window.ui.Installed_games_content.children():
                games_in_gui.append(item.objectName())

        for appid_and_name in zip(self.app_ids, self.app_names):
            if appid_and_name[1][0] not in games_in_gui:
                try:
                    game_icon_urls.append([f"https://steamcdn-a.akamaihd.net/steam/apps/{appid_and_name[0]}/library_600x900_2x.jpg", appid_and_name[0], appid_and_name[1]])
                except Exception as e:
                    game_icon_urls.append([[], appid_and_name[0], appid_and_name[1]])
                    logger.error(f"FindGameCovers: {e}")


        for url_and_appid in game_icon_urls:
            try:
                response = requests.get(url_and_appid[0], stream=True)
                image =  Image.open(response.raw)
                image = image.resize((200, 500))

                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, image.tobytes(), None, "Installed_Games")

            except Exception as e:
                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, None, None, "Installed_Games")
                logger.error(f"FindGameCovers: {e}")

        self.finished.emit()
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("resources/icons/app_icon.ico"))
    app.setStyle('GTK')

    # Make sure only 1 instance is running at the same time
    try:    
        with PidFile(piddir=os.path.expanduser('~/Games Vault/')):
            widget = MainWindow()   
            widget.show()
            sys.exit(app.exec())
            
    except PidFileError:
        QMessageBox.warning(None, "Error", "Another instance of this application is already running.")
        sys.exit(1)
        
    




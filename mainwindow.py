# This Python file uses the following encoding: utf-8
import sys
import configparser
import requests
import subprocess
import os
import ctypes

from steam_web_api import Steam
from PIL import Image
from PIL.ImageQt import ImageQt
from winotify import Notification
from ctypes import wintypes

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QPushButton, QMessageBox, QSystemTrayIcon, QMenu, QDialogButtonBox, QSizePolicy
from PySide6.QtGui import QPixmap, QImage, QCursor, QIcon, QAction
from PySide6.QtCore import QThread, Signal, QRect, Qt

from ui_form import Ui_MainWindow
from Steam import FindSteamGames
from Epic import FindEpicGames_Games
from FlowLayout import FlowLayout
from database import Database
from InputDialog import InputDialog
from MessageBox import MessageBox
from ErrorMessage import ErrorMessage
from RichTextPushButton import RichTextPushButton
from CircularAvatar import mask_image

# Windows taskbar and task manager names config
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

    steam = Steam(STEAM_API_KEY)
    col_index, row_index, last_row_index, container_id = 0, 0, 0, 0
    games = None


    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.tray_icon = QSystemTrayIcon()
        app_icon = QIcon(":/icons/resources\icons/app_icon.png")

        self.tray_icon.setIcon(app_icon)
        self.tray_icon.setToolTip("Games Vault")

        self.tray_menu = QMenu()
        self.restore_action = QAction("Open", self)
        self.hide_action = QAction("Hide", self)
        self.quit_action = QAction("Quit", self)

        self.tray_menu.addAction(self.restore_action)
        self.tray_menu.addAction(self.hide_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_menu.addSeparator()
        self.tray_icon.setContextMenu(self.tray_menu)

        # Layout
        self.flow_layout_recent_games = FlowLayout(self.ui.Steam_recent_games)
        self.flow_layout_installed_games = FlowLayout(self.ui.Steam_recent_games_8)

        self.change_steam_id = RichTextPushButton()
        self.change_steam_id.setFlat(True)
        self.change_steam_id.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.change_steam_id.setStyleSheet("color: rgb(255, 255, 255); font-size: 28px")
        self.change_steam_id.setText("Recent Games <span style='font-size: 12px; color: rgb(0, 255, 0);'>change steamID</span>")
        self.change_steam_id.setObjectName("change_steam_id_2")
        self.change_steam_id.setCursor(Qt.PointingHandCursor)

        self.ui.change_steam_id_container.layout().addWidget(self.change_steam_id)

        # Connect database
        self.database = Database()
        self.check_db()

        # Initialize buttons
        # self.FetchRecentSteamGames(steamid)
        self.ui.find_epic_games_directory.clicked.connect(lambda: FindEpicGames_Games(self))
        self.ui.find_steam_directory.clicked.connect(lambda: FindSteamGames(self))
        self.change_steam_id.clicked.connect(self.ChangeSteamID)

        self.ui.set_img_cover_width.sliderReleased.connect(self.UpdateImageCoverWidthInDatabase)
        self.ui.set_img_cover_width.valueChanged.connect(self.SetImageCoverWidth)
        self.ui.search_games.textChanged.connect(self.SearchGameOnTextChanged)

        self.tray_icon.activated.connect(self.show_normal)
        self.restore_action.triggered.connect(self.show_normal)
        self.hide_action.triggered.connect(self.hide_application)
        self.quit_action.triggered.connect(self.quit_application)
        self.tray_icon.show()

        self.setWindowIcon(app_icon)



    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def show_normal(self, reason):
        if reason == QSystemTrayIcon.Trigger or reason == False:
              self.show()

        elif reason == QSystemTrayIcon.Context:
          # Right click event, ignore it
          pass


    def hide_application(self):
        self.hide()

    def quit_application(self):
        QApplication.instance().quit()


    # Overwrited method
    def resizeEvent(self, event):
        self.ui.search_widget_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)
        self.ui.width_slider_container.setMaximumWidth((self.ui.centralwidget.width()/3)+15)


    def ShowErrorDialog(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Warning)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec()


    def ChangeSteamID(self):
        title = "Change SteamID"
        input_label_text = "steamID:"
        info_message = """
            <html><body>
            <center>
            <a style="color: lightblue;" href="https://help.steampowered.com/faqs/view/2816-BE67-5B69-0FEC">How to find my steamID</a>
            </center>
            </body></html>
        """

        dialog = InputDialog(title, input_label_text, info_message, self)

        if dialog.exec():
            steamid = dialog.get_input()
            try:
                user_info = self.steam.users.get_user_details(steamid)["player"]
                self.ui.user_display_name.setText(f"{user_info['personaname']}")

                response = requests.get(user_info['avatarmedium'], stream=True)
                image =  Image.open(response.raw)
                q_image = QImage(ImageQt(image))
                pixmap = mask_image(q_image)

                self.ui.user_avatar.setPixmap(pixmap)

                if len(self.ui.Steam_recent_games.children()) > 1:
                    for game in self.ui.Steam_recent_games.children()[1:]:
                        game.deleteLater()

                self.FetchRecentSteamGames(steamid)

                if self.database.conn:
                    sql = "UPDATE user SET steam_id = ? WHERE id = 1;"
                    self.database.execute_query(self.database.conn, sql, [steamid])

            except Exception:
                info_message = """
                    <html><body>
                    <center>
                    <a>Wrong steamID</a><br>
                    <a style="color: lightblue;" href="https://help.steampowered.com/faqs/view/2816-BE67-5B69-0FEC">How to find my steamID</a>
                    </center>
                    </body></html>
                """
                error_msg = ErrorMessage(info_message)
                error_msg.exec()

    def SearchGameOnTextChanged(self, text):
        for game in self.ui.Steam_recent_games_8.children()[1:]:
            if text.lower() not in (game.objectName()).lower():
                game.hide()
            else:
                game.show()


    def check_db(self):
        if self.database.conn:
            sql_installed_games = "SELECT * FROM Installed_Games"
            sql_user = "SELECT * FROM User WHERE id = 1"


            installed_games = self.database.execute_query(self.database.conn, sql_installed_games).fetchall()
            user_info = self.database.execute_query(self.database.conn, sql_user).fetchone()



            steamid = user_info[1]
            img_cover_width = user_info[2]
            installed_epic_games = user_info[-2]
            installed_steam_games = user_info[-1]

            if steamid != 0:
                info = self.steam.users.get_user_details(steamid)["player"]
                self.ui.user_display_name.setText(f"{info['personaname']}")

                response = requests.get(info['avatarmedium'], stream=True)
                image =  Image.open(response.raw)
                q_image = QImage(ImageQt(image))
                pixmap = mask_image(q_image)

                self.ui.user_avatar.setPixmap(pixmap)
                self.FetchRecentSteamGames(steamid)


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

            if installed_games:
                for game in installed_games:
                    self.AddGameToGUI(*game[1:])
            else:
                FindSteamGames(self)
                FindEpicGames_Games(self)

            self.SetImageCoverWidth(img_cover_width)
            self.ui.set_img_cover_width.setValue(img_cover_width)


    def SetImageCoverWidth(self, value):
        fit_width = value
        self.ui.img_cover_width_info.setText(f'{value}px')

        for game in self.ui.Steam_recent_games_8.children():
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


    def UpdateImageCoverWidthInDatabase(self):
        if self.database.conn:
            sql = "UPDATE user SET game_cover_img = ? WHERE id = 1;"
            self.database.execute_query(self.database.conn, sql, [self.ui.set_img_cover_width.value()])


    def FetchRecentSteamGames(self, steamid):
        player_info = self.steam.users.get_user_recently_played_games(steamid)
        game_icon_urls = []

        for game in player_info["games"]:
            try:
                game_icon_urls.append([f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg", game['appid'], game['name']])
            except Exception as e:
                game_icon_urls.append([[], game['appid'], game['name']])
                print('Error fetching Image', e)



        for url_and_appid in game_icon_urls:
            try:
                image =  Image.open(requests.get(url_and_appid[0], stream=True).raw)
                q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)
            except Exception:
                q_image = None


            fit_width = 1200/6.5

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

            self.play_game = QAction(f"{url_and_appid[2]}", self)
            self.tray_menu.addAction(self.play_game)
            self.play_game.triggered.connect(lambda sacrificial="", appid=url_and_appid[1], appname=url_and_appid[2]: self.LaunchGame(appid, appname, provider='steam'))
            play_button.clicked.connect(lambda sacrificial="", appid=url_and_appid[1], appname=url_and_appid[2]: self.LaunchGame(appid, appname, provider='steam'))

            url_and_appid.clear()
            self.ui.Steam_recent_games.layout().addWidget(container)
            self.ui.Steam_recent_games.update()



    def FetchInstalledGames(self, app_ids, app_names, provider):
            self.thread = QThread()
            self.worker = Worker(app_ids, app_names, provider)
            self.worker.moveToThread(self.thread)

            self.worker.progress.connect(self.AddGameToGUI)
            self.thread.started.connect(self.worker.FindGameCovers)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self.thread.start()


    def AddGameToGUI(self, launch_id, app_name, provider, image):
        try:
            container = QWidget()
            label = QLabel(container)
            btn_label = QLabel(container)
            play_button = QPushButton(btn_label)
            fit_width = self.ui.set_img_cover_width.value()

            if self.database.conn:
                sql = f"INSERT OR REPLACE INTO Installed_Games(user_id, launch_id, app_name, provider, image) VALUES(?,?,?,?,?)"

                if image:
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, image))
                else:
                    self.database.execute_query(self.database.conn, sql, (1, launch_id, app_name, provider, image))


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

            if app_name.encode().decode('unicode-escape') not in [x.objectName() for x in self.ui.Steam_recent_games_8.children()]:
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


                self.ui.Steam_recent_games_8.layout().addWidget(container)
                self.ui.installed_games_quantity.setText(f'{len(self.ui.Steam_recent_games_8.children())-1} Games')

        except Exception as e:
            print('Error in AddGametoGui: ', e)


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


class Worker(QThread):
    finished = Signal()
    progress = Signal(str, str, str, bytes)

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
            except Exception as e:
                game_icon_urls.append([[], appid_and_name[0], appid_and_name[1]])
                print('Error fetching Image', e)

        for url_and_appid in game_icon_urls:
            try:
                response = requests.get(url_and_appid[0], stream=True)
                image =  Image.open(response.raw)
                image = image.resize((200, 500))

                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, image.tobytes())

            except Exception:
                self.progress.emit(url_and_appid[2][1], url_and_appid[2][0], self.provider, None)

        self.finished.emit()



if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

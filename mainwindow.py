# This Python file uses the following encoding: utf-8
import sys
import configparser
import requests
import math
import subprocess
import os

from steam_web_api import Steam
from PIL import Image
from win11toast import toast
from winotify import Notification

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QFrame, QWidget, QPushButton, QMessageBox, QSystemTrayIcon, QMenu
from PySide6.QtGui import QPixmap, QImage, QCursor, QIcon, QAction
from PySide6.QtCore import QThread, Signal, QRect, Qt

from ui_form import Ui_MainWindow
from Steam import FindSteamGames
from Epic import FindEpicGames_Games

# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']


class MainWindow(QMainWindow):

    steam = Steam(STEAM_API_KEY)
    col_index, row_index, last_row_index, container_id = 0, 0, 0, 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.tray_icon = QSystemTrayIcon()
        pixmap = QPixmap(os.path.join(os.path.dirname(__file__), "resources", "icons", "launch.png"))
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Games Vault")

        self.tray_menu = QMenu()
        self.restore_action = QAction("Open", self)
        self.hide_action = QAction("Hide", self)
        self.quit_action = QAction("Quit", self)

        self.tray_menu.addAction(self.restore_action)
        self.tray_menu.addAction(self.hide_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)

        self.tray_icon.show()

        # Initialize buttons
        # self.ui.connect_steam.clicked.connect(self.OnConnectSteamClick())
        self.ui.connect_epic.clicked.connect(lambda: FindEpicGames_Games(self))
        self.ui.change_steam_directory.clicked.connect(lambda: FindSteamGames(self))

        self.restore_action.triggered.connect(self.show_normal)
        self.hide_action.triggered.connect(self.hide_application)
        self.quit_action.triggered.connect(self.quit_application)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def show_normal(self):
        self.show()

    def hide_application(self):
        self.hide()

    def quit_application(self):
        QApplication.instance().quit()



    # Overwrited method
    def resizeEvent(self, event):
        fit_width = (self.ui.centralwidget.width()/7)-10

        for col,game in enumerate(self.ui.Steam_recent_games_8.children()):
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


    def ShowErrorDialog(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Warning)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec()

    def OnConnectSteamClick(self):
        steamid = "76561198137844761"
        self.FetchRecentSteamGames(steamid)



    def FetchRecentSteamGames(self, steamid):
        player_info = self.steam.users.get_user_recently_played_games(steamid)

        game_icon_urls = []

        for game in player_info["games"]:
            game_icon_urls.append(f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg")


        for url in game_icon_urls:
            # testing - url = "https://steamcdn-a.akamaihd.net/steam/apps/1250410/library_600x900_2x.jpg"

            image =  Image.open(requests.get(url, stream=True).raw)
            q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)


            label = QLabel()
            pixmap = QPixmap.fromImage(q_image)

            label.setMinimumWidth(155)
            label.setMinimumHeight(225)

            label.setMaximumWidth(155)
            label.setMaximumHeight(225)

            label.setBaseSize(155, 225)

            label.setPixmap(pixmap)
            label.setScaledContents(True)
            label.setFrameShape(QFrame.Shape.Box)
            label.setFrameShadow(QFrame.Shadow.Plain)
            label.setLineWidth(3)

            self.ui.Steam_recent_games.layout().addWidget(label)
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


    def AddGameToGUI(self, q_image, info, app_name, image_found, provider):
        try:
            container = QWidget()
            label = QLabel(container)
            btn_label = QLabel(container)
            play_button = QPushButton(btn_label)
            fit_width = self.ui.centralwidget.width()/7.5

            if image_found:
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


            container.setObjectName(f'container {self.container_id}')
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

            play_button.clicked.connect(lambda: self.LaunchGame(info, app_name, provider))

            children_count = len(self.ui.Steam_recent_games_8.children())
            self.ui.Steam_recent_games_8.layout().addWidget(container, self.row_index, self.col_index)

            self.row_index = math.floor(children_count//7)

            if self.last_row_index == self.row_index:
                self.col_index += 1
            else:
                self.col_index = 0

            self.last_row_index = self.row_index
            self.container_id += 1

        except Exception as e:
            print('Error in AddGametoGui: ', e)

    # def fetchAllGames(self, steamid):
    #     player_info = self.steam.users.get_owned_games(steamid)

    #     game_icon_urls = []

    #     for game in player_info["games"]:
    #         try:
    #             game_icon_urls.append(f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg")
    #         except Exception as e:
    #             print(e)
    #     print(game_icon_urls)


    def LaunchGame(self, info, app_name, provider):
        if provider == 'steam':
            command = f"start steam://rungameid/{info[0]}"
        elif provider == 'epic':
            command = f"start com.epicgames.launcher://apps/{info[0]}?action=launch"

        try:
            subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            toast = Notification(
                app_id="Games Vault",
                title="Launching Game",
                msg=f'{app_name}',
                icon=os.path.join(os.path.dirname(__file__), "resources", "icons", "launch.png")
            ).show()

            self.showMinimized()

        except Exception as e:
            toast = Notification(
                app_id="Games Vault",
                title='Error Ocurred',
                msg=f'Error occured while launching {app_name}{e}'
            ).show()


class Worker(QThread):
    finished = Signal()
    progress = Signal(QImage, list, str, bool, str)

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
            # testing - url = "https://steamcdn-a.akamaihd.net/steam/apps/1250410/library_600x900_2x.jpg"

            try:
                response = requests.get(url_and_appid[0], stream=True)
                image =  Image.open(response.raw)
                image = image.resize((200, 500))

                q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)

                self.progress.emit(q_image, [url_and_appid[2][1], url_and_appid[0]], url_and_appid[2][0], True, self.provider)

            except Exception as e:
                self.progress.emit(QImage, [url_and_appid[2][1], url_and_appid[0]], url_and_appid[2][0], False, self.provider)

        self.finished.emit()



if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

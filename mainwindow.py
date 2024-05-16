# This Python file uses the following encoding: utf-8
import sys
# import os
import configparser
import requests
import io
import math
import subprocess


from steam_web_api import Steam
from PIL import Image


from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QFrame, QWidget, QPushButton
from PySide6.QtGui import QPixmap, QImage, QPalette, QColor, QIcon, QCursor, QPainter, QPainterPath, QBitmap
from PySide6.QtCore import QObject, QThread, Signal, QSize, QRect, Qt

from ui_form import Ui_MainWindow

# Keys
config = configparser.ConfigParser()
config.read('config.ini')

STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']



class MainWindow(QMainWindow):

    steam = Steam(STEAM_API_KEY)
    col_index, row_index,  last_row_index, container_id = 0, 0, 0, 0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.play_btn_palette = self.palette()
        self.play_btn_palette.setColor(QPalette.ColorRole.Button, QColor(0, 0, 0, 175))

        # fetch steam games
        # steamid = "76561198137844761"
        # self.fetchRecentSteamGames(steamid)


        # initialize button listeners
        self.ui.connect_steam.clicked.connect(self.runLongTask)



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


    def onConnectSteamClick(self):
        steamid = "76561198137844761"
        self.fetchRecentSteamGames(steamid)



    def fetchRecentSteamGames(self, steamid):
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



    def runLongTask(self):
            # Step 2: Create a QThread object
            self.thread = QThread()
            # Step 3: Create a worker object
            self.worker = Worker()
            # Step 4: Move worker to the thread
            self.worker.moveToThread(self.thread)
            # Step 5: Connect signals and slots
            self.worker.progress.connect(self.reportProgress)
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # Step 6: Start the thread
            self.thread.start()


    def reportProgress(self, q_image, appid):
        try:
            container = QWidget()
            label = QLabel(container)
            play_button = QPushButton(container)
            fit_width = self.ui.centralwidget.width()/7.5

            pixmap = QPixmap.fromImage(q_image)
            label.setPixmap(pixmap)

            container.setObjectName(f'container {self.container_id}')
            container.setFixedSize(fit_width, fit_width*1.5)


            label.setMaximumWidth(fit_width)
            label.setMaximumHeight(fit_width*1.5)
            label.setBaseSize(fit_width, fit_width*1.5)
            label.setScaledContents(True)


            play_button.setObjectName(f'play_button {self.container_id}')
            play_button.setProperty('geometry', QRect( 0, 0, fit_width, fit_width*1.5) )
            play_button.setText('▶')
            play_button.setFont('Inter')
            play_button.setCursor(QCursor(Qt.PointingHandCursor))
            play_button.setStyleSheet(
            """
                QPushButton {
                    background-color: rgba(0, 0, 0, 0);
                    color: transparent;
                    font-size: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.5);
                    font-size: 20px;
                    color: rgb(60, 255, 0);
                }

                QPushButton:pressed {
                    background-color: rgba(0, 0, 0, 0.8);
                    color: transparent;
                }

            """
            )
            play_button.setPalette(self.play_btn_palette)
            play_button.clicked.connect(lambda: self.launch_game(appid))


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
            print(e)

    # def fetchAllGames(self, steamid):
    #     player_info = self.steam.users.get_owned_games(steamid)

    #     game_icon_urls = []

    #     for game in player_info["games"]:
    #         try:
    #             game_icon_urls.append(f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg")
    #         except Exception as e:
    #             print(e)
    #     print(game_icon_urls)

    #     for url in game_icon_urls:
    #         # testing - url = "https://steamcdn-a.akamaihd.net/steam/apps/1250410/library_600x900_2x.jpg"

    #         try:
    #             image =  Image.open(requests.get(url, stream=True).raw)
    #             q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)

    #             label = QLabel()
    #             pixmap = QPixmap.fromImage(q_image)

    #             label.setMinimumWidth(155)
    #             label.setMinimumHeight(225)

    #             label.setMaximumWidth(155)
    #             label.setMaximumHeight(225)

    #             label.setBaseSize(155, 225)

    #             label.setPixmap(pixmap)
    #             label.setScaledContents(True)
    #             label.setFrameShape(QFrame.Shape.Box)
    #             label.setFrameShadow(QFrame.Shadow.Plain)
    #             label.setLineWidth(3)

    #             self.ui.Steam_recent_games.layout().addWidget(label)
    #         except Exception as e:
    #             print(e)

    #         self.ui.Steam_recent_games.update()

    def launch_game(self, appid):
        print('clicked')
        # command = f"start steam://rungameid/{appid}"
        # subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

class Worker(QThread):
    finished = Signal()
    progress = Signal(QImage, int)


    def run(self, steamid = "76561198137844761"):
        """Long-running task."""
        steam = Steam(STEAM_API_KEY)

        player_info = steam.users.get_owned_games(steamid, include_appinfo=False)
        game_icon_urls = []

        for game in player_info["games"]:
            try:
                game_icon_urls.append([f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg", game['appid']])
            except Exception as e:
                print(e)


        for url_and_appid in game_icon_urls:
            # testing - url = "https://steamcdn-a.akamaihd.net/steam/apps/1250410/library_600x900_2x.jpg"

            try:
                response = requests.get(url_and_appid[0], stream=True)
                image =  Image.open(response.raw)
                image = image.resize((200, 500))

                q_image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGB888)

                self.progress.emit(q_image, url_and_appid[1])

            except Exception as e:
                print(e)

        self.finished.emit()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()    
    sys.exit(app.exec())

# This Python file uses the following encoding: utf-8
import sys
import requests

from steam_web_api import Steam
from PIL import Image


from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QFrame
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from ui_form import Ui_MainWindow

class MainWindow(QMainWindow):

    API_KEY = "F8E47C8FAB2D9506C1CD120E29371F3D"
    steam = Steam(API_KEY)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # fetch steam games
        # steamid = "76561198137844761"
        # self.fetchRecentSteamGames(steamid)


        # initialize button listeners
        self.ui.connect_steam.clicked.connect(self.onConnectSteamClick)



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



if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())

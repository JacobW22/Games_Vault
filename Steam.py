import os
import vdf
import configparser
import requests

from steam_web_api import Steam as steam_api
from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import QFileDialog
from PySide6.QtGui import QImage
from PySide6.QtCore import QThread, Signal

from layout.MessageBox import MessageBox
from layout.ErrorMessage import ErrorMessage
from layout.InputDialog import InputDialog
from layout.CircularAvatar import mask_image

# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']

class Steam:
    steam = steam_api(STEAM_API_KEY)
    threads = []

    def FindSteamGames(self, main_window, directory=f"{os.getenv('SystemDrive')}\Program Files (x86)\Steam"):
        try:
            if directory:
                self.RunInThread(main_window, func="FindSteamGames", directory=directory)
            else:
                raise Exception

        except Exception:
            error_msg = ErrorMessage("Can't Find Steam Libraries")
            error_msg.exec()

            options = QFileDialog.Options()
            options |= QFileDialog.ShowDirsOnly

            info_message = """
            <html><body>
            <center>
            <p>Please select your main Steam directory.</p>
            <a style="color: lightblue;" href="https://www.partitionwizard.com/partitionmanager/where-does-steam-install-games.html">How to find my Steam Directory</a>
            </center>
            </body></html>
            """
            msg_box = MessageBox("Steam", info_message)
            msg_box.exec()

            directory = QFileDialog.getExistingDirectory(
               None,
               "Select Your Main Steam Directory",
               "",
               options=options,
            )

            if directory:
                self.RunInThread(main_window, func="FindSteamGames", directory=directory)


    def FetchRecentSteamGames(self, steamid):
        player_info = self.steam.users.get_user_recently_played_games(steamid)
        game_icon_urls = []

        for game in player_info["games"]:
            try:
                game_icon_urls.append([f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/library_600x900_2x.jpg", game['appid'], game['name']])
            except Exception as e:
                game_icon_urls.append([[], game['appid'], game['name']])
                print('Error fetching Image', e)

        return game_icon_urls



    def ChangeSteamID(self, main_window):
        title = "Change SteamID"
        input_label_text = "steamID:"
        info_message = """
            <html><body>
            <center>
            <a style="color: lightblue;" href="https://help.steampowered.com/faqs/view/2816-BE67-5B69-0FEC">How to find my steamID</a>
            </center>
            </body></html>
        """

        dialog = InputDialog(title, input_label_text, info_message)

        if dialog.exec():
            steamid = dialog.get_input()
            try:
                user_info = self.steam.users.get_user_details(steamid)["player"]
                main_window.ui.user_display_name.setText(f"{user_info['personaname']}")

                response = requests.get(user_info['avatarfull'], stream=True)
                image =  Image.open(response.raw)
                q_image = QImage(ImageQt(image))
                pixmap = mask_image(q_image)

                main_window.ui.user_avatar.setPixmap(pixmap)

                if len(main_window.ui.Steam_recent_games.children()) > 1:
                    for game in main_window.ui.Steam_recent_games.children()[1:]:
                        game.deleteLater()


                context_menu_items = ["Open", "Hide", "Quit"]

                for action in main_window.tray_menu.actions():
                    if action.text() not in context_menu_items:
                        action.deleteLater()

                main_window.UpdateRecentGamesGUI(self.FetchRecentSteamGames(steamid))
                try:
                    if main_window.ui.Owned_games_content.children()[1].objectName() == "info_label":
                        main_window.ui.Owned_games_content.children()[1].deleteLater()
                except Exception:
                    pass
                self.RunInThread(main_window, "FindOwnedSteamGames", steamid=steamid)

                if main_window.database.conn:
                    sql = "UPDATE user SET steam_id = ? WHERE id = 1;"
                    main_window.database.execute_query(main_window.database.conn, sql, [steamid])

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


    def UpdateSteamGamesNumberInDb(self, main_window, games, isError):
        if isError == False:
            if main_window.database.conn:
                sql = "UPDATE User SET installed_games_from_steam = ? WHERE id = 1"
                main_window.database.execute_query(main_window.database.conn, sql, [games])
        else:
            self.FindSteamGames(main_window, directory=None)


    # Multi-threading
    def RunInThread(self, main_window, func, steamid=None,  directory=None):
        self.thread = QThread()
        self.threads.append(self.thread)

        if func == "FindSteamGames":
            self.worker1 = Worker1(self.steam, main_window, directory)
            self.worker1.moveToThread(self.thread)  

            self.thread.started.connect(self.worker1.FindSteamGamesInThread)
            self.worker1.finished.connect(self.thread.quit)
            self.worker1.finished.connect(self.worker1.deleteLater)
            self.worker1.progress.connect(self.UpdateSteamGamesNumberInDb)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

        elif func == "FindOwnedSteamGames":
            self.worker2 = Worker2(self.steam, main_window, steamid, directory)
            self.worker2.setObjectName("owned_games")
            self.worker2.moveToThread(self.thread)

            self.worker2.progress.connect(main_window.UpdateDb)
            self.worker2.progress.connect(main_window.AddGameToGUI_Owned)
            self.thread.started.connect(self.worker2.FindOwnedSteamGamesInThread)
            self.worker2.finished.connect(self.thread.quit)
            self.worker2.wait()
            self.worker2.finished.connect(self.worker2.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()


class Worker1(QThread):
    finished = Signal()
    progress = Signal(object, int, bool)

    def __init__(self, steam, main_window, directory, parent=None):
        super().__init__(parent)
        self.steam = steam
        self.main_window = main_window
        self.directory = directory

    def FindSteamGamesInThread(self):
        try:
            with open(f"{self.directory}/steamapps/libraryfolders.vdf", "r") as file:
                vdf_with_libraries = file.read()
                parsed_vdf = vdf.loads(vdf_with_libraries)
                libraries = {index: folder['apps'].keys() for index, folder in parsed_vdf['libraryfolders'].items()}

                app_ids = [key for sub_dict in libraries.values() for key in sub_dict]
                app_names = []

                for appid in app_ids:
                    game = self.steam.apps.search_games(appid)

                    if game['apps']:
                        app_names.append([game['apps'][0]['name'], appid])
                    else:
                        app_names.append(['Unknown', appid])

                self.progress.emit(self.main_window, len(app_ids), isError:=False)
                self.main_window.ui.steam_dir_info.setText(f'✔ {len(app_ids)} Games installed')
                self.main_window.ui.steam_dir_info.setStyleSheet(
                    """
                        QLabel {
                            color: rgb(0, 255, 0);
                        }
                    """
                )
                self.main_window.ui.tabWidget.setCurrentWidget(self.main_window.ui.Installed_games)
                self.main_window.FetchInstalledGames(app_ids, app_names, 'steam')
                self.finished.emit()

        except Exception:
            self.progress.emit(self.main_window, str, isError:=True)
            self.finished.emit()


class Worker2(QThread):
    finished = Signal()
    progress = Signal(int, str, str, bytes)

    def __init__(self, steam, main_window, steamid, parent=None):
        super().__init__(parent)
        self.steam = steam
        self.main_window = main_window
        self.steamid = steamid

    def FindOwnedSteamGamesInThread(self):
        try:
            result = self.steam.users.get_owned_games(self.steamid)
            self.main_window.ui.owned_games_quantity.setText(f"{result['game_count']} Games (Only Steam)")
            for game in result["games"]:
                img_icon_url = f"http://media.steampowered.com/steamcommunity/public/images/apps/{game['appid']}/{game['img_icon_url']}.jpg"
                try:
                    response = requests.get(img_icon_url, stream=True)
                    image =  Image.open(response.raw)
                    self.progress.emit(game["appid"], game["name"], 'steam',  image.tobytes())
                except Exception:
                    self.progress.emit(game["appid"], game["name"], 'steam', None)

            self.main_window.ui.tabWidget.setCurrentWidget(self.main_window.ui.Owned_games)
            self.finished.emit()

        except Exception:
            self.finished.emit()


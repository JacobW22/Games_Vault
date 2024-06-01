import os
import vdf
import configparser
import requests

from steam_web_api import Steam as steam_api
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import QFileDialog
from PySide6.QtGui import QImage

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

    def FindSteamGames(self, main_window, directory=f"{os.getenv('SystemDrive')}\Program Files (x86)\Steam"):
        try:
            with open(f"{directory}/steamapps/libraryfolders.vdf", "r") as file:
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


                if main_window.database.conn:
                    sql = "UPDATE User SET installed_games_from_steam = ? WHERE id = 1"
                    main_window.database.execute_query(main_window.database.conn, sql, [(len(app_ids))])


                main_window.ui.steam_dir_info.setText(f'✔ {len(app_ids)} Games installed')
                main_window.ui.steam_dir_info.setStyleSheet(
                    """
                        QLabel {
                            color: rgb(0, 255, 0);
                        }
                    """
                )
                main_window.ui.tabWidget.setCurrentWidget(main_window.ui.All_games)
                main_window.FetchInstalledGames(app_ids, app_names, 'steam')

        except Exception:
            error_msg = ErrorMessage("Can't Find Game Libraries")
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
                self.FindSteamGames(main_window, directory)


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

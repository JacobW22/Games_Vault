import os
import glob
import json
import configparser

from steam_web_api import Steam
from PySide6.QtWidgets import QFileDialog

from layout.MessageBox import MessageBox
from layout.ErrorMessage import ErrorMessage

# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']
steam = Steam(STEAM_API_KEY)

class Epic:
    def FindEpicGames_Games(self, main_window, manifest_folder = f"{os.getenv('SystemDrive')}\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"):
        try:
            item_files = glob.glob(os.path.join(manifest_folder, '*.item'))
            if not item_files:
                raise Exception("Can't find Epic Games Data Folder")
            app_ids = []
            app_names = []

            for item in item_files:
                with open(item, "r", encoding='utf-8') as file:
                    data = json.load(file)

                    # Check if game is installed
                    if "InstallLocation" in data:
                        install_location = data["InstallLocation"]
                        if os.path.isdir(install_location):
                            app_names.append([data['DisplayName'], data['AppName']])
                            game = steam.apps.search_games(data['DisplayName'])
                            if game['apps']:
                                app_ids.append(game['apps'][0]['id'][0])
                            else:
                                app_ids.append('')

            if main_window.database.conn:
                sql = "UPDATE User SET installed_games_from_epic = ? WHERE id = 1"
                main_window.database.execute_query(main_window.database.conn, sql, [(len(app_ids))])

            main_window.ui.epic_dir_info.setText(f'✔ {len(app_ids)} Games installed')
            main_window.ui.epic_dir_info.setStyleSheet(
                """
                    QLabel {
                        color: rgb(0, 255, 0);
                    }
                """
            )
            main_window.ui.tabWidget.setCurrentWidget(main_window.ui.All_games)
            main_window.FetchInstalledGames(app_ids, app_names, 'epic')

        except Exception:
            error_msg = ErrorMessage("Can't Find Epic Games Program Data Folder")
            error_msg.exec()

            options = QFileDialog.Options()
            options |= QFileDialog.ShowDirsOnly


            info_message = """
                <html><body>
                <center>
                <p>Please select your 'Program Data' folder</p>
                <a style="color: lightblue;" href="https://www.minitool.com/data-recovery/program-data-folder-windows-10.html">How to find my Program Data folder</a>
                </center>
                </body></html>
            """

            msg_box = MessageBox("Epic games", info_message)
            msg_box.exec()

            directory = QFileDialog.getExistingDirectory(
               None,
               "Select Your 'Program Data' folder",
               "",
               options=options,
            )

            if directory:
                self.FindEpicGames_Games(main_window, f"{directory}\Epic\EpicGamesLauncher\Data\Manifests")

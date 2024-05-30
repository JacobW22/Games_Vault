import os
import glob
import json
import configparser

from steam_web_api import Steam
from PySide6.QtWidgets import QFileDialog

from MessageBox import MessageBox
from ErrorMessage import ErrorMessage

# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']
steam = Steam(STEAM_API_KEY)


def FindEpicGames_Games(self, manifest_folder = f"{os.getenv('SystemDrive')}\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"):
    try:
        item_files = glob.glob(os.path.join(manifest_folder, '*.item'))
        if not item_files:
            raise Exception("Can't find Epic Games Data Folder")
        app_ids = []
        app_names = []

        for item in item_files:
            with open(item, "r", encoding='utf-8') as file:
                data = json.load(file)

                # Check what games are installed
                if "InstallLocation" in data:
                    install_location = data["InstallLocation"]
                    if os.path.isdir(install_location):
                        app_names.append([data['DisplayName'], data['AppName']])
                        game = steam.apps.search_games(data['DisplayName'])
                        if game['apps']:
                            app_ids.append(game['apps'][0]['id'][0])
                        else:
                            app_ids.append('')

        if self.database.conn:
            sql = "UPDATE User SET installed_games_from_epic = ? WHERE id = 1"
            self.database.execute_query(self.database.conn, sql, [(len(app_ids))])

        self.ui.epic_dir_info.setText(f'✔ {len(app_ids)} Games installed')
        self.ui.epic_dir_info.setStyleSheet(
            """
                QLabel {
                    color: rgb(0, 255, 0);
                }
            """
        )
        self.ui.tabWidget.setCurrentWidget(self.ui.All_games)
        self.FetchInstalledGames(app_ids, app_names, 'epic')

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
            FindEpicGames_Games(self, f"{directory}\Epic\EpicGamesLauncher\Data\Manifests")

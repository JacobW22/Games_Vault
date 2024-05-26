import os
import glob
import json
import configparser

from steam_web_api import Steam

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox


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

        self.ui.Epic_dir_info.setText(f'✔ Found {len(app_ids)} games')
        self.ui.Epic_dir_info.setStyleSheet(
            """
                QLabel {
                    color: rgb(0, 255, 0);
                }
            """
        )
        self.ui.tabWidget.setCurrentWidget(self.ui.All_games)
        self.FetchInstalledGames(app_ids, app_names, 'epic')

    except Exception:
        self.ShowErrorDialog(f"Can't Find Epic Games Program Data Folder")

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly


        info_message = """
            <html><body>
            <p>Please select your 'Program Data' folder</p>
            <a style="color: lightblue;" href="https://www.minitool.com/data-recovery/program-data-folder-windows-10.html">See how to find Program Data folder</a>
            </body></html>
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Epic games")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(info_message)
        msg_box.exec()


        directory = QFileDialog.getExistingDirectory(
           None,
           "Select Your 'Program Data' folder",
           "",
           options=options,
        )

        if directory:
            FindEpicGames_Games(self, f"{directory}\Epic\EpicGamesLauncher\Data\Manifests")

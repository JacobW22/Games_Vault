import vdf
import configparser

from steam_web_api import Steam
from PySide6.QtWidgets import QFileDialog

# Keys
config = configparser.ConfigParser()
config.read('config.ini')
STEAM_API_KEY = config['API_KEYS']['STEAM_API_KEY']
steam = Steam(STEAM_API_KEY)


def FindSteamGames(self):
    options = QFileDialog.Options()
    options |= QFileDialog.ShowDirsOnly

    directory = QFileDialog.getExistingDirectory(
       None,
       "Select Your Main Steam Directory",
       "",
       options=options
    )

    if directory:
        try:
            with open(f"{directory}/steamapps/libraryfolders.vdf", "r") as file:
                vdf_with_libraries = file.read()
                parsed_vdf = vdf.loads(vdf_with_libraries)
                libraries = {index: folder['apps'].keys() for index, folder in parsed_vdf['libraryfolders'].items()}
                num_of_libraries = len(libraries)

                app_ids = [key for sub_dict in libraries.values() for key in sub_dict]
                app_names = []

                for appid in app_ids:
                    game = steam.apps.search_games(appid)

                    if game['apps']:
                        app_names.append([game['apps'][0]['name'], appid])
                    else:
                        app_names.append(['Unknown', appid])



                if num_of_libraries == 1:
                    self.ui.Steam_dir_info.setText(f'✔ Found {num_of_libraries} Library')
                else:
                    self.ui.Steam_dir_info.setText(f'✔ Found {num_of_libraries} Libraries')

                self.ui.Steam_dir_info.setStyleSheet(
                    """
                        QLabel {
                            color: rgb(0, 255, 0);
                        }
                    """
                )
                self.ui.tabWidget.setCurrentWidget(self.ui.All_games)
                self.FetchInstalledGames(app_ids, app_names, 'steam')

        except Exception as e:
            self.ShowErrorDialog(f"Can't Find Game Libraries In This Location {e}")
    else:
        pass

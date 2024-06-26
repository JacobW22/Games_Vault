import os
import glob
import json

from steam_web_api import Steam

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QThread, Signal, QObject, QSettings

from Logging import LoggingSetup

from layout.MessageBox import MessageBox


# Keys
settings = QSettings((os.path.join(os.path.dirname(__file__), "resources", "config", "config.ini")), QSettings.IniFormat)
STEAM_API_KEY = settings.value("API_KEYS/STEAM_API_KEY")


# Initialize the logger
logger = LoggingSetup.setup_logging()


class Epic(QObject):

    steam = Steam(STEAM_API_KEY)
    threads = []
    closed_dialog = Signal()


    def __init__(self, parent=None):
        super().__init__(parent)



    def FindEpicGames(self, main_window, directory = f"{os.getenv('SystemDrive')}\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"):
        try:
            if not directory:
                raise Exception
            self.RunInThread(main_window, directory, func="FindEpicGames")

        except Exception as e:
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

            options = QFileDialog.ShowDirsOnly
            directory = QFileDialog.getExistingDirectory(
               None,
               "Select Your 'Program Data' folder",
               "",
               options=options,
            )
            if directory:
                self.FindEpicGames(main_window, f"{directory}\Epic\EpicGamesLauncher\Data\Manifests")
            else:
                self.closed_dialog.emit()

            logger.error(f"FindEpicGames: {e}")



    def UpdateEpicGamesNumberInDb(self, main_window, games, isError):
        match isError:
            case False:
                if main_window.database.conn:
                    query = "UPDATE User SET installed_games_from_epic = ? WHERE id = 1"
                    main_window.database.execute_query(main_window.database.conn, query, [games])
            case True:
                self.FindEpicGames(main_window, directory = None)



    # Multi-threading
    def RunInThread(self, main_window, directory, func):
        self.thread = QThread()
        self.threads.append(self.thread)
        self.worker1 = Worker1(self.steam, self.closed_dialog, main_window, directory)
        self.worker1.moveToThread(self.thread)

        if func == "FindEpicGames":
            self.thread.started.connect(self.worker1.FindEpicGamesInThread)
            self.worker1.finished.connect(self.thread.quit)
            self.worker1.finished.connect(self.worker1.deleteLater)
            self.worker1.progress.connect(self.UpdateEpicGamesNumberInDb)
            self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()



class Worker1(QThread):

    finished = Signal()
    progress = Signal(object, int, bool)


    def __init__(self, steam, closed_dialog, main_window, directory, parent=None):
        super().__init__(parent)
        self.steam = steam
        self.main_window = main_window
        self.directory = directory
        self.closed_dialog = closed_dialog



    def FindEpicGamesInThread(self):
        try:
            item_files = glob.glob(os.path.join(self.directory, '*.item'))

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
                            game = self.steam.apps.search_games(data['DisplayName'])
                            if game['apps']:
                                app_ids.append(game['apps'][0]['id'][0])
                            else:
                                app_ids.append('')

            games = len(app_ids)
            self.progress.emit(self.main_window, games, isError:=False)
            self.closed_dialog.emit()

            self.main_window.ui.epic_dir_info.setText(f'✔ {len(app_ids)} Games installed')
            self.main_window.ui.epic_dir_info.setStyleSheet(
                """
                    QLabel {
                        color: rgb(0, 255, 0);
                    }
                """
            )
            self.main_window.ui.tabWidget.setCurrentWidget(self.main_window.ui.Installed_games)
            self.main_window.FetchInstalledGames(app_ids, app_names, 'epic')
            self.finished.emit()

        except Exception as e:
            self.progress.emit(self.main_window, str, isError:=True)
            self.finished.emit()
            logger.error(f"FindEpicGamesInThread: {e}")

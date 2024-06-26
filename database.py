import sqlite3
from sqlite3 import Error
from Logging import LoggingSetup

# Initialize the logger
logger = LoggingSetup.setup_logging()


class Database:

    def __init__(self):
        self.db_file = r"user_data.db"
        self.conn = self.create_connection(r"user_data.db")

        if self.conn:
            self.initialize_database()


    def create_connection(self, db_file):
        """ Create a database connection to the SQLite database specified by db_file """
        conn = None
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            logger.error(f"create_connection: {e}")

        return conn



    def execute_query(self, conn, create_table_sql, values=None):
        """ Create a table """
        try:
            c = conn.cursor()
            if values:
                c.execute(create_table_sql, values)
            else:
                c.execute(create_table_sql)

            conn.commit()
            return c

        except Error as e:
            logger.error(f"execute_query: {e}")



    def initialize_database(self):
        """ Initialize the database with required tables """

        sql_create_user_table  = """
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY,
            steam_id INTEGER,
            widget_last_pos_x REAL,
            widget_last_pos_y REAL,
            widget_last_width INTEGER,
            widget_last_height INTEGER,
            game_cover_img INTEGER,
            owned_game_cover_img INTEGER,
            first_time_visit BOOLEAN NOT NULL,
            installed_games_from_epic INTEGER,
            installed_games_from_steam INTEGER,
            total_user_playtime_in_minutes INTEGER
        );
        """

        sql_insert_into_user_table = """
        INSERT INTO User VALUES (NULL, 0, 0.0, 0.0, 0.0, 0.0, 140, 200, TRUE, 0, 0, 0);
        """

        sql_create_installed_games_table  = """
        CREATE TABLE IF NOT EXISTS Installed_Games (
            user_id INTEGER,
            launch_id TEXT NOT NULL PRIMARY KEY,
            app_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            image BLOB,

            FOREIGN KEY(user_id) REFERENCES User(id)
        );
        """

        sql_create_owned_games_table  = """
        CREATE TABLE IF NOT EXISTS Owned_Games (
            user_id INTEGER NOT NULL,
            launch_id TEXT NOT NULL PRIMARY KEY,
            app_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            image BLOB,
            playtime INTEGER,

            FOREIGN KEY(user_id) REFERENCES User(id)
        );
        """

        self.execute_query(self.conn, sql_create_user_table)
        self.execute_query(self.conn, sql_create_installed_games_table)
        self.execute_query(self.conn, sql_create_owned_games_table)
        self.execute_query(self.conn, sql_insert_into_user_table)



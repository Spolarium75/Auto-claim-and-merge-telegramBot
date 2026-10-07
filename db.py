import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "papaldo.db"


def get_connection():
    DATA_DIR.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection

def migrate_database(connection):
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(jobs)")
    columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    new_columns = {
        "prepared_accounts":
            "INTEGER NOT NULL DEFAULT 0",

        "preparation_failed_accounts":
            "INTEGER NOT NULL DEFAULT 0",

        "redemption_failed_accounts":
            "INTEGER NOT NULL DEFAULT 0",
    }

    for column_name, column_definition in new_columns.items():

        if column_name not in columns:

            cursor.execute(
                f"""
                ALTER TABLE jobs
                ADD COLUMN {column_name}
                {column_definition}
                """
            )

            print(
                f"[DB] Added column: {column_name}"
            )

    connection.commit()

def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usernames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            created_at TEXT NOT NULL,

            UNIQUE(telegram_id, username),

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            telegram_id INTEGER PRIMARY KEY,
            shared_password TEXT,
            updated_at TEXT,

            FOREIGN KEY (telegram_id)
                REFERENCES users(telegram_id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL,

        total_accounts INTEGER NOT NULL,

        prepared_accounts INTEGER NOT NULL DEFAULT 0,
        preparation_failed_accounts INTEGER NOT NULL DEFAULT 0,

        completed_accounts INTEGER NOT NULL DEFAULT 0,
        success_accounts INTEGER NOT NULL DEFAULT 0,
        redemption_failed_accounts INTEGER NOT NULL DEFAULT 0,

        last_success_username TEXT,
        last_success_line INTEGER,

        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,

        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        )

    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            line_number INTEGER NOT NULL,

            status TEXT NOT NULL,
            error_code TEXT,
            error_message TEXT,

            started_at TEXT,
            finished_at TEXT,

            FOREIGN KEY (job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS websites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,

        name TEXT NOT NULL,
        url TEXT NOT NULL,

        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,

        FOREIGN KEY (telegram_id)
            REFERENCES users(telegram_id)
            ON DELETE CASCADE
        )
    """)

    connection.commit()

    migrate_database(connection)

    connection.close()
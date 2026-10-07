from datetime import datetime, timezone
from pathlib import Path

from db import get_connection


def utc_now():
    return datetime.now(timezone.utc).isoformat()


# =========================
# Users
# =========================

def ensure_user(telegram_id):
    connection = get_connection()

    connection.execute(
        """
        INSERT OR IGNORE INTO users (telegram_id, created_at)
        VALUES (?, ?)
        """,
        (telegram_id, utc_now())
    )

    connection.commit()
    connection.close()


# =========================
# Usernames
# =========================

def replace_usernames(telegram_id, usernames):
    connection = get_connection()

    try:
        connection.execute(
            "DELETE FROM usernames WHERE telegram_id = ?",
            (telegram_id,)
        )

        for line_number, username in enumerate(
            usernames,
            start=1
        ):
            connection.execute(
                """
                INSERT INTO usernames
                (telegram_id, username, line_number, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    telegram_id,
                    username,
                    line_number,
                    utc_now()
                )
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_usernames(telegram_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT username, line_number
        FROM usernames
        WHERE telegram_id = ?
        ORDER BY line_number ASC
        """,
        (telegram_id,)
    ).fetchall()

    connection.close()

    return rows


def get_username_count(telegram_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM usernames
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    ).fetchone()

    connection.close()

    return row["count"]

def delete_usernames(telegram_id):
    connection = get_connection()

    try:
        connection.execute(
            """
            DELETE FROM usernames
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# =========================
# Password
# =========================

def save_shared_password(
    telegram_id,
    password
):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO settings
        (telegram_id, shared_password, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            shared_password = excluded.shared_password,
            updated_at = excluded.updated_at
        """,
        (
            telegram_id,
            password,
            utc_now()
        )
    )

    connection.commit()
    connection.close()


def has_shared_password(telegram_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT shared_password
        FROM settings
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    ).fetchone()

    connection.close()

    return bool(
        row and row["shared_password"]
    )


def get_shared_password(telegram_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT shared_password
        FROM settings
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    ).fetchone()

    connection.close()

    if not row:
        return None

    return row["shared_password"]


# =========================
# Balances
# =========================

BALANCE_FILE = Path("balances.txt")
REDEMPTION_VALUE = 10


def _read_balances():
    balances = {}

    if not BALANCE_FILE.exists():
        return balances

    with BALANCE_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or "|" not in line:
                continue

            username, amount = line.rsplit("|", 1)
            username = username.strip()

            if not username:
                continue

            try:
                balances[username] = float(amount.strip())
            except ValueError:
                continue

    return balances


def _write_balances(balances):
    temp_file = BALANCE_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        for username, amount in sorted(balances.items()):
            file.write(f"{username}|{amount:g}\n")

    temp_file.replace(BALANCE_FILE)


def get_balance(username):
    balances = _read_balances()
    return balances.get(username, 0)


def get_balances():
    return _read_balances()


def get_total_balance():
    return sum(_read_balances().values())


def set_balance(username, amount):
    balances = _read_balances()
    balances[username] = float(amount)
    _write_balances(balances)


def add_balance(username, amount=REDEMPTION_VALUE):
    balances = _read_balances()
    balances[username] = balances.get(username, 0) + float(amount)
    _write_balances(balances)


# =========================
# Jobs
# =========================

def create_job(
    telegram_id,
    code,
    usernames
):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO jobs (
                telegram_id,
                code,
                status,
                total_accounts,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                code,
                "queued",
                len(usernames),
                utc_now()
            )
        )

        job_id = cursor.lastrowid

        for username, line_number in usernames:

            cursor.execute(
                """
                INSERT INTO job_accounts (
                    job_id,
                    username,
                    line_number,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    job_id,
                    username,
                    line_number,
                    "queued"
                )
            )

        connection.commit()

        return job_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def set_job_code(
    job_id,
    code
):
    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE jobs
            SET code = ?
            WHERE id = ?
            """,
            (
                code,
                job_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_active_job(telegram_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE telegram_id = ?
          AND status IN ('queued', 'running')
        ORDER BY id DESC
        LIMIT 1
        """,
        (telegram_id,)
    ).fetchone()

    connection.close()

    return row


def mark_job_running(job_id):
    connection = get_connection()

    connection.execute(
        """
        UPDATE jobs
        SET status = 'running',
            started_at = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            job_id
        )
    )

    connection.commit()
    connection.close()


def get_next_queued_account(job_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM job_accounts
        WHERE job_id = ?
          AND status = 'queued'
        ORDER BY line_number ASC
        LIMIT 1
        """,
        (job_id,)
    ).fetchone()

    connection.close()

    return row


def mark_account_running(account_id):
    connection = get_connection()

    connection.execute(
        """
        UPDATE job_accounts
        SET status = 'running',
            started_at = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            account_id
        )
    )

    connection.commit()
    connection.close()

def mark_account_prepared(job_id, account_id):
    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE job_accounts
            SET status = 'prepared'
            WHERE id = ? AND job_id = ?
            """,
            (account_id, job_id)
        )

        connection.execute(
            """
            UPDATE jobs
            SET prepared_accounts = prepared_accounts + 1
            WHERE id = ?
            """,
            (job_id,)
        )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def mark_preparation_failed(
    job_id,
    account_id,
    error_code=None,
    error_message=None
):
    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE job_accounts
            SET status = 'preparation_failed',
                error_code = ?,
                error_message = ?,
                finished_at = ?
            WHERE id = ? AND job_id = ?
            """,
            (
                error_code,
                error_message,
                datetime.now(timezone.utc).isoformat(),
                account_id,
                job_id
            )
        )

        connection.execute(
            """
            UPDATE jobs
            SET preparation_failed_accounts =
                preparation_failed_accounts + 1
            WHERE id = ?
            """,
            (job_id,)
        )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def finish_account(
    job_id,
    account_id,
    success,
    error_code=None,
    error_message=None
):
    connection = get_connection()

    try:
        account = connection.execute(
            """
            SELECT username, line_number, status
            FROM job_accounts
            WHERE id = ? AND job_id = ?
            """,
            (account_id, job_id)
        ).fetchone()

        if not account:
            return

        # Prevent duplicate finalization if an account has
        # already been counted.
        if account["status"] in (
            "success",
            "redemption_failed"
        ):
            return

        now = datetime.now(timezone.utc).isoformat()
        status = "success" if success else "redemption_failed"

        connection.execute(
            """
            UPDATE job_accounts
            SET status = ?,
                error_code = ?,
                error_message = ?,
                finished_at = ?
            WHERE id = ? AND job_id = ?
            """,
            (
                status,
                error_code,
                error_message,
                now,
                account_id,
                job_id
            )
        )

        connection.execute(
            """
            UPDATE jobs
            SET completed_accounts = completed_accounts + 1,
                success_accounts = success_accounts + ?,
                redemption_failed_accounts =
                    redemption_failed_accounts + ?
            WHERE id = ?
            """,
            (
                1 if success else 0,
                0 if success else 1,
                job_id
            )
        )

        if success:
            connection.execute(
                """
                UPDATE jobs
                SET last_success_username = ?,
                    last_success_line = ?
                WHERE id = ?
                """,
                (
                    account["username"],
                    account["line_number"],
                    job_id
                )
            )

        connection.commit()

        # Balance is persistent and keyed by username.
        if success:
            add_balance(account["username"], REDEMPTION_VALUE)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def mark_job_completed(job_id):
    connection = get_connection()

    connection.execute(
        """
        UPDATE jobs
        SET status = 'completed',
            finished_at = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            job_id
        )
    )

    connection.commit()
    connection.close()


def mark_job_stopped(job_id):
    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE jobs
            SET status = 'stopped',
                finished_at = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                job_id
            )
        )

        connection.execute(
            """
            UPDATE job_accounts
            SET status = 'cancelled',
                finished_at = ?
            WHERE job_id = ?
              AND status = 'queued'
            """,
            (
                utc_now(),
                job_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_job(job_id):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()

    connection.close()

    return row


def get_job_accounts(job_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM job_accounts
        WHERE job_id = ?
        ORDER BY line_number ASC
        """,
        (job_id,)
    ).fetchall()

    connection.close()

    return rows


def get_job_history(
    telegram_id,
    limit=10
):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            telegram_id,
            limit
        )
    ).fetchall()

    connection.close()

    return rows


# =========================
# Websites
# =========================

def create_website(
    telegram_id,
    name,
    url
):
    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO websites (
                telegram_id,
                name,
                url,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                name,
                url,
                utc_now(),
                utc_now()
            )
        )

        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_websites(telegram_id):
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM websites
        WHERE telegram_id = ?
        ORDER BY id ASC
        """,
        (telegram_id,)
    ).fetchall()

    connection.close()

    return rows


def get_website(
    telegram_id,
    website_id
):
    connection = get_connection()

    row = connection.execute(
        """
        SELECT *
        FROM websites
        WHERE id = ?
          AND telegram_id = ?
        """,
        (
            website_id,
            telegram_id
        )
    ).fetchone()

    connection.close()

    return row


def update_website(
    telegram_id,
    website_id,
    name,
    url
):
    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE websites
            SET name = ?,
                url = ?,
                updated_at = ?
            WHERE id = ?
              AND telegram_id = ?
            """,
            (
                name,
                url,
                utc_now(),
                website_id,
                telegram_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_website(
    telegram_id,
    website_id
):
    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM websites
            WHERE id = ?
              AND telegram_id = ?
            """,
            (
                website_id,
                telegram_id
            )
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
from job_manager import job_manager
from merge_manager import merge_manager
from merge_worker import merge_worker
from repositories import (
    get_usernames,
    get_active_job,
    get_job,
    get_job_history,
    ensure_user,
    replace_usernames,
    delete_usernames,
    get_username_count,
    has_shared_password,
    save_shared_password,
    create_website,
    get_websites,
    get_website,
    update_website,
    delete_website,
    set_job_code,
    get_balances,
    get_balance,
    get_total_balance,
    set_balance,
    get_shared_password,
)
import asyncio
import logging
from telegram.error import NetworkError

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN
from db import initialize_database

from keyboards import (
    main_menu,
    website_menu,
    accounts_menu,
    delete_usernames_menu,
    balance_menu,
    merge_menu,
)

from session import (
    get_session,
    get_state,
    set_state,
    clear_session,
)


# =========================
# Telegram send retry helper
# =========================

async def safe_reply_text(
    message,
    *args,
    retries=3,
    **kwargs
):
    """
    Send a Telegram reply with exponential-backoff retries
    for transient Telegram/network connection failures.

    Retry delays: 1s, 2s, 4s.
    Non-network Telegram errors are not retried.
    """
    for attempt in range(retries):
        try:
            return await message.reply_text(
                *args,
                **kwargs
            )

        except NetworkError as error:
            if attempt >= retries - 1:
                raise

            delay = 2 ** attempt

            logging.warning(
                "Telegram send failed "
                "(attempt %s/%s): %s. "
                "Retrying in %ss...",
                attempt + 1,
                retries,
                type(error).__name__,
                delay
            )

            await asyncio.sleep(delay)


# =========================
# Conversation states
# =========================

WAITING_FOR_USERNAME_FILE = (
    "waiting_for_username_file"
)

WAITING_FOR_PASSWORD = (
    "waiting_for_password"
)

WAITING_FOR_REDEEM_CODE = (
    "waiting_for_redeem_code"
)

WAITING_FOR_WEBSITE_NAME = (
    "waiting_for_website_name"
)

WAITING_FOR_WEBSITE_URL = (
    "waiting_for_website_url"
)

WAITING_FOR_BALANCE_EDIT = (
    "waiting_for_balance_edit"
)


# =========================
# /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    ensure_user(user_id)

    clear_session(user_id)

    await safe_reply_text(update.message, 
        "🤖 Welcome to Papaldo!\n\n"
        "Choose an option below:",
        reply_markup=main_menu(),
    )


# =========================
# Button handler
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    action = query.data

    ensure_user(user_id)
    
        # -------------------------
    # Accounts
    # -------------------------

    if action == "accounts":

        await safe_reply_text(query.message, 
            "👤 Accounts\n\n"
            "Manage your current username list.",
            reply_markup=accounts_menu()
        )

        return

    # -------------------------
    # Add usernames
    # -------------------------

    if action == "add_usernames":

        set_state(
            user_id,
            WAITING_FOR_USERNAME_FILE
        )

        await safe_reply_text(query.message, 
            "👤 Add Usernames\n\n"
            "Please upload a TXT file containing "
            "one username per line."
        )

    
    # -------------------------
    # View usernames
    # -------------------------

    elif action == "view_usernames":

        username_rows = get_usernames(user_id)

        if not username_rows:

            await safe_reply_text(query.message, 
                "📋 Current Username List\n\n"
                "No usernames are currently stored."
            )

            return

        lines = [
            "📋 Current Username List\n",
            f"👤 Total: {len(username_rows)}\n"
        ]

        # Show first 20 usernames only.
        for row in username_rows[:20]:

            lines.append(
                f"{row['line_number']}. "
                f"{row['username']}"
            )

        if len(username_rows) > 20:

            lines.append(
                f"\n... and "
                f"{len(username_rows) - 20} more."
            )

        await safe_reply_text(query.message, 
            "\n".join(lines),
            reply_markup=accounts_menu()
        )

        return
    
    # -------------------------
    # Delete usernames
    # -------------------------

    elif action == "delete_usernames":

        active_job = get_active_job(user_id)

        if active_job:

            await safe_reply_text(query.message, 
                "⚠️ You cannot delete the username "
                "list while a Papaldo job is active.\n\n"
                f"Active job: #{active_job['id']}"
            )

            return

        username_count = get_username_count(
            user_id
        )

        if username_count == 0:

            await safe_reply_text(query.message, 
                "📋 There is no username list "
                "to delete.",
                reply_markup=accounts_menu()
            )

            return

        await safe_reply_text(query.message, 
            "⚠️ Delete Current Username List?\n\n"
            f"👤 Accounts: {username_count}\n\n"
            "This will permanently remove the "
            "current username list.",
            reply_markup=delete_usernames_menu()
        )

        return
    
        # -------------------------
    # Confirm delete usernames
    # -------------------------

    elif action == "confirm_delete_usernames":

        active_job = get_active_job(user_id)

        if active_job:

            await safe_reply_text(query.message, 
                "⚠️ You cannot delete the username "
                "list while a Papaldo job is active."
            )

            return

        username_count = get_username_count(
            user_id
        )

        if username_count == 0:

            await safe_reply_text(query.message, 
                "📋 There is no username list "
                "to delete.",
                reply_markup=accounts_menu()
            )

            return

        try:

            delete_usernames(user_id)

        except Exception as error:

            await safe_reply_text(query.message, 
                "❌ Failed to delete the username list.\n\n"
                f"Error: {type(error).__name__}",
                reply_markup=accounts_menu()
            )

            return

        await safe_reply_text(query.message, 
            "✅ Username list deleted successfully.\n\n"
            f"🗑️ Removed: {username_count} username(s).",
            reply_markup=accounts_menu()
        )

        return
    
        # -------------------------
    # Cancel delete usernames
    # -------------------------

    elif action == "cancel_delete_usernames":

        await safe_reply_text(query.message, 
            "❌ Delete cancelled.",
            reply_markup=accounts_menu()
        )

        return

    elif action == "add_password":

        set_state(
            user_id,
            WAITING_FOR_PASSWORD
        )

        await safe_reply_text(query.message, 
            "🔑 Add / Update Password\n\n"
            "Please enter the password that will "
            "be used for all usernames."
        )

    # -------------------------
    # Websites
    # -------------------------

    elif action == "websites":

        await safe_reply_text(query.message, 
            "🌐 Website Manager\n\n"
            "Manage the websites used for Papaldo "
            "automation.",
            reply_markup=website_menu()
        )

    # -------------------------
    # Add Website
    # -------------------------

    elif action == "add_website":

        set_state(
            user_id,
            WAITING_FOR_WEBSITE_NAME
        )

        await safe_reply_text(query.message, 
            "➕ Add Website\n\n"
            "Please enter a name for this website."
        )
        
    elif action == "stop_preparation":

        job = get_active_job(user_id)

        if not job:
            await safe_reply_text(query.message, 
                "❌ No active Papaldo job."
            )
            return

        await job_manager.stop_preparation(
            job["id"]
        )

        job = get_job(job["id"])

        prepared = job_manager.prepared_accounts.get(
            job["id"],
            {}
        )

        if not prepared:
            clear_session(user_id)

            await safe_reply_text(query.message, 
                "❌ Preparation stopped.\n\n"
                "No accounts were successfully prepared.",
                reply_markup=main_menu()
            )

            return

        session = get_session(user_id)

        session["temp"]["job_id"] = job["id"]

        set_state(
            user_id,
            WAITING_FOR_REDEEM_CODE
        )

        await safe_reply_text(query.message, 
            "⏹ Preparation stopped.\n\n"
            f"🆔 Job: #{job['id']}\n"
            f"✅ Prepared accounts: {len(prepared)}\n\n"
            "Only these prepared accounts will be "
            "used for redemption.\n\n"
            "🎁 Please send the Papaldo code."
        )    

    # -------------------------
    # Start Papaldo
    # -------------------------

    elif action == "start_papaldo":

        # Check for existing active job
        active_job = get_active_job(user_id)

        if active_job:

            await safe_reply_text(query.message, 
                "⚠️ You already have an active "
                f"Papaldo job #{active_job['id']}.\n\n"
                f"Status: "
                f"{active_job['status'].upper()}"
            )

            return

        # Check usernames
        username_count = get_username_count(
            user_id
        )

        if username_count == 0:

            await safe_reply_text(query.message, 
                "❌ Cannot start Papaldo.\n\n"
                "No usernames have been added yet.\n\n"
                "Please add your username list first."
            )

            return

        # Check password
        password_exists = has_shared_password(
            user_id
        )

        if not password_exists:

            await safe_reply_text(query.message, 
                "❌ Cannot start Papaldo.\n\n"
                "No password has been configured yet.\n\n"
                "Please add a password first."
            )

            return

        # Check website
        websites = get_websites(user_id)

        if not websites:

            await safe_reply_text(query.message, 
                "❌ Cannot start Papaldo.\n\n"
                "No website has been configured yet.\n\n"
                "Please add a website first."
            )

            return

        # Get usernames
        username_rows = get_usernames(
            user_id
        )

        usernames = [
            (
                row["username"],
                row["line_number"]
            )
            for row in username_rows
        ]

        # Start preparation
        preparation_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            "⏹ Stop Preparing",
            callback_data="stop_preparation"
        )
    ]
])

        await safe_reply_text(query.message, 
            "🚀 Starting Papaldo preparation...\n\n"
            f"👤 Accounts: {len(usernames)}\n"
            "🔐 Logging into accounts...\n"
            "🌐 Opening Gift Code section...\n\n"
            "You can stop preparation at any time.\n"
            "Already prepared accounts will remain ready.",
            reply_markup=preparation_keyboard
        )

        try:

            job_id = await job_manager.start_job(
                telegram_id=user_id,
                usernames=usernames
            )

        except Exception as error:

            clear_session(user_id)

            await safe_reply_text(query.message, 
                "❌ Failed to start Papaldo.\n\n"
                f"Error: {type(error).__name__}",
                reply_markup=main_menu()
            )

            return

        await job_manager.wait_for_preparation(
            job_id
        )

        # Stop Preparing was already handled
        # by the callback handler.
        if job_manager.consume_preparation_stopped(job_id):
            return

        # Check final job state
        job = get_job(job_id)

        if not job:

            clear_session(user_id)

            await safe_reply_text(query.message, 
                "❌ Papaldo job could not be found.",
                reply_markup=main_menu()
            )

            return

        # If job was stopped / failed during
        # preparation.
        if job["status"] != "running":

            clear_session(user_id)

            await safe_reply_text(query.message, 
                "❌ Papaldo preparation did not "
                "complete.\n\n"
                f"Job: #{job_id}\n"
                f"Status: {job['status'].upper()}",
                reply_markup=main_menu()
            )

            return

        # Check prepared accounts
        prepared = job_manager.prepared_accounts.get(
            job_id,
            {}
        )

        if not prepared:

            clear_session(user_id)

            await safe_reply_text(query.message, 
                "❌ No accounts were successfully "
                "prepared.\n\n"
                f"Job: #{job_id}\n"
                f"Preparation failed: "
                f"{job['preparation_failed_accounts']}",
                reply_markup=main_menu()
            )

            return

        # Wait for code
        session = get_session(user_id)

        session["temp"]["job_id"] = job_id
        
        set_state(
            user_id,
            WAITING_FOR_REDEEM_CODE
        )

        await safe_reply_text(query.message, 
            "✅ Preparation finished!\n\n"
            f"🆔 Job: #{job_id}\n\n"
            "🔐 Preparation\n"
            f"✅ Ready: "
            f"{job['prepared_accounts']}\n"
            f"❌ Failed: "
            f"{job['preparation_failed_accounts']}\n\n"
            "🎁 Please send the Papaldo code "
            "to begin redemption."
        )

    # -------------------------
    # Merge
    # -------------------------

    elif action == "merge":

        await safe_reply_text(
            query.message,
            "🔀 Merge\n\n"
            "Merge accounts through Fan Tan "
            "head-to-head matches.",
            reply_markup=merge_menu()
        )

        return

    elif action == "start_merge":

        # Get configured usernames
        username_rows = get_usernames(user_id)

        if len(username_rows) < 2:

            await safe_reply_text(
                query.message,
                "❌ Cannot start Merge.\n\n"
                "You need at least 2 usernames "
                "in your account list.",
                reply_markup=merge_menu()
            )

            return

        usernames = [
            row["username"]
            for row in username_rows
        ]

        # Check for existing Merge job
        if merge_manager.is_active(user_id):

            summary = merge_manager.get_summary(
                user_id
            )

            await safe_reply_text(
                query.message,
                "⚠️ You already have an active "
                "Merge job.\n\n"
                f"🥊 {summary['current_account']} "
                f"vs {summary['opponent']}\n"
                f"🔄 Round: "
                f"{summary['round_number']}",
                reply_markup=merge_menu()
            )

            return

        # Check website
        websites = get_websites(user_id)

        if not websites:

            await safe_reply_text(
                query.message,
                "❌ Cannot start Merge.\n\n"
                "No website has been configured yet.\n\n"
                "Please add a website first.",
                reply_markup=merge_menu()
            )

            return

        # Check shared password
        password = get_shared_password(user_id)

        if not password:

            await safe_reply_text(
                query.message,
                "❌ Cannot start Merge.\n\n"
                "No shared password has been configured yet.",
                reply_markup=merge_menu()
            )

            return

        # Use the first configured website
        website = websites[0]

        # Create Merge job
        job = merge_manager.start_merge(
            telegram_id=user_id,
            usernames=usernames
        )

        if not job:

            await safe_reply_text(
                query.message,
                "❌ Failed to create Merge job.",
                reply_markup=merge_menu()
            )

            return

        await safe_reply_text(
            query.message,
            "🔀 Merge started!\n\n"
            f"👤 Accounts: {len(usernames)}\n"
            f"🌐 Website: {website['name']}\n\n"
            "🔐 Preparing and logging in accounts...\n"
            "🎲 The Merge chain will run automatically.\n\n"
            "Please wait for the final result."
        )

        # ==================================================
        # Phase 6.8 — Run Complete Merge Chain
        # ==================================================
        # IMPORTANT:
        # run_merge_chain() owns the account preparation flow.
        # It uses the existing merge_worker.open_account() and
        # merge_worker.login_account() implementations that were
        # already used by the working 6.7 bot flow.
        #
        # Do NOT manually open/login accounts here.
        # ==================================================

        try:

            result = await merge_manager.run_merge_chain(
                telegram_id=user_id,
                password=password,
                url=website["url"],
                batch_size=3,
                round_timeout=120,
                settlement_delay=1.0
            )

        except Exception as error:

            merge_manager.stop(user_id)

            await safe_reply_text(
                query.message,
                "❌ Merge chain failed unexpectedly.\n\n"
                f"⚠️ Error: {type(error).__name__}",
                reply_markup=merge_menu()
            )

            return

        if not result:

            await safe_reply_text(
                query.message,
                "🛑 Merge chain did not produce a result.",
                reply_markup=merge_menu()
            )

            return

        if not result.get("success"):

            stage = result.get(
                "stage",
                result.get("status", "unknown")
            )

            error = result.get(
                "error",
                "Unknown error"
            )

            rounds = result.get(
                "rounds",
                0
            )

            survivor = result.get(
                "survivor"
            )

            await safe_reply_text(
                query.message,
                "❌ Merge chain failed.\n\n"
                f"📍 Stage: {stage}\n"
                f"🔄 Rounds completed: {rounds}\n"
                f"👤 Survivor: {survivor or 'None'}\n"
                f"⚠️ {error}",
                reply_markup=merge_menu()
            )

            return

        # Final successful result
        final_winner = result.get(
            "final_winner",
            "Unknown"
        )

        final_balance = result.get(
            "final_balance"
        )

        rounds = result.get(
            "rounds",
            0
        )

        if final_balance is None:
            balance_text = "Unknown"
        else:
            balance_text = f"₱{final_balance:.2f}"

        await safe_reply_text(
            query.message,
            "🏆 Merge Chain Finished!\n\n"
            f"👤 Starting accounts: {len(usernames)}\n"
            f"🔄 Total rounds: {rounds}\n\n"
            f"🏆 Final Winner: {final_winner}\n"
            f"💰 Final Balance: {balance_text}",
            reply_markup=merge_menu()
        )

    # -------------------------
    # My Balance
    # -------------------------

    elif action == "my_balance":

        await safe_reply_text(query.message, 
            "💰 My Balance\n\n"
            "Manage your accumulated username balances.",
            reply_markup=balance_menu()
        )

        return

    elif action == "view_balances":

        balances = get_balances()

        if not balances:
            await safe_reply_text(query.message, 
                "📋 No balances yet.",
                reply_markup=balance_menu()
            )
            return

        lines = ["📋 Account Balances\n"]

        for username, amount in sorted(
            balances.items()
        ):
            lines.append(
                f"{username} — ₱{amount:g}"
            )

        await safe_reply_text(query.message, 
            "\n".join(lines),
            reply_markup=balance_menu()
        )

        return

    elif action == "total_balance":

        total = get_total_balance()

        await safe_reply_text(query.message, 
            "💰 Total Balance\n\n"
            f"₱{total:g}",
            reply_markup=balance_menu()
        )

        return

    elif action == "edit_balance":

        set_state(
            user_id,
            WAITING_FOR_BALANCE_EDIT
        )

        await safe_reply_text(query.message, 
            "✏️ Edit Balance\n\n"
            "Send the username and new balance "
            "in this format:\n\n"
            "username | 50\n\n"
            "This replaces the existing balance."
        )

        return

    # -------------------------
    # Current jobs
    # -------------------------

    elif action == "current_jobs":

        job = get_active_job(user_id)

        if not job:

            await safe_reply_text(query.message, 
                "📊 No active Papaldo job."
            )

            return

        await safe_reply_text(query.message, 
            "📊 Current Papaldo Job\n\n"
            f"🆔 Job: #{job['id']}\n"
            f"Status: {job['status'].upper()}\n\n"

            "🔐 Preparation\n"
            f"✅ Ready: "
            f"{job['prepared_accounts']}\n"
            f"❌ Failed: "
            f"{job['preparation_failed_accounts']}\n\n"

            "🎁 Redemption\n"
            f"✅ Successful: "
            f"{job['success_accounts']}\n"
            f"❌ Failed: "
            f"{job['redemption_failed_accounts']}\n"
            f"📊 Completed: "
            f"{job['completed_accounts']}/"
            f"{job['prepared_accounts']}\n\n"

            f"💰 Successfully Claimed: "
            f"₱{job['success_accounts'] * 10:g}\n"
            f"💳 Total Balance: "
            f"₱{get_total_balance():g}\n\n"

            "Last successful:\n"
            f"{job['last_success_username'] or 'None'}\n"
            "Line: "
            f"{job['last_success_line'] or 'None'}"
        )

    # -------------------------
    # History
    # -------------------------

    elif action == "history":

        jobs = get_job_history(user_id)

        if not jobs:

            await safe_reply_text(query.message, 
                "📜 No Papaldo history yet."
            )

            return

        lines = [
            "📜 Papaldo History\n"
        ]

        for job in jobs:

            lines.append(
            f"#{job['id']} — "
            f"{job['status'].upper()}\n"
            f"Accounts: "
            f"{job['total_accounts']}\n\n"
            "🔐 Preparation\n"
            f"✅ Ready: "
            f"{job['prepared_accounts']} "
            f"❌ Failed: "
            f"{job['preparation_failed_accounts']}\n\n"
            "🎁 Redemption\n"
            f"✅ Successful: "
            f"{job['success_accounts']} "
            f"❌ Failed: "
            f"{job['redemption_failed_accounts']}\n"
        )

        await safe_reply_text(query.message, 
            "\n".join(lines)
        )

    # -------------------------
    # Stop
    # -------------------------

    elif action == "stop":

        job = get_active_job(user_id)

        if not job:

            await safe_reply_text(query.message, 
                "🛑 No active Papaldo job."
            )

            return

        await job_manager.stop_job(
            job["id"]
        )

        clear_session(user_id)

        stopped_job = get_job(
            job["id"]
        )

        await safe_reply_text(query.message, 
            "🛑 Papaldo stopped.\n\n"
            f"🆔 Job: #{stopped_job['id']}\n"
            f"👤 Total accounts: "
            f"{stopped_job['total_accounts']}\n\n"

            "🔐 Preparation\n"
            f"✅ Ready: "
            f"{stopped_job['prepared_accounts']}\n"
            f"❌ Failed: "
            f"{stopped_job['preparation_failed_accounts']}\n\n"

            "🎁 Redemption\n"
            f"✅ Successful: "
            f"{stopped_job['success_accounts']}\n"
            f"❌ Failed: "
            f"{stopped_job['redemption_failed_accounts']}\n"
            f"📊 Completed: "
            f"{stopped_job['completed_accounts']}/"
            f"{stopped_job['prepared_accounts']}\n\n"

            f"💰 Successfully Claimed: "
            f"₱{stopped_job['success_accounts'] * 10:g}\n"
            f"💳 Total Balance: "
            f"₱{get_total_balance():g}\n\n"

            "Last successful:\n"
            f"{stopped_job['last_success_username'] or 'None'}\n"
            "Line: "
            f"{stopped_job['last_success_line'] or 'None'}",
            reply_markup=main_menu()
        )

    # -------------------------
    # Help
    # -------------------------

    elif action == "help":

        await safe_reply_text(query.message, 
            "❓ Help\n\n"
            "▶️ Start Papaldo\n"
            "Prepare all configured accounts and "
            "navigate them to the Gift Code section.\n\n"
            "👤 Add Usernames\n"
            "Upload a TXT file containing one "
            "username per line.\n\n"
            "🔑 Add / Update Password\n"
            "Set the shared password used by all "
            "usernames.\n\n"
            "🌐 Websites\n"
            "Manage the website used by Papaldo.\n\n"
            "📊 Current Jobs\n"
            "View the active job.\n\n"
            "📜 History\n"
            "View previous jobs.\n\n"
            "🛑 Stop\n"
            "Stop the active job."
        )


# =========================
# Document handler
# =========================

async def document_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    state = get_state(user_id)

    if state != WAITING_FOR_USERNAME_FILE:

        await safe_reply_text(update.message, 
            "❌ I wasn't expecting a username "
            "file right now."
        )

        return

    document = update.message.document

    if not document.file_name.lower().endswith(
        ".txt"
    ):

        await safe_reply_text(update.message, 
            "❌ Please upload a .txt file."
        )

        return

    telegram_file = await document.get_file()

    file_bytes = (
        await telegram_file.download_as_bytearray()
    )

    try:

        text = bytes(file_bytes).decode(
            "utf-8-sig"
        )

    except UnicodeDecodeError:

        clear_session(user_id)

        await safe_reply_text(update.message, 
            "❌ The file could not be read "
            "as UTF-8 text.",
            reply_markup=main_menu()
        )

        return

    usernames = []

    for line in text.splitlines():

        username = line.strip()

        if username:
            usernames.append(username)

    if not usernames:

        clear_session(user_id)

        await safe_reply_text(update.message, 
            "❌ The file contains no usernames.",
            reply_markup=main_menu()
        )

        return

    # Remove duplicates while preserving order.
    usernames = list(
        dict.fromkeys(usernames)
    )

    try:

        replace_usernames(
            user_id,
            usernames
        )

    except Exception:

        clear_session(user_id)

        await safe_reply_text(update.message, 
            "❌ Failed to save the usernames.",
            reply_markup=main_menu()
        )

        return

    clear_session(user_id)

    await safe_reply_text(update.message, 
        "✅ Username list updated successfully.\n\n"
        f"👤 Total usernames: "
        f"{len(usernames)}",
        reply_markup=main_menu()
    )


# =========================
# Text handler
# =========================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    state = get_state(user_id)

    text = update.message.text.strip()

    # -------------------------
    # Password
    # -------------------------

    if state == WAITING_FOR_PASSWORD:

        if not text:

            await safe_reply_text(update.message, 
                "❌ Password cannot be empty."
            )

            return

        save_shared_password(
            user_id,
            text
        )

        clear_session(user_id)

        username_count = get_username_count(
            user_id
        )

        await safe_reply_text(update.message, 
            "✅ Password updated successfully.\n\n"
            f"👤 It will be used for "
            f"{username_count} stored username(s).",
            reply_markup=main_menu()
        )

        return

    # -------------------------
    # Website name
    # -------------------------

    if state == WAITING_FOR_WEBSITE_NAME:

        if not text:

            await safe_reply_text(update.message, 
                "❌ Website name cannot be empty."
            )

            return

        session = get_session(user_id)

        session["temp"]["website_name"] = text

        set_state(
            user_id,
            WAITING_FOR_WEBSITE_URL
        )

        await safe_reply_text(update.message, 
            "🔗 Now enter the website URL.\n\n"
            "Example:\n"
            "https://example.com"
        )

        return

    # -------------------------
    # Website URL
    # -------------------------

    if state == WAITING_FOR_WEBSITE_URL:

        if not text:

            await safe_reply_text(update.message, 
                "❌ Website URL cannot be empty."
            )

            return

        session = get_session(user_id)

        name = session["temp"].get(
            "website_name"
        )

        if not name:

            clear_session(user_id)

            await safe_reply_text(update.message, 
                "❌ Website setup expired.",
                reply_markup=main_menu()
            )

            return

        create_website(
            telegram_id=user_id,
            name=name,
            url=text
        )

        clear_session(user_id)

        await safe_reply_text(update.message, 
            "✅ Website added successfully!\n\n"
            f"🌐 Name: {name}\n"
            f"🔗 URL: {text}",
            reply_markup=website_menu()
        )

        return

    # -------------------------
    # Balance Edit
    # -------------------------

    if state == WAITING_FOR_BALANCE_EDIT:

        parts = text.split("|", 1)

        if len(parts) != 2:

            await safe_reply_text(update.message, 
                "❌ Invalid format.\n\n"
                "Use:\n"
                "username | 50"
            )

            return

        username = parts[0].strip()
        amount_text = parts[1].strip()

        if not username:

            await safe_reply_text(update.message, 
                "❌ Username cannot be empty."
            )

            return

        try:
            amount = float(amount_text)

            if amount < 0:
                raise ValueError

        except ValueError:

            await safe_reply_text(update.message, 
                "❌ Balance must be a valid "
                "non-negative number."
            )

            return

        set_balance(
            username,
            amount
        )

        clear_session(user_id)

        await safe_reply_text(update.message, 
            "✅ Balance updated!\n\n"
            f"👤 Username: {username}\n"
            f"💰 Balance: ₱{amount:g}\n"
            f"💳 Total Balance: "
            f"₱{get_total_balance():g}",
            reply_markup=balance_menu()
        )

        return

    # -------------------------
    # Papaldo Redeem Code
    # -------------------------

    if state == WAITING_FOR_REDEEM_CODE:
        
        session = get_session(user_id)

        job_id = session["temp"].get(
            "job_id"
        )

        if not job_id:

            clear_session(user_id)

            await safe_reply_text(update.message, 
                "❌ No active Papaldo job "
                "was found.",
                reply_markup=main_menu()
            )

            return

        job = get_job(job_id)

        if not job:

            clear_session(user_id)

            await safe_reply_text(update.message, 
                "❌ Papaldo job could not be found.",
                reply_markup=main_menu()
            )

            return

        if job["status"] != "running":

            clear_session(user_id)

            await safe_reply_text(update.message, 
                "❌ This Papaldo job is no longer "
                "active.\n\n"
                f"Status: "
                f"{job['status'].upper()}",
                reply_markup=main_menu()
            )

            return

        if not text:

            await safe_reply_text(update.message, 
                "❌ Code cannot be empty."
            )

            return

        # Save the code to the job.
        set_job_code(
            job_id,
            text
        )

        # Prevent another code message from
        # starting another redemption.
        clear_session(user_id)

        await safe_reply_text(update.message, 
            "🎁 Code received!\n\n"
            f"🚀 Starting redemption for "
            f"Job #{job_id}...\n\n"
            "Please wait."
        )

        try:
            
            await job_manager.submit_code(
                job_id,
                text
            )

        except Exception as error:

            await safe_reply_text(update.message, 
                "❌ An error occurred while "
                "redeeming the code.\n\n"
                f"Error: {type(error).__name__}",
                reply_markup=main_menu()
            )

            return

        # Get final result
        final_job = get_job(job_id)

        if not final_job:

            await safe_reply_text(update.message, 
                "❌ Could not retrieve the final "
                "job result.",
                reply_markup=main_menu()
            )

            return

        await safe_reply_text(update.message, 
            "🏁 Papaldo job finished!\n\n"
            f"🆔 Job: #{final_job['id']}\n"
            f"👤 Total accounts: "
            f"{final_job['total_accounts']}\n"
            f"❌ Failed: "
            f"{final_job['total_accounts'] - final_job['success_accounts']}\n\n"

            "🔐 Preparation\n"
            f"✅ Ready: "
            f"{final_job['prepared_accounts']}\n"
            f"❌ Failed: "
            f"{final_job['preparation_failed_accounts']}\n\n"

            "🎁 Redemption\n"
            f"✅ Successful: "
            f"{final_job['success_accounts']}\n"
            f"❌ Failed: "
            f"{final_job['redemption_failed_accounts']}\n\n"

            f"💰 Successfully Claimed: "
            f"₱{final_job['success_accounts'] * 10:g}\n"
            f"💳 Total Balance: "
            f"₱{get_total_balance():g}\n\n"

            "⭐ Last successful:\n"
            f"{final_job['last_success_username'] or 'None'}\n"
            "Line: "
            f"{final_job['last_success_line'] or 'None'}",
            reply_markup=main_menu()
        )

        return

    # -------------------------
    # Unknown text
    # -------------------------

    await safe_reply_text(update.message, 
        "Please choose an option from the menu.",
        reply_markup=main_menu(),
    )


# =========================
# Main
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logging.exception(
        "Telegram bot error",
        exc_info=context.error
    )

def main():

    initialize_database()

    application = (
    Application
    .builder()
    .token(BOT_TOKEN)
    .connect_timeout(30)
    .read_timeout(30)
    .write_timeout(30)
    .pool_timeout(30)
    .build()
)
    
    application.add_error_handler(error_handler)

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            document_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    print(
        "Papaldo bot is running..."
    )

    application.run_polling()


if __name__ == "__main__":
    main()
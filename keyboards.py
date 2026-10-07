from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("▶️ Start Papaldo", callback_data="start_papaldo")
        ],
        [   InlineKeyboardButton("👤 Accounts", callback_data="accounts"),
            InlineKeyboardButton("🔑 Add / Update Password", callback_data="add_password")],
        [
            InlineKeyboardButton("🌐 Websites", callback_data="websites")
        ],
        [
            InlineKeyboardButton("💰 My Balance", callback_data="my_balance")
        ],
        [
            InlineKeyboardButton("🔀 Merge", callback_data="merge")
        ],
        [
            InlineKeyboardButton("📊 Current Jobs", callback_data="current_jobs"),
            InlineKeyboardButton("📜 History", callback_data="history")
        ],
        [
            InlineKeyboardButton("🛑 Stop", callback_data="stop"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def delete_usernames_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🗑️ Yes, Delete",
                callback_data="confirm_delete_usernames"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="cancel_delete_usernames"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def accounts_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Add Username List", callback_data="add_usernames")],
        [InlineKeyboardButton("📋 View Current List", callback_data="view_usernames")],
        [InlineKeyboardButton("🗑️ Delete Current List", callback_data="delete_usernames")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main_menu")]
    ]

    return InlineKeyboardMarkup(keyboard)

def confirm_job():
    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ Start",
                callback_data="confirm_start_job"
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="cancel_start_job"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def website_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "➕ Add Website",
                callback_data="add_website"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 View Websites",
                callback_data="view_websites"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ Update Website",
                callback_data="update_website"
            ),
            InlineKeyboardButton(
                "🗑️ Remove Website",
                callback_data="remove_website"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_main_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def balance_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "📋 View Balances",
                callback_data="view_balances"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ Edit Balance",
                callback_data="edit_balance"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Total Balance",
                callback_data="total_balance"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_main_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

def merge_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "▶️ Start Merge",
                callback_data="start_merge"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_main_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

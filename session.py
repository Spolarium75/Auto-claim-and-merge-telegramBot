sessions = {}


def get_session(telegram_id):
    if telegram_id not in sessions:
        sessions[telegram_id] = {
            "state": None,
            "temp": {}
        }

    return sessions[telegram_id]


def set_state(telegram_id, state):
    session = get_session(telegram_id)

    print(f"[SESSION] SET STATE: {state}")

    session["state"] = state


def get_state(telegram_id):
    session = get_session(telegram_id)
    return session["state"]


def clear_session(telegram_id):
    print(f"[SESSION] CLEAR SESSION: {telegram_id}")
    sessions.pop(telegram_id, None)
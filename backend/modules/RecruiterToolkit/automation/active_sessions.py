import uuid

ACTIVE_SESSIONS = {}


def create_session(browser, page):

    session_id = str(uuid.uuid4())

    ACTIVE_SESSIONS[session_id] = {
        "browser": browser,
        "page": page,
    }

    return session_id


def get_session(session_id):

    return ACTIVE_SESSIONS.get(session_id)


def remove_session(session_id):

    if session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_id]

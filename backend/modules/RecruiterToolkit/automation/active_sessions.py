import uuid
import threading
import time


ACTIVE_SESSIONS = {}

_SESSION_LOCK = threading.Lock()

# Keep verification sessions alive for 15 minutes.
SESSION_TIMEOUT = 15 * 60


def create_session(
    browser,
    page,
    company,
    location,
    max_profiles
):
    session_id = str(uuid.uuid4())

    session = {
        "session_id": session_id,
        "browser": browser,
        "page": page,
        "company": company,
        "location": location,
        "max_profiles": max_profiles,
        "created_at": time.time(),
        "last_activity": time.time(),
    }

    with _SESSION_LOCK:
        ACTIVE_SESSIONS[session_id] = session

    print("=" * 60)
    print("LINKEDIN SESSION CREATED")
    print("=" * 60)
    print("Session ID :", session_id)
    print("Company    :", company)
    print("Location   :", location)
    print("=" * 60)

    return session_id


def get_session(session_id):

    with _SESSION_LOCK:

        session = ACTIVE_SESSIONS.get(session_id)

        if not session:
            return None

        # Refresh activity timestamp
        session["last_activity"] = time.time()

        return session


def remove_session(session_id):

    with _SESSION_LOCK:

        if session_id in ACTIVE_SESSIONS:

            del ACTIVE_SESSIONS[session_id]

            print(
                f"LinkedIn session removed: {session_id}"
            )


def session_exists(session_id):

    with _SESSION_LOCK:

        return session_id in ACTIVE_SESSIONS


def update_activity(session_id):

    with _SESSION_LOCK:

        session = ACTIVE_SESSIONS.get(session_id)

        if session:

            session["last_activity"] = time.time()

            return True

    return False


def get_active_sessions():

    with _SESSION_LOCK:

        return list(ACTIVE_SESSIONS.keys())


def cleanup_expired_sessions():

    now = time.time()

    expired = []

    with _SESSION_LOCK:

        for session_id, session in list(
            ACTIVE_SESSIONS.items()
        ):

            last_activity = session.get(
                "last_activity",
                session.get("created_at", now)
            )

            if now - last_activity > SESSION_TIMEOUT:

                expired.append(
                    session_id
                )

    for session_id in expired:

        session = get_session(session_id)

        if not session:
            continue

        browser = session.get("browser")

        try:

            if browser:
                browser.close()

        except Exception as ex:

            print(
                "Error closing expired LinkedIn browser:",
                ex
            )

        remove_session(session_id)

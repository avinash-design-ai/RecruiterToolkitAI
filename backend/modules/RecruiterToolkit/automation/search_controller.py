STOP_REQUESTED = False


def request_stop():
    global STOP_REQUESTED
    STOP_REQUESTED = True


def reset():
    global STOP_REQUESTED
    STOP_REQUESTED = False


def should_stop():
    return STOP_REQUESTED

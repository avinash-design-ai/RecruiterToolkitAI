from functools import wraps
from pathlib import Path
from datetime import datetime
import traceback

from automation.config import SCREENSHOT_DIR
from automation.logger import log


class FailureHandler:

    @staticmethod
    def execute(page, action_name):

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):

                try:
                    return func(*args, **kwargs)

                except Exception as e:

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    screenshot = SCREENSHOT_DIR / f"{action_name}_{timestamp}.png"
                    html = SCREENSHOT_DIR / f"{action_name}_{timestamp}.html"

                    try:
                        page.screenshot(
                            path=str(screenshot),
                            full_page=True
                        )
                    except Exception:
                        pass

                    try:
                        Path(html).write_text(
                            page.content(),
                            encoding="utf-8"
                        )
                    except Exception:
                        pass

                    log.error("=" * 70)
                    log.error(f"ACTION : {action_name}")
                    log.error(f"URL    : {page.url}")
                    log.error(f"ERROR  : {e}")
                    log.error(traceback.format_exc())
                    log.error(f"Screenshot : {screenshot}")
                    log.error(f"HTML       : {html}")
                    log.error("=" * 70)

                    raise

            return wrapper

        return decorator

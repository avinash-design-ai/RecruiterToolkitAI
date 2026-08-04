from pathlib import Path
from datetime import datetime

import pandas as pd

from automation.config import EXPORT_DIR
from automation.logger import log


class Exporter:

    @staticmethod
    def export_csv(records, filename=None):

        if not records:
            log.warning("No records to export.")
            return None

        if filename is None:
            filename = f"export_{datetime.now():%Y%m%d_%H%M%S}.csv"

        filepath = EXPORT_DIR / filename

        df = pd.DataFrame(records)

        df.to_csv(filepath, index=False, encoding="utf-8-sig")

        log.success(f"CSV exported -> {filepath}")

        return filepath

    @staticmethod
    def export_excel(records, filename=None):

        if not records:
            log.warning("No records to export.")
            return None

        if filename is None:
            filename = f"export_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

        filepath = EXPORT_DIR / filename

        df = pd.DataFrame(records)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        log.success(f"Excel exported -> {filepath}")

        return filepath

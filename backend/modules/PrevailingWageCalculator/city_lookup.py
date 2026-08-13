"""
city_lookup.py

City → County + State lookup
"""

import sqlite3
import sys
from pathlib import Path


def get_base_dir():
    """
    Return the application base directory.

    Development:
        backend/modules/PrevailingWageCalculator

    PyInstaller:
        PyInstaller extraction directory
    """

    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)

    # city_lookup.py is:
    # PrevailingWageCalculator/city_lookup.py
    #
    # Database is:
    # PrevailingWageCalculator/data/us_cities.db

    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()

DB_FILE = BASE_DIR / "data" / "us_cities.db"


class CityLookup:

    def __init__(self):

        print("City database path:")
        print(DB_FILE)

        if not DB_FILE.exists():
            raise FileNotFoundError(
                f"City database not found:\n{DB_FILE}"
            )

        self.conn = sqlite3.connect(str(DB_FILE))
        self.cursor = self.conn.cursor()

    # ----------------------------------------
    # City → County + State
    # ----------------------------------------

    def lookup(self, city):

        city = city.strip()

        if not city:
            raise Exception("City cannot be empty.")

        # Exact match
        self.cursor.execute(
            """
            SELECT county, state
            FROM cities
            WHERE LOWER(city)=LOWER(?)
            LIMIT 1
            """,
            (city,)
        )

        row = self.cursor.fetchone()

        # Remove ", XX" state abbreviation
        #
        # Example:
        # Pittsburgh, PA → Pittsburgh
        #
        if row is None and "," in city:

            base_city = city.rsplit(",", 1)[0].strip()

            self.cursor.execute(
                """
                SELECT county, state
                FROM cities
                WHERE LOWER(city)=LOWER(?)
                LIMIT 1
                """,
                (base_city,)
            )

            row = self.cursor.fetchone()

        if row is None:

            raise Exception(
                f"City '{city}' not found."
            )

        county = row[0].strip()
        state = row[1].strip().upper()

        # Normalize County
        if (
            state != "CONNECTICUT"
            and state != "DISTRICT OF COLUMBIA"
            and not county.endswith("County")
        ):
            county += " County"

        return county, state

    # ----------------------------------------

    def close(self):

        self.conn.close()

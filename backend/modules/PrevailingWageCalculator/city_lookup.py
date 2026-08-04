"""
city_lookup.py

City → County + State lookup
"""

import sqlite3
from pathlib import Path

# Folder where city_lookup.py is located
BASE_DIR = Path(__file__).resolve().parent

# Absolute path to the SQLite database
DB_FILE = BASE_DIR / "data" / "us_cities.db"


class CityLookup:

    def __init__(self):

        self.conn = sqlite3.connect(DB_FILE)

        self.cursor = self.conn.cursor()

    # ----------------------------------------

    def lookup(self, city):

        city = city.strip()

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

        if row is None:

            raise Exception(

                f"City '{city}' not found."

            )

        county = row[0].strip()
        state = row[1].strip().upper()

        # Most states in AREA_MAP expect "County"
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


if __name__ == "__main__":

    lookup = CityLookup()

    county, state = lookup.lookup("Plano")

    print(county)

    print(state)

    lookup.close()

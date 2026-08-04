"""
build_database.py

Creates us_cities.db from uscities.csv

Run only once.
"""

import csv
import sqlite3
import os


CSV_FILE = "uscities.csv"

DB_FOLDER = "data"

DB_FILE = os.path.join(DB_FOLDER, "us_cities.db")


def main():

    os.makedirs(DB_FOLDER, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)

    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS cities")

    cur.execute("""
        CREATE TABLE cities (

            city TEXT,

            county TEXT,

            state TEXT

        )
    """)

    count = 0

    with open(CSV_FILE, newline="", encoding="utf-8") as file:

        reader = csv.DictReader(file)

        for row in reader:

            city = row["city"].strip()

            county = row["county_name"].strip()

            state = row["state_name"].strip().upper()

            cur.execute(

                """
                INSERT INTO cities
                VALUES (?,?,?)
                """,

                (

                    city,

                    county,

                    state

                )

            )

            count += 1

    cur.execute(

        """
        CREATE INDEX idx_city
        ON cities(city)
        """
    )

    conn.commit()

    conn.close()

    print("=" * 50)
    print("Database Created Successfully")
    print("Rows Imported :", count)
    print("Database :", DB_FILE)
    print("=" * 50)


if __name__ == "__main__":

    main()

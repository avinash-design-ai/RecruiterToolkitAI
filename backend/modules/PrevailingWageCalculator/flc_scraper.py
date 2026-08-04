"""
flc_scraper.py

Desktop wrapper around FLAG website
"""

from .flag import FlagWebsite
from .parser import WageParser
from .city_lookup import CityLookup
from .mappings import (
    AREA_MAP,
    UI_OCCUPATION_MAP
)


class FLCScraper:

    def __init__(self):

        self.website = FlagWebsite()
        self.parser = WageParser()
        self.lookup = CityLookup()

    # ----------------------------------------------------

    def get_wages(self, city):

        city = city.strip()

        # --------------------------------------------
        # Lookup County + State from SQLite
        # --------------------------------------------

        county, state = self.lookup.lookup(city)

        print("=" * 50)
        print("City   :", city)
        print("County :", county)
        print("State  :", state)
        print("Exists :", (state, county) in AREA_MAP)
        print("=" * 50)

        area_key = (state, county)

        if area_key not in AREA_MAP:

            raise Exception(

                f"AREA_MAP does not contain:\n\n"

                f"{state}\n"

                f"{county}"

            )

        results = {

            "county": county,

            "state": state

        }

        # --------------------------------------------
        # Search FLAG
        # --------------------------------------------

        for job_title, soc_code in UI_OCCUPATION_MAP.items():

            print("\nSearching :", job_title)

            table = self.website.search(

                soc_code,

                state,

                county

            )

            wage = self.parser.level2_wage(table)

            print("Extracted Wage :", wage)

            results[job_title] = wage

        print("\n================ RESULTS ================")
        print(results)
        print("=========================================\n")

        return results

    # ----------------------------------------------------

    def close(self):

        try:
            self.lookup.close()
        except:
            pass

        try:
            self.website.close()
        except:
            pass

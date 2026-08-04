"""
Prevailing Wage Updater
Version 1.0
"""

import os

from excel import ExcelManager
from flag import FlagWebsite
from mappings import OCCUPATION_MAP, STATE_MAP
from parser import WageParser
from logger import Logger


def main():

    print("=" * 60)
    print("Prevailing Wage Updater")
    print("=" * 60)

    excel_file = os.path.join(
        "..",
        "input",
        "Prevailing Wage 07.01.2025.xlsx"
    )

    output_file = os.path.join(
        "..",
        "output",
        "Prevailing Wage Updated.xlsx"
    )

    log_file = os.path.join(
        "..",
        "logs",
        "run.log"
    )

    logger = Logger()
    logger.start(log_file)

    excel = ExcelManager(excel_file)

    website = FlagWebsite()

    parser = WageParser()

    logger.log(f"Total Locations : {excel.total_rows()}")

    try:

        for row in excel.get_rows():

            city = row["city"]
            county = row["county"]

            logger.log("")
            logger.log("=" * 60)
            logger.log(city)
            logger.log("=" * 60)

            if city not in STATE_MAP:

                logger.log(f"State mapping not found for {city}")
                continue

            state = STATE_MAP[city]

            for column, occupation in OCCUPATION_MAP.items():

                logger.log(f"Searching {occupation}")

                try:

                    table = website.search(

                        occupation,

                        state,

                        county

                    )

                    wage = parser.level2_annual(table)

                    logger.log(f"Level II Wage : {wage}")

                    excel.write(

                        row["row"],

                        column,

                        wage

                    )

                except Exception as e:

                    logger.log(
                        f"FAILED : {occupation} : {str(e)}"
                    )

        excel.save(output_file)

        logger.log("")
        logger.log("Workbook Saved Successfully")

    finally:

        website.close()

        logger.close()


if __name__ == "__main__":
    main()

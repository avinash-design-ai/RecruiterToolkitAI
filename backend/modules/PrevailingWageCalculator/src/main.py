"""
Prevailing Wage Bulk Updater

Used by:
1. Bulk desktop UI
2. Optional command-line execution

The desktop UI supplies the input Excel file.
No hardcoded input workbook is used by the UI.
"""

import os

from .excel import ExcelManager
from .flag import FlagWebsite
from .mappings import OCCUPATION_MAP, STATE_MAP
from .parser import WageParser
from .logger import Logger
from ..city_lookup import CityLookup


def run_bulk_calculation(
    excel_file,
    output_file,
    log_file,
    progress_callback=None
):
    """
    Process ONLY the cities contained in the Excel file selected
    by the user.

    Excel format:
        Column A = City
        Column B = County (optional)

    If County is blank, CityLookup is used to determine:
        County + State

    progress_callback:
        callback(completed, total, city, status)
    """

    logger = Logger()

    excel = None
    website = None
    lookup = None

    try:

        # --------------------------------------------------
        # Validate input
        # --------------------------------------------------

        if not excel_file:
            raise Exception("No Excel file was selected.")

        if not os.path.isfile(excel_file):
            raise Exception(
                f"Input Excel file not found:\n{excel_file}"
            )

        logger.start(log_file)

        logger.log("=" * 60)
        logger.log("Prevailing Wage Bulk Calculator")
        logger.log("=" * 60)
        logger.log(f"Input  : {excel_file}")
        logger.log(f"Output : {output_file}")
        logger.log("")

        # --------------------------------------------------
        # Open selected workbook
        # --------------------------------------------------

        excel = ExcelManager(excel_file)

        rows = excel.get_rows()

        total = len(rows)

        if total == 0:
            raise Exception(
                "No city records were found in the selected Excel file."
            )

        logger.log(
            f"Total Locations : {total}"
        )

        # --------------------------------------------------
        # Start FLAG browser
        # --------------------------------------------------

        website = FlagWebsite()

        parser = WageParser()

        lookup = CityLookup()

        completed = 0

        # --------------------------------------------------
        # Process ONLY selected workbook rows
        # --------------------------------------------------

        for row in rows:

            city = row["city"].strip()
            county = row["county"].strip()

            logger.log("")
            logger.log("=" * 60)
            logger.log(f"Processing City : {city}")
            logger.log("=" * 60)

            if progress_callback:

                progress_callback(
                    completed,
                    total,
                    city,
                    "Processing city..."
                )

            # --------------------------------------------------
            # Determine County + State
            # --------------------------------------------------

            try:

                # ----------------------------------------------
                # County supplied by user
                # ----------------------------------------------

                if county:

                    logger.log(
                        f"County from Excel : {county}"
                    )

                    # First try exact city mapping.
                    state = STATE_MAP.get(city)

                    # If the city is not in STATE_MAP,
                    # use CityLookup to determine state.
                    if not state:

                        logger.log(
                            "City not found in STATE_MAP."
                        )

                        logger.log(
                            "Using CityLookup for state..."
                        )

                        _, state = lookup.lookup(city)

                # ----------------------------------------------
                # County missing
                # ----------------------------------------------

                else:

                    logger.log(
                        "County is blank. "
                        "Looking up CityLookup..."
                    )

                    county, state = lookup.lookup(city)

                    county = county.strip()
                    state = state.strip().upper()

                    logger.log(
                        f"County automatically found : {county}"
                    )

                    logger.log(
                        f"State automatically found  : {state}"
                    )

                    # --------------------------------------------------
                    # Write automatically detected county back to Excel
                    # Column B = County
                    # --------------------------------------------------

                    excel.write(
                        row["row"],
                        "B",
                        county
                    )

                    logger.log(
                        f"County written to Excel column : B"
                    )

                # --------------------------------------------------
                # Final cleanup
                # --------------------------------------------------

                county = county.strip()
                state = state.strip().upper()

                logger.log(
                    f"Final Location : {city} | "
                    f"{county} | {state}"
                )

            except Exception as e:

                logger.log(
                    f"LOCATION LOOKUP FAILED : {city} : {str(e)}"
                )

                if progress_callback:

                    progress_callback(
                        completed,
                        total,
                        city,
                        f"Location lookup failed: {str(e)}"
                    )

                # IMPORTANT:
                # Continue to the NEXT row.
                continue

            # --------------------------------------------------
            # Search all occupations
            # --------------------------------------------------

            for column, occupation in OCCUPATION_MAP.items():

                logger.log(
                    f"Searching {occupation}"
                )

                if progress_callback:

                    progress_callback(
                        completed,
                        total,
                        city,
                        f"Searching {occupation}..."
                    )

                try:

                    table = website.search(
                        occupation,
                        state,
                        county
                    )

                    wage = parser.level2_annual(
                        table
                    )

                    logger.log(
                        f"Level II Wage : {wage}"
                    )

                    # ------------------------------------------
                    # Write wage into selected workbook
                    # ------------------------------------------

                    excel.write(
                        row["row"],
                        column,
                        wage
                    )

                    logger.log(
                        f"Written to Excel column : {column}"
                    )

                except Exception as e:

                    logger.log(
                        f"FAILED : {occupation} : {str(e)}"
                    )

                    # Continue with the next occupation
                    continue

            # --------------------------------------------------
            # City completed
            # --------------------------------------------------

            completed += 1

            logger.log(
                f"Completed : {city}"
            )

            if progress_callback:

                progress_callback(
                    completed,
                    total,
                    city,
                    "Completed"
                )

        # --------------------------------------------------
        # Save output
        # --------------------------------------------------

        output_dir = os.path.dirname(
            os.path.abspath(output_file)
        )

        if output_dir:
            os.makedirs(
                output_dir,
                exist_ok=True
            )

        excel.save(output_file)

        logger.log("")
        logger.log("=" * 60)
        logger.log("Workbook Saved Successfully")
        logger.log(f"Output : {output_file}")
        logger.log("=" * 60)

        return output_file

    finally:

        # --------------------------------------------------
        # Close FLAG browser
        # --------------------------------------------------

        if website:

            try:
                website.close()
            except Exception:
                pass

        # --------------------------------------------------
        # Close CityLookup
        # --------------------------------------------------

        if lookup:

            try:
                lookup.close()
            except Exception:
                pass

        # --------------------------------------------------
        # Close logger
        # --------------------------------------------------

        try:
            logger.close()
        except Exception:
            pass


# ==========================================================
# OPTIONAL COMMAND-LINE TEST
# ==========================================================

def main():

    print("=" * 60)
    print("Prevailing Wage Bulk Calculator")
    print("=" * 60)

    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    # This is ONLY for manual developer testing.
    # The desktop UI does NOT use this path.

    excel_file = os.path.join(
        base_dir,
        "input",
        "Prevailing Wage 07.01.2025.xlsx"
    )

    output_file = os.path.join(
        base_dir,
        "output",
        "Prevailing Wage Updated.xlsx"
    )

    log_file = os.path.join(
        base_dir,
        "logs",
        "run.log"
    )

    run_bulk_calculation(
        excel_file=excel_file,
        output_file=output_file,
        log_file=log_file
    )


if __name__ == "__main__":
    main()

import re


class WageParser:

    def level2_wage(self, table_text):

        for line in table_text.splitlines():

            line = line.strip()

            if line.startswith("II"):

                wages = re.findall(
                    r"\$[\d,]+\.\d{2}",
                    line
                )

                if len(wages) >= 2:

                    return {

                        "hourly": wages[0],

                        "annual": wages[1]

                    }

        return {

            "hourly": "",

            "annual": ""

        }

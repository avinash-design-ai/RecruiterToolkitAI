import re


class WageParser:

    def level2_annual(self, table_text):

        lines = table_text.splitlines()

        for line in lines:

            line = line.strip()

            parts = line.split()

            if len(parts) == 0:
                continue

            if parts[0] == "II":

                matches = re.findall(
                    r'US\$[\d,.]+(?:\.\d{2})?',
                    line
                )

                if len(matches) >= 2:

                    return matches[1]

        return ""

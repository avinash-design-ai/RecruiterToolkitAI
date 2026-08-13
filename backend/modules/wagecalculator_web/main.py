from .excel import ExcelReader
from .flag import FlagWebsite

def main(file_path=None, output_path=None):

    print("=" * 60)
    print("Recruiter's Toolkit v2")
    print("=" * 60)

    excel = ExcelReader(file_path)

    flag = FlagWebsite()

    try:

        headers = excel.get_headers()

        rows = excel.get_rows()

        total = len(rows)

        current = 1

        for row_data in rows:

            print()
            print("=" * 60)
            print(f"{current} / {total}")
            print(row_data["city"])
            print("=" * 60)

            for column, occupation in headers.items():

                print()
                print("Searching", occupation)

                try:

                    wage = flag.search(

                        occupation,

                        row_data["city"],

                        row_data["county"]

                    )

                    excel.write(

                        row_data["row"],

                        column,

                        wage

                    )

                except Exception as e:

                    print()

                    print("FAILED :", e)

                    excel.write(

                        row_data["row"],

                        column,

                        "ERROR"

                    )

            current += 1

        output = excel.save(output_path)

        print()
        print("=" * 60)
        print("Completed Successfully")
        print("=" * 60)
        print(output)

        return output

    finally:

        flag.close()


if __name__ == "__main__":

    main()

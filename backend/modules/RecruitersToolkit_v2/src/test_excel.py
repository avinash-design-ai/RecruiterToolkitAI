from excel import ExcelReader

excel = ExcelReader()

print(excel.input_file)

print()

print(excel.get_headers())

print()

print(excel.get_rows()[:5])

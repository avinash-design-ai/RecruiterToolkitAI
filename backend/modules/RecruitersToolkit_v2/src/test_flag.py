from flag import FlagWebsite

flag = FlagWebsite()

wage = flag.search(

    "15-1252",

    "Boston, MA",

    "Suffolk County"

)

print()

print("Returned Wage :", wage)

flag.close()

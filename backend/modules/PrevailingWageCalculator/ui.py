"""
ui.py
Prevailing Wage Calculator
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from flc_scraper import FLCScraper


class PrevailingWageUI:

    def __init__(self, root):

        self.root = root

        self.root.title("Prevailing Wage Calculator")

        self.root.geometry("650x560")

        self.root.resizable(False, False)

        self.build_ui()

    # ----------------------------------------------------

    def build_ui(self):

        padding = 10

        title = tk.Label(

            self.root,

            text="Prevailing Wage Calculator",

            font=("Segoe UI", 16, "bold")

        )

        title.pack(pady=15)

        # ----------------------------

        frame = tk.Frame(self.root)

        frame.pack(fill="x", padx=20)

        tk.Label(

            frame,

            text="City",

            font=("Segoe UI",10,"bold")

        ).grid(row=0,column=0,sticky="w")

        self.city = tk.Entry(

            frame,

            width=40,

            font=("Segoe UI",11)

        )

        self.city.grid(

            row=1,

            column=0,

            padx=5,

            pady=5

        )

        tk.Button(

            frame,

            text="Get Wage",

            width=15,

            command=self.get_wages

        ).grid(

            row=1,

            column=1,

            padx=15

        )

        # ----------------------------

        result = tk.LabelFrame(

            self.root,

            text="Results",

            padx=15,

            pady=15

        )

        result.pack(

            fill="both",

            padx=20,

            pady=20

        )

        self.county = self.create_field(

            result,

            "County",

            0

        )

        self.software = self.create_field(

            result,

            "Software Developer (Level II)",

            1

        )

        self.programmer = self.create_field(

            result,

            "Computer Programmer (Level II)",

            2

        )

        self.analyst = self.create_field(

            result,

            "Computer Systems Analyst (Level II)",

            3

        )

        self.data_engineer = self.create_field(
            result,
            "Data Engineer (Level II)",
            4
        )        

        bottom = tk.Frame(self.root)

        bottom.pack(pady=15)

        tk.Button(

            bottom,

            text="Copy",

            width=15,

            command=self.copy_results

        ).grid(row=0,column=0,padx=5)

        tk.Button(

            bottom,

            text="Exit",

            width=15,

            command=self.root.destroy

        ).grid(row=0,column=1,padx=5)

    # ----------------------------------------------------

    def create_field(self,parent,label,row):

        tk.Label(

            parent,

            text=label,

            font=("Segoe UI",10,"bold")

        ).grid(

            row=row,

            column=0,

            sticky="w",

            pady=8

        )

        entry = tk.Entry(

            parent,

            width=45,

            font=("Segoe UI",11),

            state="normal"

        )

        entry.grid(

            row=row,

            column=1,

            padx=10

        )

        return entry

    # ----------------------------------------------------

    def set_value(self,entry,value):

        entry.config(state="normal")

        entry.delete(0,"end")

        entry.insert(0,value)

        entry.config(state="readonly")

    # ----------------------------------------------------

    def get_wages(self):

        city = self.city.get().strip()

        if city == "":

            messagebox.showwarning(

                "Input",

                "Please enter a city."

            )

            return

        scraper = None

        try:

            scraper = FLCScraper()

            result = scraper.get_wages(city)

            self.set_value(

                self.county,

                result["county"]

            )

            self.set_value(

                self.software,

                f'{result["Software Developer"]["hourly"]} /hr    {result["Software Developer"]["annual"]} /yr'

            )
            
            self.set_value(

                self.programmer,

                f'{result["Computer Programmer"]["hourly"]} /hr    {result["Computer Programmer"]["annual"]} /yr'

            )

            self.set_value(

                self.analyst,

                f'{result["Computer Systems Analyst"]["hourly"]} /hr    {result["Computer Systems Analyst"]["annual"]} /yr'

            )

            self.set_value(

                self.data_engineer,

                f'{result["Data Engineer"]["hourly"]} /hr    {result["Data Engineer"]["annual"]} /yr'

            )

        except Exception as ex:

            messagebox.showerror(

                "Error",

                str(ex)

            )

        finally:

            if scraper:

                scraper.close()

    # ----------------------------------------------------

    def copy_results(self):

        text = f"""County : {self.county.get()}

        Software Developer : {self.software.get()}

        Computer Programmer : {self.programmer.get()}

        Computer Systems Analyst : {self.analyst.get()}

        Data Engineer : {self.data_engineer.get()}"""

        self.root.clipboard_clear()

        self.root.clipboard_append(text)

        messagebox.showinfo(

            "Copied",

            "Results copied to clipboard."

        )

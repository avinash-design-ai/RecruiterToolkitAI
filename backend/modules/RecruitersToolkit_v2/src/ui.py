import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from main import main


class RecruitersToolkitUI:

    def __init__(self):

        self.root = tk.Tk()

        self.root.title("Recruiter's Toolkit")

        self.root.geometry("700x220")

        self.root.resizable(False, False)

        self.input_file = tk.StringVar()

        self.output_file = tk.StringVar()

        self.status = tk.StringVar(value="Ready")

        self.build_ui()

        self.root.mainloop()

    # --------------------------------------------------

    def build_ui(self):

        tk.Label(

            self.root,

            text="Prevailing Wage Updater",

            font=("Segoe UI", 16, "bold")

        ).pack(pady=10)

        # ---------------- INPUT ----------------

        frame1 = tk.Frame(self.root)

        frame1.pack(pady=5)

        tk.Label(

            frame1,

            text="Input Excel",

            width=12,

            anchor="w"

        ).grid(row=0, column=0)

        tk.Entry(

            frame1,

            width=60,

            textvariable=self.input_file

        ).grid(row=0, column=1)

        ttk.Button(

            frame1,

            text="Browse",

            command=self.select_input

        ).grid(row=0, column=2, padx=5)

        # ---------------- OUTPUT ----------------

        frame2 = tk.Frame(self.root)

        frame2.pack(pady=5)

        tk.Label(

            frame2,

            text="Save As",

            width=12,

            anchor="w"

        ).grid(row=0, column=0)

        tk.Entry(

            frame2,

            width=60,

            textvariable=self.output_file

        ).grid(row=0, column=1)

        ttk.Button(

            frame2,

            text="Browse",

            command=self.select_output

        ).grid(row=0, column=2, padx=5)

        # ---------------- STATUS ----------------

        tk.Label(

            self.root,

            textvariable=self.status

        ).pack(pady=10)

        # ---------------- BUTTON ----------------

        ttk.Button(

            self.root,

            text="START",

            width=20,

            command=self.start

        ).pack()

    # --------------------------------------------------

    def select_input(self):

        file = filedialog.askopenfilename(

            title="Select Prevailing Wage File",

            filetypes=[

                ("Excel Workbook", "*.xlsx")

            ]

        )

        if file:

            self.input_file.set(file)

            if not self.output_file.get():

                if file.lower().endswith(".xlsx"):

                    self.output_file.set(

                        file.replace(

                            ".xlsx",

                            "_Updated.xlsx"

                        )

                    )

    # --------------------------------------------------

    def select_output(self):

        file = filedialog.asksaveasfilename(

            title="Save Updated Workbook",

            defaultextension=".xlsx",

            filetypes=[

                ("Excel Workbook", "*.xlsx")

            ]

        )

        if file:

            self.output_file.set(file)

    # --------------------------------------------------

    def start(self):

        if self.input_file.get() == "":

            messagebox.showerror(

                "Error",

                "Please select the input Excel."

            )

            return

        if self.output_file.get() == "":

            messagebox.showerror(

                "Error",

                "Please select where to save the output."

            )

            return

        threading.Thread(

            target=self.run,

            daemon=True

        ).start()

    # --------------------------------------------------

    def run(self):

        try:

            self.status.set("Processing...")

            output = main(

                self.input_file.get(),

                self.output_file.get()

            )

            self.status.set("Completed")

            messagebox.showinfo(

                "Success",

                f"Workbook saved successfully.\n\n{output}"

            )

        except Exception as e:

            self.status.set("Failed")

            messagebox.showerror(

                "Error",

                str(e)

            )


RecruitersToolkitUI()

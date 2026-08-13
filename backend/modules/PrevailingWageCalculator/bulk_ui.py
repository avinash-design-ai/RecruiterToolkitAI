"""
Bulk Prevailing Wage Calculator UI
"""

import os
import threading
import tkinter as tk

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

from .src.main import run_bulk_calculation


class BulkWageUI:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Bulk Prevailing Wage Calculator"
        )

        self.root.geometry(
            "720x560"
        )

        self.root.resizable(
            False,
            False
        )

        self.input_file = None
        self.output_file = None

        self.build_ui()

    # --------------------------------------------------
    # BUILD UI
    # --------------------------------------------------

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="Bulk Prevailing Wage Calculator",
            font=("Segoe UI", 17, "bold")
        )

        title.pack(pady=15)

        subtitle = tk.Label(
            self.root,
            text="Process multiple cities from an Excel workbook",
            font=("Segoe UI", 10)
        )

        subtitle.pack(pady=(0, 15))

        # --------------------------------------------------
        # INPUT FILE
        # --------------------------------------------------

        input_frame = tk.LabelFrame(
            self.root,
            text="Input Excel File",
            padx=15,
            pady=15
        )

        input_frame.pack(
            fill="x",
            padx=25,
            pady=10
        )

        self.input_label = tk.Label(
            input_frame,
            text="No Excel file selected",
            anchor="w",
            width=65
        )

        self.input_label.grid(
            row=0,
            column=0,
            padx=5,
            sticky="w"
        )

        self.input_button = tk.Button(
            input_frame,
            text="Select Excel File",
            width=18,
            command=self.select_input
        )

        self.input_button.grid(
            row=0,
            column=1,
            padx=10
        )

        # --------------------------------------------------
        # OUTPUT FILE
        # --------------------------------------------------

        output_frame = tk.LabelFrame(
            self.root,
            text="Output Excel File",
            padx=15,
            pady=15
        )

        output_frame.pack(
            fill="x",
            padx=25,
            pady=10
        )

        self.output_label = tk.Label(
            output_frame,
            text="Output file will be created here",
            anchor="w",
            width=65
        )

        self.output_label.grid(
            row=0,
            column=0,
            padx=5,
            sticky="w"
        )

        self.output_button = tk.Button(
            output_frame,
            text="Select Output",
            width=18,
            command=self.select_output
        )

        self.output_button.grid(
            row=0,
            column=1,
            padx=10
        )

        # --------------------------------------------------
        # PROGRESS
        # --------------------------------------------------

        progress_frame = tk.LabelFrame(
            self.root,
            text="Progress",
            padx=15,
            pady=15
        )

        progress_frame.pack(
            fill="x",
            padx=25,
            pady=10
        )

        self.progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            length=620,
            mode="determinate"
        )

        self.progress.pack(
            pady=5
        )

        self.status_label = tk.Label(
            progress_frame,
            text="Ready",
            anchor="w"
        )

        self.status_label.pack(
            fill="x",
            pady=5
        )

        # --------------------------------------------------
        # BUTTONS
        # --------------------------------------------------

        button_frame = tk.Frame(
            self.root
        )

        button_frame.pack(
            pady=15
        )

        self.start_button = tk.Button(
            button_frame,
            text="Start Calculation",
            width=20,
            command=self.start_calculation
        )

        self.start_button.grid(
            row=0,
            column=0,
            padx=5
        )

        self.open_button = tk.Button(
            button_frame,
            text="Open Output Folder",
            width=20,
            command=self.open_output_folder,
            state="disabled"
        )

        self.open_button.grid(
            row=0,
            column=1,
            padx=5
        )

        self.exit_button = tk.Button(
            button_frame,
            text="Exit",
            width=15,
            command=self.root.destroy
        )

        self.exit_button.grid(
            row=0,
            column=2,
            padx=5
        )

    # --------------------------------------------------
    # SELECT INPUT
    # --------------------------------------------------

    def select_input(self):

        file_path = filedialog.askopenfilename(
            title="Select Input Excel File",
            filetypes=[
                (
                    "Excel Files",
                    "*.xlsx"
                ),
                (
                    "Excel Files",
                    "*.xlsm"
                )
            ]
        )

        if not file_path:
            return

        self.input_file = file_path

        self.input_label.config(
            text=file_path
        )

        # Automatically suggest output filename

        directory = os.path.dirname(
            file_path
        )

        filename = os.path.basename(
            file_path
        )

        name, extension = os.path.splitext(
            filename
        )

        self.output_file = os.path.join(
            directory,
            f"{name} - Updated{extension}"
        )

        self.output_label.config(
            text=self.output_file
        )

    # --------------------------------------------------
    # SELECT OUTPUT
    # --------------------------------------------------

    def select_output(self):

        file_path = filedialog.asksaveasfilename(
            title="Save Output Excel File",
            defaultextension=".xlsx",
            filetypes=[
                (
                    "Excel Files",
                    "*.xlsx"
                )
            ]
        )

        if not file_path:
            return

        self.output_file = file_path

        self.output_label.config(
            text=file_path
        )

    # --------------------------------------------------
    # START CALCULATION
    # --------------------------------------------------

    def start_calculation(self):

        if not self.input_file:

            messagebox.showwarning(
                "Input Required",
                "Please select an Excel input file."
            )

            return

        if not self.output_file:

            messagebox.showwarning(
                "Output Required",
                "Please select an output file."
            )

            return

        if os.path.abspath(
            self.input_file
        ) == os.path.abspath(
            self.output_file
        ):

            messagebox.showerror(
                "Invalid Output",
                "Input and output files must be different."
            )

            return

        confirm = messagebox.askyesno(
            "Start Calculation",
            "Start the bulk prevailing wage calculation?"
        )

        if not confirm:
            return

        self.start_button.config(
            state="disabled"
        )

        self.input_button.config(
            state="disabled"
        )

        self.output_button.config(
            state="disabled"
        )

        self.open_button.config(
            state="disabled"
        )

        self.progress["value"] = 0

        self.status_label.config(
            text="Starting calculation..."
        )

        thread = threading.Thread(
            target=self.run_worker,
            daemon=True
        )

        thread.start()

    # --------------------------------------------------
    # WORKER
    # --------------------------------------------------

    def run_worker(self):

        try:

            output_directory = os.path.dirname(
                self.output_file
            )

            if output_directory:

                os.makedirs(
                    output_directory,
                    exist_ok=True
                )

            log_file = os.path.join(
                output_directory,
                "bulk_wage_run.log"
            )

            result = run_bulk_calculation(
                excel_file=self.input_file,
                output_file=self.output_file,
                log_file=log_file,
                progress_callback=self.progress_callback
            )

            self.root.after(
                0,
                lambda: self.calculation_complete(
                    result
                )
            )

        except Exception as ex:

            self.root.after(
                0,
                lambda: self.calculation_failed(
                    str(ex)
                )
            )

    # --------------------------------------------------
    # PROGRESS CALLBACK
    # --------------------------------------------------

    def progress_callback(
        self,
        completed,
        total,
        city,
        status
    ):

        self.root.after(
            0,
            lambda: self.update_progress(
                completed,
                total,
                city,
                status
            )
        )

    # --------------------------------------------------
    # UPDATE PROGRESS
    # --------------------------------------------------

    def update_progress(
        self,
        completed,
        total,
        city,
        status
    ):

        if total > 0:

            percentage = (
                completed / total
            ) * 100

        else:

            percentage = 0

        self.progress["value"] = percentage

        if city:

            self.status_label.config(
                text=f"{city} - {status}"
            )

        else:

            self.status_label.config(
                text=status
            )

    # --------------------------------------------------
    # COMPLETED
    # --------------------------------------------------

    def calculation_complete(
        self,
        result
    ):

        self.progress["value"] = 100

        self.status_label.config(
            text="Calculation completed successfully."
        )

        self.start_button.config(
            state="normal"
        )

        self.input_button.config(
            state="normal"
        )

        self.output_button.config(
            state="normal"
        )

        self.open_button.config(
            state="normal"
        )

        messagebox.showinfo(
            "Completed",
            "Prevailing wage calculation completed successfully.\n\n"
            f"Output file:\n{result}"
        )

    # --------------------------------------------------
    # FAILED
    # --------------------------------------------------

    def calculation_failed(
        self,
        error
    ):

        self.status_label.config(
            text="Calculation failed."
        )

        self.start_button.config(
            state="normal"
        )

        self.input_button.config(
            state="normal"
        )

        self.output_button.config(
            state="normal"
        )

        messagebox.showerror(
            "Calculation Error",
            error
        )

    # --------------------------------------------------
    # OPEN OUTPUT FOLDER
    # --------------------------------------------------

    def open_output_folder(self):

        if not self.output_file:
            return

        folder = os.path.dirname(
            os.path.abspath(
                self.output_file
            )
        )

        if os.path.exists(folder):

            os.startfile(folder)

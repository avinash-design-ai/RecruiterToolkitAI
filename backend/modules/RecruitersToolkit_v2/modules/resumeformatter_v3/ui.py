import tkinter as tk
from tkinter import filedialog, messagebox
import os

from resume_parser import ResumeParser
from formatter import generate_resume


class ResumeFormatterUI:

    def __init__(self, root):

        self.root = root
        self.root.title("Recruiter's Toolkit - Resume Formatter")
        self.root.geometry("600x260")
        self.root.resizable(False, False)

        self.resume_path = tk.StringVar()
        self.output_folder = tk.StringVar(value=os.getcwd())

        tk.Label(root, text="Resume (.docx)").pack(anchor="w", padx=10, pady=(10,0))

        f1 = tk.Frame(root)
        f1.pack(fill="x", padx=10)

        tk.Entry(f1, textvariable=self.resume_path).pack(side="left", fill="x", expand=True)
        tk.Button(f1, text="Browse", command=self.browse_resume, width=12).pack(side="left", padx=5)

        tk.Label(root, text="Output Folder").pack(anchor="w", padx=10, pady=(10,0))

        f2 = tk.Frame(root)
        f2.pack(fill="x", padx=10)

        tk.Entry(f2, textvariable=self.output_folder).pack(side="left", fill="x", expand=True)
        tk.Button(f2, text="Browse", command=self.browse_output, width=12).pack(side="left", padx=5)

        f3 = tk.Frame(root)
        f3.pack(pady=20)

        tk.Button(f3, text="Generate Resume", width=18, command=self.generate).pack(side="left", padx=5)
        tk.Button(f3, text="Open Output", width=18, command=self.open_output).pack(side="left", padx=5)
        tk.Button(f3, text="Exit", width=10, command=root.destroy).pack(side="left", padx=5)

    def browse_resume(self):
        file = filedialog.askopenfilename(
            title="Select Resume",
            filetypes=[("Word Document","*.docx")]
        )
        if file:
            self.resume_path.set(file)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)

    def generate(self):
        if not self.resume_path.get():
            messagebox.showerror("Error","Please select a resume.")
            return

        try:
            parser = ResumeParser()
            resume = parser.parse(self.resume_path.get())

            name = resume.name.strip() if getattr(resume, "name", "") else "Formatted_Resume"
            safe = "".join(c for c in name if c.isalnum() or c in (" ","_","-")).strip()
            if not safe:
                safe = "Formatted_Resume"

            output_file = os.path.join(self.output_folder.get(), safe + ".docx")

            generate_resume(resume, output_file)

            messagebox.showinfo("Success", f"Resume Generated Successfully.\n\n{output_file}")

        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def open_output(self):
        folder = self.output_folder.get()
        if os.path.isdir(folder):
            os.startfile(folder)


if __name__ == "__main__":
    root = tk.Tk()
    ResumeFormatterUI(root)
    root.mainloop()

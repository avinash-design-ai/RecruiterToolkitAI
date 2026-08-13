import tkinter as tk

from .bulk_ui import BulkWageUI


def main():
    root = tk.Tk()

    BulkWageUI(root)

    root.mainloop()


if __name__ == "__main__":
    main()

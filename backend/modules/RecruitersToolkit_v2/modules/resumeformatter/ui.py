from parser import read_resume
from ai_parser import parse_resume_ai
from formatter import generate_resume

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QMessageBox,
)

import sys
import os


class ResumeFormatterWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Recruiter's Toolkit - Resume Formatter (AI)")
        self.resize(700, 300)

        layout = QVBoxLayout()

        # Resume File

        layout.addWidget(QLabel("Input Resume"))

        file_layout = QHBoxLayout()

        self.resume_path = QLineEdit()
        self.resume_path.setReadOnly(True)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_resume)

        file_layout.addWidget(self.resume_path)
        file_layout.addWidget(browse_btn)

        layout.addLayout(file_layout)

        # Template

        layout.addWidget(QLabel("Template"))

        self.template = QComboBox()

        self.template.addItems([
            "SmartWorks",
            "iTech"
        ])

        layout.addWidget(self.template)

        # Generate Button

        self.generate_btn = QPushButton("Generate Resume")

        self.generate_btn.clicked.connect(self.generate_resume)

        layout.addWidget(self.generate_btn)

        self.setLayout(layout)

    def browse_resume(self):

        filename, _ = QFileDialog.getOpenFileName(

            self,

            "Select Resume",

            "",

            "Resume Files (*.docx *.pdf)"

        )

        if filename:

            self.resume_path.setText(filename)

    def generate_resume(self):

        if not self.resume_path.text():

            QMessageBox.warning(

                self,

                "Resume",

                "Please select a resume."

            )

            return

        try:

            resume_text = read_resume(
                self.resume_path.text()
            )

            resume = parse_resume_ai(
                resume_text
            )

            os.makedirs(
                "output",
                exist_ok=True
            )

            output_file = os.path.join(

                "output",

                "Generated Resume.docx"

            )

            generate_resume(

                resume,

                output_file

            )

            QMessageBox.information(

                self,

                "Completed",

                f"Resume generated successfully.\n\n{output_file}"

            )

        except Exception as e:

            QMessageBox.critical(

                self,

                "Error",

                str(e)

            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = ResumeFormatterWindow()

    window.show()

    sys.exit(app.exec())

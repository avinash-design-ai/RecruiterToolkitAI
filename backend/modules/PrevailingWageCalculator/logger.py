from datetime import datetime


class Logger:

    def __init__(self):

        self.file = None

    def start(self, logfile):

        self.file = open(
            logfile,
            "w",
            encoding="utf-8"
        )

        self.log("=" * 60)
        self.log("Prevailing Wage Updater")
        self.log("=" * 60)

    def log(self, message):

        timestamp = datetime.now().strftime("%H:%M:%S")

        line = f"[{timestamp}] {message}"

        print(line)

        if self.file:

            self.file.write(line + "\n")
            self.file.flush()

    def close(self):

        if self.file:

            self.log("=" * 60)
            self.log("Completed")
            self.log("=" * 60)

            self.file.close()

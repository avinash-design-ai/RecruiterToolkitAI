import random
import string
from datetime import datetime


class Helpers:

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def random_string(length=8):
        return ''.join(
            random.choice(string.ascii_letters)
            for _ in range(length)
        )

    @staticmethod
    def random_number(length=6):
        return ''.join(
            random.choice(string.digits)
            for _ in range(length)
        )

    @staticmethod
    def random_email(domain="example.com"):
        return (
            Helpers.random_string(8).lower()
            + "@"
            + domain
        )

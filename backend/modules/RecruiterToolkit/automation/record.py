from dataclasses import dataclass

@dataclass
class Record:
    name: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""

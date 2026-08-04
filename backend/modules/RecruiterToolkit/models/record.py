from dataclasses import dataclass, asdict


@dataclass
class Record:

    name: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    notes: str = ""

    def to_dict(self):
        return asdict(self)

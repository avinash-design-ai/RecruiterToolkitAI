from dataclasses import dataclass, field


@dataclass
class Project:

    title: str = ""

    role: str = ""

    duration: str = ""

    responsibilities: list = field(default_factory=list)


@dataclass
class Job:

    client: str = ""

    employer: str = ""

    location: str = ""

    duration: str = ""          # Employment Duration

    role: str = ""              # Latest Role

    projects: list = field(default_factory=list)

    environment: list = field(default_factory=list)


@dataclass
class Resume:

    name: str = ""

    phone: str = ""

    email: str = ""

    linkedin: str = ""

    summary: list = field(default_factory=list)

    technical_skills: dict = field(default_factory=dict)

    experience: list = field(default_factory=list)

    education: list = field(default_factory=list)

    certifications: list = field(default_factory=list)

    raw_document = None


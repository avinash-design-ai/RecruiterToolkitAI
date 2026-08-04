from dataclasses import dataclass, field


@dataclass
class Project:
    client: str = ""
    project_name: str = ""
    role: str = ""
    duration: str = ""
    location: str = ""
    environment: str = ""
    description: str = ""
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class Resume:
    # Contact
    name: str = ""
    phone: str = ""
    email: str = ""
    linkedin: str = ""

    # Sections
    summary: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    technical_skills: dict = field(default_factory=dict)
    certifications: list[str] = field(default_factory=list)

    # Experience
    projects: list[Project] = field(default_factory=list)

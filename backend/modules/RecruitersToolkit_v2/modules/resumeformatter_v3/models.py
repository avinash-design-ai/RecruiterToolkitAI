from dataclasses import dataclass, field


@dataclass
class Project:
    client: str = ""
    project_name: str = ""
    role: str = ""
    duration: str = ""
    location: str = ""
    description: str = ""
    environment: str = ""
    responsibilities: list[str] = field(default_factory=list)


@dataclass
class Resume:

    # Contact
    name: str = ""
    phone: str = ""
    email: str = ""
    linkedin: str = ""

    # Summary
    summary: list[str] = field(default_factory=list)

    # Education
    education: list[str] = field(default_factory=list)

    # Skills
    technical_skills: dict = field(default_factory=dict)

    # Certifications
    certifications: list[str] = field(default_factory=list)

    # Projects
    projects: list[Project] = field(default_factory=list)

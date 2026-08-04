"""
Recruiter's Toolkit
Knowledge Base

All parser keywords live here.

Whenever you encounter a new resume format,
only update this file.
"""

import re


# ======================================================
# SECTION HEADINGS
# ======================================================

SECTION_HEADERS = {

    "summary": [

        "summary",
        "professional summary",
        "career summary",
        "executive summary",
        "profile",
        "professional profile",
        "career profile",
        "objective",
        "career objective",
        "about me"

    ],

    "skills": [

        "technical skills",
        "skills",
        "technical expertise",
        "technical proficiency",
        "technical competencies",
        "core competencies",
        "core skills",
        "technology",
        "technologies",
        "tools",
        "skill set"

    ],

    "experience": [

        "professional experience",
        "work experience",
        "employment history",
        "experience",
        "project experience",
        "professional projects",
        "projects"

    ],

    "education": [

        "education",
        "academic",
        "academic details",
        "academic qualification",
        "qualification",
        "educational qualification"

    ],

    "certifications": [

        "certifications",
        "certification",
        "professional certifications",
        "licenses",
        "license"

    ]

}


# ======================================================
# EXPERIENCE LABELS
# ======================================================

CLIENT_LABELS = [

    "client",
    "customer",
    "company",
    "organization",
    "employer"

]

ROLE_LABELS = [

    "role",
    "designation",
    "position",
    "title"

]

PROJECT_LABELS = [

    "project",
    "project name",
    "application"

]

DURATION_LABELS = [

    "duration",
    "period",
    "timeline"

]

LOCATION_LABELS = [

    "location",
    "onsite",
    "offshore"

]

RESPONSIBILITY_LABELS = [

    "responsibilities",
    "responsibility",
    "roles and responsibilities",
    "key responsibilities"

]

ENVIRONMENT_LABELS = [

    "environment",
    "technology",
    "technologies",
    "technical environment"

]


# ======================================================
# BULLET SYMBOLS
# ======================================================

BULLETS = [

    "•",
    "-",
    "▪",
    "◦",
    "●",
    "*"

]


# ======================================================
# COMMON DATE PATTERNS
# ======================================================

DATE_PATTERNS = [

    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\s*[-–]\s*(?:Present|Current|Till Date|Till Now|Now|\w+\s+\d{4})",

    r"\d{2}/\d{4}\s*[-–]\s*(?:Present|\d{2}/\d{4})",

    r"\d{4}\s*[-–]\s*(?:Present|\d{4})"

]


# ======================================================
# HELPER FUNCTIONS
# ======================================================

def normalize(text):

    text = text.lower()

    text = text.replace(":", "")
    text = text.replace("|", "")
    text = text.replace("-", " ")

    text = " ".join(text.split())

    return text.strip()


def is_heading(line):

    value = normalize(line)

    for section, headings in SECTION_HEADERS.items():

        if value in headings:

            return section

    return None


def contains_date(text):

    for pattern in DATE_PATTERNS:

        if re.search(pattern, text, re.IGNORECASE):

            return True

    return False


def starts_with_any(text, labels):

    value = normalize(text)

    for label in labels:

        if value.startswith(label):

            return True

    return False

US_STATE_CODES = [

"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",

"HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",

"MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",

"NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",

"SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"

]

ROLE_KEYWORDS = [

    "Developer",
    "Engineer",
    "Architect",
    "Consultant",
    "Administrator",
    "Analyst",
    "Lead",
    "Manager",
    "Director",
    "Principal",
    "Specialist",
    "Coordinator",
    "Programmer",
    "Designer",

    "Business Analyst",
    "Technical Business Analyst",

    "Software Engineer",
    "Senior Software Engineer",

    "Java Developer",
    "Python Developer",
    ".NET Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Developer",

    "ETL Developer",
    "Data Engineer",
    "Data Analyst",

    "Cloud Engineer",
    "AWS Engineer",
    "Azure Engineer",
    "GCP Engineer",

    "DevOps Engineer",

    "QA Engineer",
    "Automation Tester",
    "Manual Tester",
    "SDET",

    "Scrum Master",
    "Product Owner",
    "Project Manager",
    "Program Manager",
    "Technical Lead",
    "Team Lead",

    "ServiceNow Developer",
    "Snowflake Developer"

]

US_STATE_NAMES = [

    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming"

]

TECHNOLOGY_KEYWORDS = [

    "Java",
    "Spring",
    "Spring Boot",
    "Hibernate",

    "Python",
    "Django",
    "Flask",

    "C#",
    ".NET",
    "ASP.NET",

    "Angular",
    "React",
    "Vue",
    "Node.js",

    "Oracle",
    "SQL Server",
    "MySQL",
    "PostgreSQL",

    "Snowflake",
    "Databricks",
    "Redshift",

    "Informatica",
    "DataStage",
    "Talend",
    "SSIS",

    "AWS",
    "Azure",
    "GCP",

    "Docker",
    "Kubernetes",
    "Jenkins",
    "Git",
    "Kafka",
    "Spark",
    "Hadoop",

    "Power BI",
    "Tableau",

    "ServiceNow"

]

WORK_MODES = [

    "Remote",
    "Hybrid",
    "Onsite",
    "On-Site",
    "Work From Home",
    "WFH"

]

COMPANY_SUFFIXES = [

    "Inc",
    "LLC",
    "Ltd",
    "Limited",
    "Corporation",
    "Corp",

    "Technologies",
    "Technology",

    "Solutions",
    "Systems",
    "Consulting",
    "Services"

]

COMMON_COMPANIES = [

    "Accenture",
    "Capgemini",
    "Cognizant",
    "Deloitte",
    "EY",
    "HCL",
    "IBM",
    "Infosys",
    "KPMG",
    "LTIMindtree",
    "NTT DATA",
    "PwC",
    "TCS",
    "Tech Mahindra",
    "UST",
    "Wipro",

    "Amazon",
    "Apple",
    "Google",
    "Meta",
    "Microsoft",
    "Oracle",
    "Salesforce",

    "Cigna",
    "UnitedHealth",
    "Humana",
    "Anthem",

    "JPMorgan Chase",
    "Bank of America",
    "Wells Fargo",
    "Capital One"

]

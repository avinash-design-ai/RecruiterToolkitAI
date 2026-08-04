class ResumeValidator:

    def __init__(self, resume):

        self.resume = resume
        self.errors = []
        self.warnings = []

    def validate(self):

        self.validate_contact()

        self.validate_summary()

        self.validate_skills()

        self.validate_experience()

        self.validate_education()

        self.validate_certifications()

        return self

    # -------------------------------------

    def validate_contact(self):

        if not self.resume.name:
            self.errors.append("Candidate Name Missing")

        if not self.resume.phone:
            self.warnings.append("Phone Missing")

        if not self.resume.email:
            self.warnings.append("Email Missing")

        if not self.resume.linkedin:
            self.warnings.append("LinkedIn Missing")

    # -------------------------------------

    def validate_summary(self):

        if not self.resume.summary:
            self.warnings.append("Professional Summary Missing")

    # -------------------------------------

    def validate_skills(self):

        if not self.resume.technical_skills:
            self.warnings.append("Technical Skills Missing")

    # -------------------------------------

    def validate_experience(self):

        if not self.resume.experience:

            self.errors.append("Professional Experience Missing")

            return

        for i, job in enumerate(self.resume.experience, start=1):

            if not job.get("company"):
                self.warnings.append(
                    f"Job {i}: Client Missing"
                )

            if not job.get("title"):
                self.warnings.append(
                    f"Job {i}: Role Missing"
                )

            if not job.get("duration"):
                self.warnings.append(
                    f"Job {i}: Duration Missing"
                )

            if not job.get("project"):
                self.warnings.append(
                    f"Job {i}: Project Description Missing"
                )

            if not job.get("environment"):
                self.warnings.append(
                    f"Job {i}: Environment Missing"
                )

    # -------------------------------------

    def validate_education(self):

        if not self.resume.education:
            self.warnings.append("Education Missing")

    # -------------------------------------

    def validate_certifications(self):

        if not self.resume.certifications:
            self.warnings.append("Certifications Missing")

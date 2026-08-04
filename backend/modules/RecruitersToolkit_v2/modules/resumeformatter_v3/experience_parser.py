import re

from knowledge_base import contains_date


class ExperienceParser:

    def __init__(self):
        pass

    # --------------------------------------------------
    # Split Experience into Job Blocks
    # --------------------------------------------------

    def split_jobs(self, experience_text):

        if not experience_text:
            return []

        lines = [

            line.strip()

            for line in experience_text.splitlines()

            if line.strip()

        ]

        jobs = []

        current_job = []

        found_date = False

        for line in lines:

            # If we already have a date
            # and another date appears,
            # that means next job begins.

            if contains_date(line):

                if found_date and current_job:

                    jobs.append("\n".join(current_job))

                    current_job = []

                found_date = True

            current_job.append(line)

        if current_job:

            jobs.append("\n".join(current_job))

        return jobs

    # --------------------------------------------------
    # Debug
    # --------------------------------------------------

    def print_jobs(self, jobs):

        print("\n==============================")
        print("JOBS FOUND:", len(jobs))
        print("==============================\n")

        for i, job in enumerate(jobs, 1):

            print(f"JOB {i}")
            print("-" * 40)

            print(job[:800])

            print("\n")

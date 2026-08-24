import base64
import io
import os
import time
import zipfile

import requests
from nacl import encoding
from nacl import public


GITHUB_API = "https://api.github.com"

GITHUB_OWNER = os.getenv(
    "GITHUB_OWNER",
    "avinash-design-ai",
)

GITHUB_REPO = os.getenv(
    "GITHUB_REPO",
    "RecruiterToolkitAI",
)

GITHUB_WORKFLOW = os.getenv(
    "GITHUB_WORKFLOW",
    "linkedin-v2-storage-search.yml",
)

GITHUB_BRANCH = os.getenv(
    "GITHUB_BRANCH",
    "main",
)

GITHUB_SECRET_NAME = os.getenv(
    "GITHUB_SECRET_NAME",
    "LINKEDIN_STORAGE_STATE",
)


class GitHubActionsService:

    # ---------------------------------------------------------
    # GitHub headers
    # ---------------------------------------------------------

    @staticmethod
    def _headers():

        token = os.getenv("GITHUB_TOKEN")

        if not token:
            raise RuntimeError(
                "GITHUB_TOKEN environment variable is not configured."
            )

        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ---------------------------------------------------------
    # Repository URL
    # ---------------------------------------------------------

    @classmethod
    def _repo_url(cls, path=""):

        return (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_OWNER}/"
            f"{GITHUB_REPO}"
            f"{path}"
        )

    # ---------------------------------------------------------
    # Get GitHub repository public key
    # ---------------------------------------------------------

    @classmethod
    def get_public_key(cls):

        url = cls._repo_url(
            "/actions/secrets/public-key"
        )

        response = requests.get(
            url,
            headers=cls._headers(),
            timeout=30,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to retrieve GitHub repository "
                f"public key: {response.status_code} "
                f"{response.text}"
            )

        return response.json()

    # ---------------------------------------------------------
    # Encrypt secret using GitHub public key
    # ---------------------------------------------------------

    @staticmethod
    def encrypt_secret(
        value,
        public_key,
    ):

        key = public.PublicKey(
            public_key.encode("utf-8"),
            encoding.Base64Encoder(),
        )

        sealed_box = public.SealedBox(key)

        encrypted = sealed_box.encrypt(
            value.encode("utf-8")
        )

        return base64.b64encode(
            encrypted
        ).decode("utf-8")

    # ---------------------------------------------------------
    # Update GitHub repository secret
    # ---------------------------------------------------------

    @classmethod
    def update_storage_state(
        cls,
        storage_state,
    ):

        print("=" * 70)
        print("UPDATING GITHUB LINKEDIN STORAGE STATE")
        print("=" * 70)

        if not storage_state:

            raise RuntimeError(
                "LinkedIn storage state is empty."
            )

        key_data = cls.get_public_key()

        public_key = key_data.get(
            "key"
        )

        key_id = key_data.get(
            "key_id"
        )

        if not public_key or not key_id:

            raise RuntimeError(
                "GitHub repository public key response "
                "is missing key or key_id."
            )

        encrypted_value = cls.encrypt_secret(
            storage_state,
            public_key,
        )

        url = cls._repo_url(
            "/actions/secrets/"
            f"{GITHUB_SECRET_NAME}"
        )

        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_id,
        }

        response = requests.put(
            url,
            headers=cls._headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code not in (
            201,
            204,
        ):

            raise RuntimeError(
                "Failed to update GitHub secret: "
                f"{response.status_code} "
                f"{response.text}"
            )

        print(
            "GitHub secret updated successfully."
        )

        return True

    # ---------------------------------------------------------
    # Dispatch workflow and identify created run
    # ---------------------------------------------------------

    @classmethod
    def dispatch_search(
        cls,
        company,
        location,
        max_profiles,
    ):

        url = (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_OWNER}/"
            f"{GITHUB_REPO}/"
            f"actions/workflows/"
            f"{GITHUB_WORKFLOW}/dispatches"
        )

        payload = {
            "ref": GITHUB_BRANCH,
            "inputs": {
                "company": company,
                "location": location,
                "max_profiles": str(
                    max_profiles
                ),
            },
        }

        dispatch_started = time.time()

        response = requests.post(
            url,
            headers=cls._headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code != 204:

            raise RuntimeError(
                "GitHub workflow dispatch failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        print(
            "GitHub LinkedIn workflow dispatched."
        )

        # GitHub's dispatch API returns 204 and does not
        # directly provide the workflow run ID.
        #
        # Give GitHub a moment to register the run, then
        # identify the newest run created after this dispatch.

        run_id = None

        for attempt in range(10):

            time.sleep(2)

            runs = cls.get_workflow_runs(
                limit=10
            )

            for run in runs:

                created_at = run.get(
                    "created_at"
                )

                if not created_at:
                    continue

                try:

                    from datetime import datetime

                    created_time = (
                        datetime.fromisoformat(
                            created_at.replace(
                                "Z",
                                "+00:00"
                            )
                        ).timestamp()
                    )

                except Exception:

                    continue

                if created_time >= (
                    dispatch_started - 5
                ):

                    run_id = run.get(
                        "id"
                    )

                    if run_id:

                        print(
                            "GitHub workflow run found:",
                            run_id
                        )

                        break

            if run_id:
                break

            print(
                f"Waiting for GitHub workflow run "
                f"(attempt {attempt + 1}/10)..."
            )

        if not run_id:

            raise RuntimeError(
                "GitHub workflow was dispatched successfully, "
                "but the workflow run ID could not be determined."
            )

        return {
            "success": True,
            "workflow": GITHUB_WORKFLOW,
            "branch": GITHUB_BRANCH,
            "run_id": run_id,
        }

    # ---------------------------------------------------------
    # Get latest workflow runs
    # ---------------------------------------------------------

    @classmethod
    def get_workflow_runs(
        cls,
        limit=10,
    ):

        url = (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_OWNER}/"
            f"{GITHUB_REPO}/"
            f"actions/workflows/"
            f"{GITHUB_WORKFLOW}/runs"
        )

        response = requests.get(
            url,
            headers=cls._headers(),
            params={
                "branch": GITHUB_BRANCH,
                "per_page": limit,
            },
            timeout=30,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to retrieve GitHub workflow runs: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json().get(
            "workflow_runs",
            []
        )

    # ---------------------------------------------------------
    # Find latest run
    # ---------------------------------------------------------

    @classmethod
    def get_latest_run(cls):

        runs = cls.get_workflow_runs(
            limit=10
        )

        if not runs:
            return None

        return runs[0]

    # ---------------------------------------------------------
    # Get specific workflow run
    # ---------------------------------------------------------

    @classmethod
    def get_run(
        cls,
        run_id,
    ):

        url = cls._repo_url(
            f"/actions/runs/{run_id}"
        )

        response = requests.get(
            url,
            headers=cls._headers(),
            timeout=30,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to retrieve GitHub workflow run: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json()

    # ---------------------------------------------------------
    # Get artifacts for run
    # ---------------------------------------------------------

    @classmethod
    def get_run_artifacts(
        cls,
        run_id,
    ):

        url = cls._repo_url(
            f"/actions/runs/{run_id}/artifacts"
        )

        response = requests.get(
            url,
            headers=cls._headers(),
            timeout=30,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to retrieve GitHub artifacts: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json().get(
            "artifacts",
            []
        )

    # ---------------------------------------------------------
    # Download CSV artifact
    # ---------------------------------------------------------

    @classmethod
    def download_csv_artifact(
        cls,
        run_id,
        destination_path,
    ):

        artifacts = cls.get_run_artifacts(
            run_id
        )

        target = None

        for artifact in artifacts:

            if (
                artifact.get("name")
                == "linkedin-v2-results"
            ):

                target = artifact
                break

        if not target:

            raise RuntimeError(
                "LinkedIn CSV artifact was not found."
            )

        if target.get("expired"):

            raise RuntimeError(
                "LinkedIn CSV artifact has expired."
            )

        artifact_id = target.get(
            "id"
        )

        url = cls._repo_url(
            f"/actions/artifacts/"
            f"{artifact_id}/zip"
        )

        headers = cls._headers()

        headers[
            "Accept"
        ] = "application/vnd.github+json"

        response = requests.get(
            url,
            headers=headers,
            timeout=120,
        )

        if response.status_code != 200:

            raise RuntimeError(
                "Unable to download GitHub artifact: "
                f"{response.status_code} "
                f"{response.text}"
            )

        os.makedirs(
            os.path.dirname(destination_path),
            exist_ok=True,
        )

        with zipfile.ZipFile(
            io.BytesIO(response.content)
        ) as archive:

            csv_files = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".csv")
            ]

            if not csv_files:

                raise RuntimeError(
                    "GitHub artifact does not contain "
                    "a CSV file."
                )

            csv_name = csv_files[0]

            with archive.open(csv_name) as source:

                with open(
                    destination_path,
                    "wb",
                ) as target_file:

                    target_file.write(
                        source.read()
                    )

        print(
            "CSV downloaded from GitHub:"
        )

        print(
            destination_path
        )

        return destination_path
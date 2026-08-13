import os
import streamlit as st

from resume_parser import parse_resume
from engine.word_generator import generate_resume

st.set_page_config(
    page_title="Resume Formatter Pro V2",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Resume Formatter Pro V2")

uploaded = st.file_uploader(
    "Upload Resume",
    type=["pdf", "docx"]
)

if uploaded:

    os.makedirs("uploads", exist_ok=True)

    filepath = os.path.join(
        "uploads",
        uploaded.name
    )

    with open(filepath, "wb") as f:
        f.write(uploaded.getbuffer())

    st.success("Resume uploaded successfully.")

    if st.button(
        "Analyze Resume",
        use_container_width=True,
        type="primary"
    ):

        with st.spinner("Analyzing Resume..."):

            st.write("1. Starting parser")

            resume = parse_resume(filepath)

            st.write("2. Parser finished")
            
            st.write("Experience Objects")

            for job in resume.experience:

                st.write(vars(job))

                for project in job.projects:

                    st.write(vars(project))
            
            st.success("Resume parsed successfully.")

        # ---------------------------------------
        # Generate SmartWorks Resume
        # ---------------------------------------

        output_file = os.path.join(
            "uploads",
            "SmartWorks_" +
            os.path.splitext(uploaded.name)[0] +
            ".docx"
        )

        template_file = os.path.join(
            "templates",
            "SmartWorks_Template.docx"
        )

        try:

          
            generate_resume(
                resume,
                template_file,
                output_file
            )

            st.success("SmartWorks Resume Generated Successfully")

        except Exception as e:

            st.exception(e)

            st.stop()

        # ---------------------------------------
        # Layout
        # ---------------------------------------

        left, right = st.columns([1, 2])

        # ---------------------------------------
        # Left Panel
        # ---------------------------------------

        with left:

            st.subheader("Resume Information")

            st.write("**Name:**", resume.name)

            st.write("**Phone:**", resume.phone)

            st.write("**Email:**", resume.email)

            st.write("**LinkedIn:**", resume.linkedin)

            st.divider()

            st.subheader("Education")

            if resume.education:

                for item in resume.education:
                    st.write("•", item)

            else:

                st.warning("Education Missing")

            st.divider()

            st.subheader("Certifications")

            if resume.certifications:

                for item in resume.certifications:
                    st.write("•", item)

            else:

                st.info("No Certifications")

        # ---------------------------------------
        # Right Panel
        # ---------------------------------------

        with right:

            st.subheader("Professional Summary")

            if resume.summary:

                for item in resume.summary:
                    st.write("•", item)

            else:

                st.warning("Summary Missing")

            st.divider()

            st.subheader("Technical Skills")

            st.json(
                resume.technical_skills
            )

            st.divider()

            st.subheader("Professional Experience")

            if not resume.experience:

                st.warning("No Experience Found")

            for i, job in enumerate(
                resume.experience,
                start=1
            ):

                with st.expander(f"Employment {i}"):

                    st.write(
                        "**Employer:**",
                        job.employer
                    )

                    st.write(
                        "**Client:**",
                        job.client
                    )

                    st.write(
                        "**Location:**",
                        job.location
                    )

                    st.write(
                        "**Role:**",
                        job.role
                    )

                    st.write(
                        "**Duration:**",
                        job.duration
                    )

                    st.write("### Projects")

                    if not job.projects:

                        st.info(
                            "No Projects Found"
                        )

                    for project in job.projects:

                        st.write(
                            "**Project:**",
                            project.title
                        )

                        st.write(
                            "Role:",
                            project.role
                        )

                        st.write(
                            "Duration:",
                            project.duration
                        )

                        st.write(
                            "Responsibilities"
                        )

                        if project.responsibilities:

                            for bullet in project.responsibilities:

                                st.write(
                                    "•",
                                    bullet
                                )

                        else:

                            st.write(
                                "No Responsibilities"
                            )

                    st.write("### Environment")

                    if job.environment:

                        for env in job.environment:

                            st.write(
                                "•",
                                env
                            )

                    else:

                        st.warning(
                            "Environment Missing"
                        )

        # ---------------------------------------
        # Download
        # ---------------------------------------

        st.divider()

        with open(output_file, "rb") as f:

            st.download_button(
                "📄 Download SmartWorks Resume",
                data=f,
                file_name=os.path.basename(output_file),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

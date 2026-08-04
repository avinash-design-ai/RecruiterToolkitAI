import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


MODEL = "gpt-5-mini"


def ask_ai(system_prompt, user_prompt):

    response = client.responses.create(

        model=MODEL,

        input=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

    )

    return response.output_text

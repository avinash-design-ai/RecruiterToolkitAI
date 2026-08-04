from llm import LLM

llm = LLM()

response = llm.ask(
    "You are a helpful assistant.",
    "Say Hello"
)

print(response)

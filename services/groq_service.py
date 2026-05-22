import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    groq_api_key=api_key
)

def ask_llm(message: str):
    try:
        response = llm.invoke(message)
        return response.content
    except Exception as e:
        print("LLM ERROR:", e)
        return f"LLM Error: {str(e)}"
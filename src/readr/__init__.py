import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

def main() -> None:
    client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="why is the sky blue?"
    )
    print(response.text)
    client.close()

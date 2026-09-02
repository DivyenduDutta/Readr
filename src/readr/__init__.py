import os
from dotenv import load_dotenv
from google import genai
from trafilatura import fetch_url, extract

load_dotenv()

URL = "https://ploum.net/2026-09-02-i_dont_have_a_smartphone.html"

def main() -> None:
    #client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
    #response = client.models.generate_content(
        #model="gemini-3.6-flash",
        #contents="why is the sky blue?"
    #)
    #print(response.text)
    #client.close()
    page = fetch_url(URL)
    text = extract(page)
    print(text)

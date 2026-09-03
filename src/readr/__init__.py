import os
from dotenv import load_dotenv
from google import genai
from trafilatura import fetch_url, extract

load_dotenv()

URL = "https://ploum.net/2026-09-02-i_dont_have_a_smartphone.html"
MODEL = "gemini-3.5-flash"

def main() -> None:
    page = fetch_url(URL)
    text = extract(page)

    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

        questions_asked = list()
        questions_asked.append(f"\n\n Summarize the following text:\n{text}")
        questions_asked.append(f"\n\n What did I just ask you?")

        responses_recieved = list()

        history = list()

        for prompt in questions_asked:
            history.append(
                {
                    "type": "user_input",
                    "content": [{"type": "text", "text": f"{prompt}"}]
                }
            )
            interaction = client.interactions.create(
                model = MODEL,
                store = False, # opt out of server side storage
                input = history
            )

            responses_recieved.append(interaction.steps[-1].content[0].text)

            # save all the steps in the interaction to the history list
            for step in interaction.steps:
                history.append(step.model_dump())
        print(f"\n\n Model finished...")
        for question, response in zip(questions_asked, responses_recieved):
            print(f"\n\n Question: {question}\n\n Response: {response}")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    finally:
        client.close()

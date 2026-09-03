from trafilatura import fetch_url, extract

from readr.model.Conversation import Conversation

URL = "https://ploum.net/2026-09-02-i_dont_have_a_smartphone.html"
MODEL = "gemini-3.5-flash"

def main() -> None:
    page = fetch_url(URL)
    text = extract(page)

    conversation = Conversation(model_name=MODEL)

    try:
        questions_asked = list()
        questions_asked.append(f"\n\n Summarize the following text:\n{text}")
        questions_asked.append(f"\n\n What did I just ask you?")

        responses_recieved = list()

        for prompt in questions_asked:
            responses_recieved.append(conversation.ask(prompt))

        print(f"\n\n Model finished...")

        for question, response in zip(questions_asked, responses_recieved):
            print(f"\n\n Question: {question}\n\n Response: {response}")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    finally:
        conversation.close()

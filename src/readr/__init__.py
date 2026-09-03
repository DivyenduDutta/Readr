from trafilatura import fetch_url, extract

from readr.model.Conversation import Conversation

URL = "https://ploum.net/2026-09-02-i_dont_have_a_smartphone.html"
MODEL = "gemini-3.6-flash"

def main() -> None:
    page = fetch_url(URL)
    text = extract(page)

    conversation = Conversation(model_name=MODEL)

    try:
        while True:
            user_input = input("\n\n Ask a question (or type 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
            response, total_tokens, current_interaction_tokens = conversation.ask(user_input)
            print(f"\n\n Question: {user_input}\n\n Response: {response}")
            print("\n")
            print(f"Current interaction input tokens: {current_interaction_tokens['input']}")
            print(f"Current interaction output tokens: {current_interaction_tokens['output']}")
            print(f"Current interaction total tokens: {current_interaction_tokens['total']}") 
            print("=" * 50)
            print(f"Overall Input tokens: {total_tokens['input']}")
            print(f"Overall Output tokens: {total_tokens['output']}")
            print(f"Overall Total tokens: {total_tokens['total']}")
            print("=" * 50)
            print("\n\n")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    finally:
        conversation.close()

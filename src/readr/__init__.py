import os

from readr.model.Conversation import Conversation
from readr.utils.file import load_config, retrieve_file_contents

URL = "https://ploum.net/2026-09-02-i_dont_have_a_smartphone.html"


def session_selector(session_path: str) -> str | None:
    """
    Show user a list of existing sessions (if available).
    The user can select an existing session to reload or start a new session.

    Args:
        session_path (Union[str, None]) : Relative path of the folder where prior sessions are stored.
                                          Relative to CWD.

    Returns:
        str : The user selected session file or None (in case of new session)
    """
    try:
        session_files = os.listdir(os.getcwd() + session_path)
        if not session_files:
            print(f"\n\nNo prior sessions found in {session_path}.")
            return

        print(f"\n\n{len(session_files)} prior sessions found : ")
        for index, file_name in enumerate(session_files):
            session_name = file_name.replace("_", " ").replace(".json", "")
            print(f"{index + 1}. {session_name}")
        user_input = input(
            "\n Please select an appropriate session (or type /new to start a new one) : "
        )
        if user_input == "/new":
            return None
        elif int(user_input) in range(1, len(session_files) + 1):
            return session_files[int(user_input) - 1]
    except ValueError as e:
        print(f"\n\nAn error occurred while trying to list prior sessions: {e}")
        return None  # consider as new session


def main() -> None:
    # page = fetch_url(URL)
    # text = extract(page)

    try:
        config = load_config("readr.yml")
        selected_session_file = session_selector(config["session"]["base_path"])
        prior_session_data = None
        if selected_session_file is not None:
            selected_session_path = (
                config["session"]["base_path"] + selected_session_file
            )
            prior_session_data = retrieve_file_contents(
                selected_session_path, is_json=True
            )

        conversation = Conversation(model_name=config["model"]["name"])

        # reload prior session data into current conversation
        if prior_session_data:
            if isinstance(prior_session_data, dict):
                conversation.reload_session_data(prior_session_data)
            else:
                raise ValueError("Expected session data to be a dictionary")
            print("\nSelected session data loaded. Please continue conversation.")
        else:
            print("\nNew session started.")

        while True:
            user_input = input("\n\n Ask a question (or type '/quit' to quit): ")
            if user_input.lower() == "/quit":
                conversation.persist()
                break
            response, total_tokens, current_interaction_tokens = conversation.ask(
                user_input
            )
            print(f"\n\n Question: {user_input}\n\n Response: {response}")
            print("\n")
            print(
                f"Current interaction input tokens: {current_interaction_tokens['input']}"
            )
            print(
                f"Current interaction output tokens: {current_interaction_tokens['output']}"
            )
            print(
                f"Current interaction total tokens: {current_interaction_tokens['total']}"
            )
            print("=" * 50)
            print(f"Overall Input tokens: {total_tokens['input']}")
            print(f"Overall Output tokens: {total_tokens['output']}")
            print(f"Overall Total tokens: {total_tokens['total']}")
            print("=" * 50)
            print("\n\n")
    except FileNotFoundError as e:
        print(f"\n\nAn error occurred while loading config file : {e}")
    except (ValueError, TypeError) as e:
        print(f"\n\nAn error occurred : {e}")
    except RuntimeError as e:
        print(f"\n\nAn error occurred : {e}")
    finally:
        conversation.close()

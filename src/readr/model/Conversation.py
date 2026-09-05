import os
import re
from typing import Any
from uuid import uuid4 as uuid

from dotenv import load_dotenv
from google import genai
from google.genai.interactions import Interaction

from readr.utils.file import load_config, retrieve_file_contents, save_file_contents


class Conversation:
    """
    A class to manage a conversation with the Google Gemini API.
    Maintains a history of user inputs and model responses, and
    provides methods to ask questions and retrieve responses.
    """

    def __init__(self, model_name: str):
        """
        Initializes a Conversation instance.

        Args:
            model_name (str): The name of the model to use for the conversation.
        """
        self.id = uuid().hex
        self.model_name = model_name
        self.title = None
        self.history = []
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
        self.config = load_config("readr.yml")

        # this is used to keep track of the previous interaction id for getting back the
        # token usage in that interaction
        self.previous_interaction_id = None

        self.total_tokens = {"input": 0, "output": 0, "total": 0}

        self.current_interaction_tokens = {"input": 0, "output": 0, "total": 0}

    def _add_to_history(self, question: str):
        """
        Adds a user input to the conversation history.

        Args:
            question (str): The user's input.
        """
        self.history.append(
            {"type": "user_input", "content": [{"type": "text", "text": f"{question}"}]}
        )

    def _remove_most_recent_from_history(self):
        """
        Removes the most recent entry from the conversation history.
        """
        if self.history:
            self.history.pop()

    def _create_interaction(self) -> Interaction | None:
        """
        Creates an interaction with the Google Gemini API.

        Returns:
            Interaction | None : The created interaction or None.
        Raises:
            TypeError : Expected response to be non-streaming type.
        """
        try:
            interaction = self.client.interactions.create(
                model=self.model_name,
                store=False,  # opt out of server side storage
                system_instruction=retrieve_file_contents(
                    self.config["model"]["system_instruction_prompt"]
                ),
                input=self.history,
                previous_interaction_id=self.previous_interaction_id
                if self.previous_interaction_id
                else None,
                stream=False,
            )
            if not isinstance(interaction, Interaction):
                raise TypeError("Expected a non-streaming response")
            return interaction
        except FileNotFoundError as e:
            print(
                f"\n\nAn error occurred while loading system instruction prompt file : {e}"
            )
            return None

    def _save_interaction_steps(self, interaction: Interaction):
        """
        Saves the steps of an interaction to the conversation history.

        Args:
            interaction (Interaction): The interaction whose steps are to be saved.
        """
        # save all the steps in the interaction to the history list
        if interaction.steps:
            for step in interaction.steps:
                self.history.append(step.model_dump())

    def _record_usage_tokens(self, interaction: Interaction):
        """Record token usage for the current interaction."""

        if not interaction.usage:
            print("No tokens available for the interaction. Will hold prior values.")
            return

        input_tokens = interaction.usage.total_input_tokens
        output_tokens = interaction.usage.total_output_tokens
        total_tokens = interaction.usage.total_tokens

        if input_tokens is None or output_tokens is None or total_tokens is None:
            print(
                "Incomplete token usage for this interaction. Will hold prior values."
            )
            return

        current_input = input_tokens - self.total_tokens["input"]
        current_output = output_tokens - self.total_tokens["output"]
        current_total = total_tokens - self.total_tokens["total"]

        self.current_interaction_tokens["input"] = current_input
        self.current_interaction_tokens["output"] = current_output
        self.current_interaction_tokens["total"] = current_total

        self.total_tokens["input"] = input_tokens
        self.total_tokens["output"] = output_tokens
        self.total_tokens["total"] = total_tokens

    def _extract_title_from_interaction(self, response: str) -> str:
        """
        Extracts a title from the interaction's response.
        This method looks for a line in the response that starts with "[Title]:" and captures the
        text that follows as the title. If no such line is found, it returns a default title.
        This behavior of expecting a title in the response is defined in the ssystem instruction prompt
        file.
        """
        match = re.search(r"\[Title\]:\s*(.+)", response)
        title = "Whats in a title"  # Default title if not found
        if match:
            title = match.group(1)
        return title

    def ask(self, question: str) -> tuple[str, dict[str, int], dict[str, int]]:
        """
        Asks a question to the model and returns the response.

        1. Adds the question to the conversation history.
        2. Creates an interaction with the model.
        3. If the interaction is successful, retrieves the model's response, extracts a title, saves
           the interaction steps to history, and records the token usage.
        4. If the interaction fails, removes the most recent question from the history and raises a
           ValueError.
        5. Responds with the model's answer, total token usage, and current interaction token usage.

        Args:
            question (str): The question to ask the model.
        Returns:
            Tuple[str, Dict[str, int], Dict[str, int]]: A tuple containing the model's response,
                                                        total token usage, and current
            interaction token usage.
        Raises:
            ValueError: If the interaction could not be created.
            TyepeError: If the interaction is streaming type.
        """
        self._add_to_history(question)
        try:
            interaction = self._create_interaction()
        except TypeError as e:
            raise TypeError(f"{e}")
        if interaction is None:
            self._remove_most_recent_from_history()
            self.previous_interaction_id = None
            raise ValueError("Error: Interaction could not be created")

        response = interaction.output_text or "Sorry, what was that again?"

        self.title = (
            self._extract_title_from_interaction(response)
            if self.title is None
            else self.title
        )
        self._save_interaction_steps(interaction)
        self._record_usage_tokens(interaction)
        self.previous_interaction_id = interaction.id
        return response, self.total_tokens, self.current_interaction_tokens

    def persist(self):
        """
        Persists the conversation history to a file.
        """
        if self.title is not None:
            conversation_context_to_persist = {
                "id": self.id,
                "title": self.title,
                "model_name": self.model_name,
                "history": self.history,
                "previous_interaction_id": self.previous_interaction_id,
                "total_tokens": self.total_tokens,
            }
            file_name = self.title.replace(" ", "_") + ".json"
            relative_path = self.config["session"]["base_path"] + file_name
            try:
                save_file_contents(relative_path, conversation_context_to_persist)
                print(f"\n{self.title} : Session saved.")
            except RuntimeError as e:
                raise RuntimeError(f"\n\nPersist the conversation: {e}")

    def reload_session_data(self, prior_session_data: dict[str, Any]):
        """
        Reload provided session data into the conversation.

        Args:
            prior_session_data (Dict[str, Any]) : Previous session data to be reloaded.
        """
        self.id = prior_session_data["id"]
        self.model_name = prior_session_data["model_name"]
        self.title = prior_session_data["title"]
        self.history = prior_session_data["history"]
        self.previous_interaction_id = prior_session_data["previous_interaction_id"]
        self.total_tokens = prior_session_data["total_tokens"]

    def close(self):
        """
        Closes the conversation and releases any resources held by the client.
        """
        self.client.close()

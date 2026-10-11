import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai.interactions import Interaction

from readr.utils.file import retrieve_file_contents
from readr.utils.logger import LoggerConfig

# Setup to handle GenAiError, CreateInteractionClientError but fallback to broad
# Exception if google-genai makes breaking changes. Could be possible since its imported
# from privately scoped _gaos
try:
    from google.genai._gaos.errors import GenAiError
except ImportError:
    GenAiError = Exception

try:
    from google.genai._gaos.errors.createinteraction import CreateInteractionClientError
except ImportError:
    CreateInteractionClientError = Exception

try:
    from google.genai._gaos.lib.compat_errors import BadRequestError
except ImportError:
    BadRequestError = Exception

try:
    from google.genai._gaos.lib.compat_errors import RateLimitError
except ImportError:
    RateLimitError = Exception

LOGGER = LoggerConfig().logger


class GeminiClient:
    """
    Thin wrapper around the Google GenAI SDK client.

    Owns the SDK client's lifecycle and translates SDK failures into `None`
    return values (logged) so callers do not need to know about SDK error types.
    """

    def __init__(self) -> None:
        """
        Initializes the wrapper and the underlying Google GenAI SDK client.

        The API key is read from the `GOOGLE_GEMINI_API_KEY` environment variable
        (a `.env` file is loaded if present).
        """
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

    def _create_interaction(self, **kwargs: Any) -> Interaction | None:
        """
        Creates a non-streaming interaction without server side storage.

        `store=False` and `stream=False` are fixed here so that no caller can
        accidentally opt in to server side storage or streaming.

        Args:
            **kwargs (Any): Keyword arguments forwarded to the SDK's
                            `interactions.create` (e.g. model, input, tools).

        Returns:
            Interaction | None: The created interaction, or None if the SDK call
                                failed or did not return a non-streaming response.
                                The failure reason is logged.
        """
        try:
            interaction = self.client.interactions.create(
                store=False,  # opt-out of server storage
                stream=False,
                **kwargs,
            )
            if not isinstance(interaction, Interaction):
                LOGGER.error("\nExpected a non-streaming response")
                return None
            return interaction
        except (GenAiError, CreateInteractionClientError) as e:
            LOGGER.error(
                f"\n\nAn error occurred while creating interaction from Google GenAI SDK : {e}"
            )
            return None
        except BadRequestError as e:
            LOGGER.error(
                f"\n\nAn error occurred due to some issue in the request to the LLM : {e}"
            )
            return None
        except RateLimitError as e:
            LOGGER.error(
                f"\n\nAn error occurred due to surpassing LLM usage limit : {e}"
            )
            return None

    def create_primary_interaction(
        self,
        model_name: str,
        history: list[dict[str, Any]],
        previous_interaction_id: str | None,
        tools: list[dict[str, Any]],
        system_instruction_file: str,
    ) -> Interaction | None:
        """
        Creates the interaction that answers the user's prompt.

        Args:
            model_name (str): The name of the model to use.
            history (list[dict[str, Any]]): The conversation history to send as input.
            previous_interaction_id (str | None): The id of the previous interaction
                                                  in this conversation, if any.
            tools (list[dict[str, Any]]): The tool declarations available to the model.
            system_instruction_file (str): Path (relative to the CWD) of the file
                                           holding the system instruction prompt.

        Returns:
            Interaction | None: The created interaction, or None if the system
                                instruction file could not be loaded or the SDK
                                call failed. The failure reason is logged.
        """
        try:
            system_instruction_content = retrieve_file_contents(system_instruction_file)
        except RuntimeError as e:
            LOGGER.error(
                f"\n\nAn error occurred while loading system instruction prompt file : {e}"
            )
            return None

        interaction = self._create_interaction(
            model=model_name,
            system_instruction=system_instruction_content,
            input=history,
            previous_interaction_id=previous_interaction_id
            if previous_interaction_id
            else None,
            tools=tools,
        )
        return interaction

    def create_interaction_to_determine_intent(
        self, model_name: str, input_prompt: str, system_instruction_file: str
    ) -> Interaction | None:
        """
        Creates a one-off interaction used to classify what the user wants done
        with a url. It is stateless: no history, previous interaction or tools.

        Args:
            model_name (str): The name of the model to use.
            input_prompt (str): The prompt to classify.
            system_instruction_file (str): Path (relative to the CWD) of the file
                                           holding the system instruction prompt.

        Returns:
            Interaction | None: The created interaction, or None if the system
                                instruction file could not be loaded or the SDK
                                call failed. The failure reason is logged.
        """
        try:
            system_instruction_content = retrieve_file_contents(system_instruction_file)
        except RuntimeError as e:
            LOGGER.error(
                f"\n\nAn error occurred while loading system instruction prompt file : {e}"
            )
            return None

        interaction = self._create_interaction(
            model=model_name,
            system_instruction=system_instruction_content,
            input=input_prompt,
        )
        return interaction

    def close(self) -> None:
        """
        Closes the GeminiClient instance and releases any resources.
        """
        self.client.close()

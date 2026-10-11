import json
import re
from json import JSONDecodeError
from typing import Any
from uuid import uuid4 as uuid

from google.genai.interactions import Interaction

from readr.constants.tool_constants import ToolNames
from readr.core.GeminiClient import GeminiClient
from readr.tools.ArticleFetcherTool import ArticleFetcherTool
from readr.utils.file import load_config, save_file_contents
from readr.utils.logger import LoggerConfig

LOGGER = LoggerConfig().logger

# Token counts keyed by "input", "output" and "total".
type TokenUsage = dict[str, int]
# Citation details keyed by citation title; each value has "url" and "cited_text".
type Citations = dict[str, dict[str, str]]


class Conversation:
    """
    A class to manage a conversation with the Google Gemini API.
    Maintains a history of user inputs and model responses, and
    provides methods to ask questions and retrieve responses.

    Attributes:
        id (str): Unique id of this conversation (used when persisting it).
        model_name (str): The name of the model used for the conversation.
        title (str | None): The conversation title, taken from the first model response.
        history (list[dict[str, Any]]): User inputs, model steps and tool results sent
                                        back to the model as the conversation input.
        tools (list[dict[str, Any]]): The tool declarations sent with the current request.
        previous_interaction_id (str | None): Id of the last successful interaction.
        total_tokens (TokenUsage): Cumulative token usage for the whole conversation.
        current_interaction_tokens (TokenUsage): Token usage of the latest interaction.
    """

    def __init__(
        self,
        model_name: str,
        enable_google_search_grounding: bool,
        custom_url_content_fetch: bool,
    ) -> None:
        """
        Initializes a Conversation instance.

        Args:
            model_name (str): The name of the model to use for the conversation.
            enable_google_search_grounding (bool) : Whether google search tool is enabled or not.
            custom_url_content_fetch (bool) : Whether to use url content fetch tool calling capability or not.
        """
        self.id: str = uuid().hex
        self.model_name: str = model_name
        self.enable_google_search_grounding = enable_google_search_grounding
        self.custom_url_content_fetch = custom_url_content_fetch
        self.title: str | None = None
        self.client = GeminiClient()
        self.history: list[dict[str, Any]] = []
        self.config = load_config("readr.yml")
        # tools to be used by the LLM to fulfil the user request
        self.tools: list[dict[str, Any]] = []

        # this is used to keep track of the previous interaction id for getting back the
        # token usage in that interaction
        self.previous_interaction_id: str | None = None

        self.total_tokens: TokenUsage = {"input": 0, "output": 0, "total": 0}

        self.current_interaction_tokens: TokenUsage = {
            "input": 0,
            "output": 0,
            "total": 0,
        }

    def _add_to_history(self, question: str) -> None:
        """
        Adds a user input to the conversation history.

        Args:
            question (str): The user's input.
        """
        self.history.append(
            {"type": "user_input", "content": [{"type": "text", "text": f"{question}"}]}
        )

    def _remove_most_recent_from_history(self) -> None:
        """
        Removes the most recent entry from the conversation history.
        Does nothing if the history is empty.
        """
        if self.history:
            self.history.pop()

    def _save_interaction_steps(self, interaction: Interaction) -> None:
        """
        Saves the steps of an interaction to the conversation history.

        Args:
            interaction (Interaction): The interaction whose steps are to be saved.
        """
        # save all the steps in the interaction to the history list
        if interaction.steps:
            for step in interaction.steps:
                self.history.append(step.model_dump())

    def _record_usage_tokens(self, interaction: Interaction) -> None:
        """
        Record token usage for the current interaction.

        Updates `total_tokens` and `current_interaction_tokens`. If the interaction
        has no usage, or any count is missing or zero, the prior values are kept.

        Args:
            interaction (Interaction): The interaction to record usage from. Its
                                       cumulative usage is diffed against the running
                                       totals to derive this interaction's own usage.
        """

        if not interaction.usage:
            print("No tokens available for the interaction. Will hold prior values.")
            return

        input_tokens = interaction.usage.total_input_tokens
        output_tokens = interaction.usage.total_output_tokens
        total_tokens = interaction.usage.total_tokens

        if (
            input_tokens is None
            or input_tokens == 0
            or output_tokens is None
            or output_tokens == 0
            or total_tokens is None
            or total_tokens == 0
        ):
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
        This behavior of expecting a title in the response is defined in the system instruction prompt
        file.

        Args:
            response (str): The model's response text to search for a title line.

        Returns:
            str: The extracted title, or a default placeholder if none was found.
        """
        match = re.search(r"\[Title\]:\s*(.+)", response)
        title = "Whats in a title"  # Default title if not found
        if match:
            title = match.group(1)
        return title

    def _determine_url_presence(self, question: str) -> str | None:
        """
        Extracts url from the user prompt.

        Args:
            question (str): The user prompt.

        Returns:
            str | None: The first url found in the user prompt, or None if the prompt
                        contains no url.
        """
        pattern = r"https?://[^\s)]+"
        match = re.search(pattern, question)
        url = match.group(0) if match else None
        return url

    def _determine_url_intent(self, question: str, url: str) -> dict[str, Any] | None:
        """
        Determines the intent of the url in the user prompt. Invokes an LLM to determine this.
        Below is the sample input prompt to the LLM for this task and the sample output from
        the LLM.

        Sample input prompt:

        Message:
        Hey can you help me understand the keypoints in
        "<url>"

        Extracted URLs:
        - <url>

        Sample response:
        {"use_url":true,"url":"https://...","reason":"User wants the webpage summarized."}

        Args:
            question (str): The user prompt.
            url (str): The url extracted from the user prompt.

        Returns:
            dict[str, Any] | None: The url intent response from the LLM. See above for
                                   sample response. None if the LLM call failed, the
                                   response had no text, or its json block was missing
                                   or could not be decoded.
        """
        input_prompt = f"Message:\n{question} \n\nExtracted URLs:\n- {url}"

        interaction = self.client.create_interaction_to_determine_intent(
            model_name=self.model_name,
            input_prompt=input_prompt,
            system_instruction_file=self.config["model"][
                "decide_url_usage_intent_prompt"
            ],
        )
        if interaction is None or interaction.output_text is None:
            LOGGER.error(
                "Interaction response was none during url intent determination"
            )
            return None

        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```", interaction.output_text, re.DOTALL
        )

        intent = None
        if match:
            try:
                intent = json.loads(match.group(1))
            except JSONDecodeError:
                LOGGER.error(
                    "Error while decoding json response from LLM regarding url intent"
                )
        return intent

    def _build_tools_list(self, intent: dict[str, Any] | None) -> None:
        """
        Builds the tool list to be sent to the Google Gen AI SDK.
        Replaces `self.tools` with the tools needed for the current request.

        Args:
            intent (dict[str, Any] | None): The url intent as determined by the LLM from the user
                                            prompt. None if there was no url or the intent
                                            could not be determined.
        """
        self.tools = []
        LOGGER.info(f"The url intent is {intent}")

        if intent and intent["use_url"]:
            if self.custom_url_content_fetch:
                tool_desc = ArticleFetcherTool.get_tool_description()
                print(f"\n[NOTE]: {tool_desc['name']} is enabled for this request")
                self.tools.append(tool_desc)
            else:
                print(
                    "\n[NOTE]: 'url_context' inbuilt tool is enabled for this request"
                )
                self.tools.append({"type": "url_context"})

        if self.enable_google_search_grounding:
            print("\n[NOTE]: Google Search Grounding is enabled for this request")
            self.tools.append({"type": "google_search"})

        LOGGER.info(f"The current tool list is {self.tools}")

    def _setup_tool_capability(self, question: str) -> None:
        """
        Builds the tool list necessary to handle the user prompt/question.
        Determines whether the prompt contains a url and, if so, what the user wants done
        with it, then sets `self.tools` accordingly.

        Args:
            question (str): The user prompt to handle.
        """
        url = self._determine_url_presence(question)
        intent = None
        if url:
            LOGGER.info(f"Determined url : {url} from user prompt")
            intent = self._determine_url_intent(question, url)
        self._build_tools_list(intent)

    def _retrieve_citations(self, interaction: Interaction | None) -> Citations:
        """
        Retrieves the citations from the LLM response. Only possible if the built in
        tool : `google_search` is used.

        Args:
            interaction (Interaction | None) : The interaction from which to retrieve the citations.

        Returns:
            Citations : The citations associated with the google search performed by the LLM,
                        keyed by citation title. Each value holds the `url` and the `cited_text`.
                        If several citations share a title, the last one wins.
                        Empty if there are no citations.
        """
        citations: Citations = {}

        if interaction and interaction.steps and len(interaction.steps) > 0:
            for step in interaction.steps:
                if (
                    step.type == "model_output"
                    and step.content
                    and len(step.content) > 0
                ):
                    for content_block in step.content:
                        if content_block.type == "text" and content_block.annotations:
                            for annotation in content_block.annotations:
                                if (
                                    annotation.type == "url_citation"
                                    and annotation.title
                                    and annotation.url
                                ):
                                    citations[annotation.title] = {}
                                    cited_text = content_block.text[
                                        annotation.start_index : annotation.end_index
                                    ]
                                    citations[annotation.title]["url"] = annotation.url
                                    citations[annotation.title]["cited_text"] = (
                                        cited_text
                                    )
        return citations

    def _handle_interaction_exit(self, interaction: Interaction) -> None:
        """
        Handles what needs to happen last wrt an interaction: saves its steps to the
        history, records its token usage and remembers its id as the previous interaction.

        Args:
            interaction (Interaction): The interaction to handle.
        """
        self._save_interaction_steps(interaction)
        self._record_usage_tokens(interaction)
        self.previous_interaction_id = interaction.id

    def _handle_custom_tool_call_functionality(
        self, interaction: Interaction
    ) -> Interaction | None:
        """
        Handles the behavior of custom tool call functionality.
        1. Saves the prior interaction (steps, token usage, id) via `_handle_interaction_exit`.
        2. Checks for the suggested tool to use by the LLM.
        3. Invokes the appropriate tool with arguments.
        4. Adds the result of the tool call to history (to be fed to the model again).
        5. Creates a new interaction so the model can use the tool result.

        Expects `interaction` to contain a `function_call` step, which
        `_is_custom_tool_call_required` establishes before this is called.

        Args:
            interaction (Interaction): The prior interaction instance (in which the LLM suggested which tool to use based on the prompt).

        Returns:
            Interaction | None: The new interaction instance (where the model can use the result of tool to answer the original user prompt).
                                None if the interaction has no steps, the requested tool is
                                not recognised, or the new interaction could not be created.
        """
        self._handle_interaction_exit(interaction)

        current_interaction = None

        if interaction.steps:
            fc_step = next(s for s in interaction.steps if s.type == "function_call")
            if fc_step.name == ToolNames.ARTICLE_FETCHER.value:
                article_fetcher = ArticleFetcherTool()
                result = article_fetcher.execute(**fc_step.arguments)

                if result and len(result) > 0:
                    LOGGER.info(
                        f"Custom article fetcher has retrieved the contents of the article. Size : {len(result)}"
                    )

                self.history.append(
                    {
                        "type": "function_result",
                        "name": fc_step.name,
                        "call_id": fc_step.id,
                        "result": [{"type": "text", "text": json.dumps(result)}],
                    }
                )
                current_interaction = self.client.create_primary_interaction(
                    self.model_name,
                    self.history,
                    self.previous_interaction_id,
                    self.tools,
                    self.config["model"]["system_instruction_prompt"],
                )
        return current_interaction

    def _is_custom_tool_call_required(self, interaction: Interaction) -> bool:
        """
        Determines if a custom tool call needs to be handled for this interaction.

        True only if a custom (function) tool was declared in the request AND the model
        actually responded with a `function_call` step. A declared tool the model chose
        not to call (it answered directly) is not a tool call.

        Args:
            interaction (Interaction): The interaction returned by the model for the
                                       current request.

        Returns:
            bool: Whether the model asked for a custom tool to be called.
        """
        tool_call_required_via_tools_list = False
        tool_call_required_via_response = False
        for tool in self.tools:
            if tool["type"] == "function":
                tool_call_required_via_tools_list = True
                break
        if interaction.steps:
            for step in interaction.steps:
                if step.type == "function_call":
                    tool_call_required_via_response = True
                    break
        return tool_call_required_via_tools_list and tool_call_required_via_response

    def ask(self, question: str) -> tuple[str, Citations, TokenUsage, TokenUsage]:
        """
        Asks a question to the model and returns the response.

        1. Adds the question to the conversation history.
        2. Sets up the tools needed for the question (url context, custom tool, google search).
        3. Creates an interaction with the model (adding appropriate tools).
        4. If the model asked for a custom tool, runs it and creates a follow-up interaction
           so the model can answer using the tool result.
        5. If the interaction is successful, retrieves the model's response and citations,
           extracts a title (first response only), saves the interaction steps to history,
           and records the token usage.
        6. If an interaction fails, removes the most recent question from the history and raises a
           ValueError.

        Args:
            question (str): The question to ask the model.

        Returns:
            tuple[str, Citations, TokenUsage, TokenUsage]: The model's response, the
                citations (keyed by title, see `_retrieve_citations`), the total token
                usage of the conversation and the token usage of this interaction.

        Raises:
            ValueError: If an interaction could not be created.
        """
        self._add_to_history(question)
        self._setup_tool_capability(question)
        interaction = self.client.create_primary_interaction(
            self.model_name,
            self.history,
            self.previous_interaction_id,
            self.tools,
            self.config["model"]["system_instruction_prompt"],
        )
        if interaction is None:
            self._remove_most_recent_from_history()
            raise ValueError("Error 1: Interaction could not be created")

        is_custom_tool_call_required = self._is_custom_tool_call_required(interaction)
        if is_custom_tool_call_required:
            interaction = self._handle_custom_tool_call_functionality(interaction)
            if interaction is None:
                self._remove_most_recent_from_history()
                raise ValueError("Error 2: Interaction could not be created")

        citations = self._retrieve_citations(interaction)
        response = interaction.output_text or "Sorry, what was that again?"

        self.title = (
            self._extract_title_from_interaction(response)
            if self.title is None
            else self.title
        )
        self._handle_interaction_exit(interaction)
        return response, citations, self.total_tokens, self.current_interaction_tokens

    def persist(self) -> None:
        """
        Persists the conversation history to a file.

        Does nothing if no title has been set yet (i.e. no successful `ask()` call
        has occurred), since the title is used to derive the session's file name.

        Raises:
            RuntimeError: If writing the session file fails.
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

    def reload_session_data(self, prior_session_data: dict[str, Any]) -> None:
        """
        Reload provided session data into the conversation.

        Args:
            prior_session_data (dict[str, Any]) : Previous session data to be reloaded, as
                                                  written by `persist`.

        Raises:
            KeyError: If prior_session_data is missing any of the expected keys
                      (id, model_name, title, history, previous_interaction_id, total_tokens).
        """
        self.id = prior_session_data["id"]
        self.model_name = prior_session_data["model_name"]
        self.title = prior_session_data["title"]
        self.history = prior_session_data["history"]
        self.previous_interaction_id = prior_session_data["previous_interaction_id"]
        self.total_tokens = prior_session_data["total_tokens"]

    def is_session_available(self) -> bool:
        """
        Returns if the current session has any conversation history to save.

        Returns:
            bool : True if the history has at least one entry.
        """
        return self.history is not None and len(self.history) > 0

    def close(self) -> None:
        """
        Closes the conversation and releases any resources held by the client.
        """
        self.client.close()

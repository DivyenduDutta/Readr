import os
from dotenv import load_dotenv
from typing import Tuple, Dict
from google import genai
from google.genai.interactions import Interaction
from readr.utils.file_reader import retrieve_file_contents
from readr.constants.file_constants import FileConstants

class Conversation:
    '''
    A class to manage a conversation with the Google Gemini API.
    Maintains a history of user inputs and model responses, and 
    provides methods to ask questions and retrieve responses.
    '''
    def __init__(self, model_name: str):
        '''
        Initializes a Conversation instance.

        Args:
            model_name (str): The name of the model to use for the conversation.
        '''
        self.model_name = model_name
        self.history = list()
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

        # this is used to keep track of the previous interaction id for getting back the 
        # token usage in that interaction
        self.previous_interaction_id = None 

        self.total_tokens = {
            "input": 0,
            "output": 0, 
            "total": 0
        }

        self.current_interaction_tokens = {
            "input": 0,
            "output": 0, 
            "total": 0
        }

    def _add_to_history(self, question: str):
        '''
        Adds a user input to the conversation history.

        Args:
            question (str): The user's input.
        '''
        self.history.append(
            {
                "type": "user_input",
                "content": [{"type": "text", "text": f"{question}"}]
            }
        )

    def _remove_most_recent_from_history(self):
        '''
        Removes the most recent entry from the conversation history.
        '''
        if self.history:
            self.history.pop()

    def _create_interaction(self) -> Interaction:
        '''
        Creates an interaction with the Google Gemini API.

        Returns:
            Interaction: The created interaction.
        '''
        interaction = None
        try:
            interaction = self.client.interactions.create(
                model = self.model_name,
                store = False, # opt out of server side storage
                system_instruction =  retrieve_file_contents(FileConstants.SYSTEM_INSTRUCTION_PROMPT_FILE_NAME.value),
                input = self.history,
                previous_interaction_id = self.previous_interaction_id if self.previous_interaction_id else None
            )
        except Exception as e:
            print(f"\n\nAn error occurred: {e}")
        finally:
            return interaction

    def _save_interaction_steps(self, interaction: Interaction):
        '''
        Saves the steps of an interaction to the conversation history.

        Args:
            interaction (Interaction): The interaction whose steps are to be saved.
        '''
        # save all the steps in the interaction to the history list
        for step in interaction.steps:
            self.history.append(step.model_dump())

    def _record_usage_tokens(self, interaction: Interaction):
        '''
        Records the total token usage and the current interaction's token usage.

        Args:
            interaction (Interaction): The interaction whose token usage is to be recorded.
        '''
        # Record the current interaction's token usage by subtracting the total tokens from the 
        # previous interactions
        self.current_interaction_tokens["input"] = interaction.usage.total_input_tokens - self.total_tokens["input"]
        self.current_interaction_tokens["output"] = interaction.usage.total_output_tokens - self.total_tokens["output"]
        self.current_interaction_tokens["total"] = interaction.usage.total_tokens - self.total_tokens["total"]

        # Record the token usage from the interaction to the total_tokens dictionary
        # Usage includes tokens from all previous interactions
        self.total_tokens["input"] = interaction.usage.total_input_tokens
        self.total_tokens["output"] = interaction.usage.total_output_tokens
        self.total_tokens["total"] = interaction.usage.total_tokens


    def ask(self, question: str) -> Tuple[str, Dict[str, int], Dict[str, int]]:
        '''
        Asks a question to the model and returns the response.

        1. Adds the question to the conversation history.
        2. Creates an interaction with the model.
        3. If the interaction is successful, retrieves the model's response, saves the interaction 
           steps to history, and records the token usage.
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
        '''
        self._add_to_history(question)
        interaction = self._create_interaction()
        if interaction is None:
            self._remove_most_recent_from_history()
            self.previous_interaction_id = None
            raise ValueError("Error: Interaction could not be created")
        response = interaction.steps[-1].content[0].text
        self._save_interaction_steps(interaction)
        self._record_usage_tokens(interaction)
        self.previous_interaction_id = interaction.id
        return response, self.total_tokens, self.current_interaction_tokens

    def close(self):
        '''
        Closes the conversation and releases any resources held by the client.
        '''
        self.client.close()

import os
from dotenv import load_dotenv
from google import genai
from google.genai.interactions import Interaction

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
                input = self.history
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

    def ask(self, question: str) -> str:
        '''
        Asks a question to the model and returns the response.

        Args:
            question (str): The question to ask the model.
        Returns:
            str: The model's response.
        Raises:
            ValueError: If the interaction could not be created.
        '''
        self._add_to_history(question)
        interaction = self._create_interaction()
        if interaction is None:
            raise ValueError("Error: Interaction could not be created")
        response = interaction.steps[-1].content[0].text
        self._save_interaction_steps(interaction)
        return response

    def close(self):
        '''
        Closes the conversation and releases any resources held by the client.
        '''
        self.client.close()

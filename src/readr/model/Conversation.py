import os
from dotenv import load_dotenv
from google import genai
from google.genai.interactions import Interaction

class Conversation:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.history = list()
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

    def _add_to_history(self, question: str):
        self.history.append(
            {
                "type": "user_input",
                "content": [{"type": "text", "text": f"{question}"}]
            }
        )

    def _create_interaction(self) -> Interaction:
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
        # save all the steps in the interaction to the history list
        for step in interaction.steps:
            self.history.append(step.model_dump())

    def ask(self, question: str) -> str:
        self._add_to_history(question)
        interaction = self._create_interaction()
        if interaction is None:
            raise ValueError("Error: Interaction could not be created")
        response = interaction.steps[-1].content[0].text
        self._save_interaction_steps(interaction)
        return response

    def close(self):
        self.client.close()

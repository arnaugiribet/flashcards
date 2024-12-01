import csv
from io import StringIO
from src.backend.flashcard_class import Flashcard

class FlashcardGenerator:
    def __init__(self, llm_client):
        """
        Initialize the FlashcardGenerator with an LLM client.
        """
        self.llm_client = llm_client

    def generate_flashcards(self, text_input):
        """
        Generate flashcards from the provided text input.
        """
        response = self.llm_client.query(text_input)
        flashcards = self.create_flashcards_from_response(response)

        return flashcards

    def create_flashcards_from_response(self, response):
        """
        Transform the LLM's raw text output into a list of Flashcard instances.
    
        Processes a CSV-formatted response from the Language Learning Model,
        converting each row into a structured Flashcard object. The method 
        handles complex parsing scenarios, including:
        - Escape characters in questions and answers
        - Comma-separated values
        - Quoted text with special characters
    
        :param response: Raw text output from the LLM, formatted as CSV
        :return: A list of Flashcard objects created from the parsed response
        :raises: Potential parsing errors if the CSV format is invalid
        """
        flashcards = []

        # Use StringIO to treat the response as a file-like object for the CSV reader
        response_io = StringIO(response)
        reader = csv.reader(response_io, quotechar='"', escapechar='\\')

        # Iterate over each row in the CSV response
        for row in reader:
            question, answer = row
            card_i = Flashcard(question.strip(), answer.strip())
            flashcards.append(card_i)

        return flashcards

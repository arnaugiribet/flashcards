import csv
from io import StringIO

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
        flashcards = self.parse_response(response)
        return flashcards

    def parse_response(self, response):
        """
        Parse the LLM's response into a list of tuples representing flashcards.
        The expected format is CSV, where the response contains question,answer pairs.
        Handle cases where the question or answer contains escape characters (e.g., \n, \t, commas).
        """
        flashcards = []

        # Use StringIO to treat the response as a file-like object for the CSV reader
        response_io = StringIO(response)
        reader = csv.reader(response_io, quotechar='"', escapechar='\\')

        # Iterate over each row in the CSV response
        for row in reader:
            question, answer = row
            flashcards.append((question.strip(), answer.strip()))

        return flashcards

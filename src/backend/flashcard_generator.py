import csv
from io import StringIO
from src.backend.flashcard_class import Flashcard

class FlashcardGenerator:
    def __init__(self, llm_client):
        """
        Initialize the FlashcardGenerator with an LLM client.
        """
        self.llm_client = llm_client

    def generate_flashcards(self, text_input, proposed_flashcards = [], feedback = ""):
        """
        Generate flashcards from the provided text input.
        """
        system_message = (
            "You are an expert in creating questions and answers out of study material.")
        if not feedback or not proposed_flashcards:
            prompt = (
            "Transform the following text (within triple claudators) into questions and answers "
            f"for studying. [[[{text_input}]]] "
            "Return it in purely CSV format without title or prefaces, like this: "
            "\"Who was Mozart?\",\"A classical composer\"\n"
            "\"What is ice?\",\"Frozen water\"\n"
            "Notice how every question and answer start and end with double quotes, to distinguish "
            "between commas in the sentence or the comma separator."
            "Do not add 'Question: ' or 'Answer: ' in the response."
            )
        elif feedback and proposed_flashcards:
            flashcards_string = "\n".join([flashcard.short_str() for flashcard in proposed_flashcards])
            prompt = (
            "The following text (within triple claudators) was transformed into questions and answers "
            "for studying. [[[{text_input}]]] "
            "Regenerate the following cards (only when necessary) according to the feedback provided. "
            f"Within double claudators are the cards: [[{flashcards_string}]] "
            f"And between claudators is the feedback to modify them: [{feedback}] "
            "Return it in purely CSV format without title or prefaces, like this: "
            "\"Who was Mozart?\",\"A classical composer\"\n"
            "\"What is ice?\",\"Frozen water\"\n"
            "Notice how every question and answer start and end with double quotes, to distinguish "
            "between commas in the sentence or the comma separator."
            "Do not add 'Question: ' or 'Answer: ' in the response."
            "Remember to only update the flashcards if needed according to the feedback with claudators."
            )
        else:
            raise ValueError("Empty proposed flashcards or feedback")

        response = self.llm_client.query(prompt, system_message)
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

        print("Turning LLM output into flashcards...")
        flashcards = []

        # Use StringIO to treat the response as a file-like object for the CSV reader
        response_io = StringIO(response)
        reader = csv.reader(response_io, quotechar='"', escapechar='\\')

        # Iterate over each row in the CSV response
        for row in reader:
            question, answer = row
            card_i = Flashcard(question.strip(), answer.strip())
            flashcards.append(card_i)

        print("Flashcards were created")
        return flashcards

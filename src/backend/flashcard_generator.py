import csv
from io import StringIO
from flashcards.models import Flashcard
import logging

class FlashcardGenerator:
    def __init__(self, llm_client):
        """
        Initialize the FlashcardGenerator with an LLM client.
        """
        self.llm_client = llm_client

        # Logger set up
        self.logger = logging.getLogger("src/backend/flashcard_generator.py")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def generate_flashcards(self, user, deck, text_input, context, proposed_flashcards = [], feedback = ""):
        """
        Generate flashcards from the provided text input.
        """
        system_message = (
            "You are an expert in creating questions and answers out of study material."
            "You follow the guidelines precisely."
        )
        if not feedback or not proposed_flashcards:
            prompt = (
            "Your task is to transform the study material below into questions and answers "
            f"for studying.\n The rules you must follow are:\n"
            " - Make sure the cards are in the same language of the text.\n"
            " - Return it in purely CSV format without title or prefaces, like this: "
            "\"Who was Mozart?\",\"A classical composer\"\n"
            "\"What is ice?\",\"Frozen water\"\n "
            " - Notice how every question and answer start and end with double quotes, to distinguish "
            "between commas in the sentence or the comma separator.\n"
            " - Questions and answers must each be surrounded by quotes. The question must be separated from the answer with a comma.\n"
            " - Different questions and answers must be separated with a new line. "
            " - Do not add 'Question: ' or 'Answer: ' in the response."
            " - Additionally, the user has added the context below. Please follow it too."
            f"\nUser context:\n{context}\n"
            f"\nThe study material is:\n{text_input}"
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
            "\"What is ice?\",\"Frozen water\"\n "
            "Notice how every question and answer start and end with double quotes, to distinguish "
            "between commas in the sentence or the comma separator. "
            "Questions and answers must each be surrounded by quotes. The question must be separated from the answer with a comma. "
            "Different questions and answers must be separated with a new line. "
            "Do not add 'Question: ' or 'Answer: ' in the response."
            "Remember to only update the flashcards if needed according to the feedback with claudators."
            )
        else:
            raise ValueError("Empty proposed flashcards or feedback")

        # Query LLM
        response, tokens = self.llm_client.query(prompt, system_message)
        
        try:
            # Attempt to create flashcards directly from the LLM response
            flashcards = self.create_flashcards_from_response(response, user, deck)
            self.logger.info("Flashcards created on the first try")
        except Exception as e:
            # If an error occurs, log it and attempt to enforce formatting on the response
            self.logger.warning(f"Initial flashcard creation failed: {e}. Attempting to clean the response.")
            try:
                clean_response, clean_tokens = self.enforce_format(response)
                tokens += clean_tokens
                flashcards = self.create_flashcards_from_response(clean_response, user, deck)
                self.logger.info("Flashcards created on the second try (after cleaning format)")
            except Exception as clean_error:
                # If enforcing the format also fails, log the error and return an empty list
                self.logger.error(f"Failed to create flashcards even after cleaning: {clean_error}")
                raise ValueError("Failed to create flashcards in second attempt (after cleaning).")

        return (flashcards, tokens)

    def enforce_format(self, response):
        system_message = (
            "You are an expert in creating questions and answers out of study material, and in the same language."
        )
        prompt = (
            "Ensure the following question and answers (within triple claudators) have the proper formatting. "
            "The proper format should be exactly like this: "
            "\"Who was Mozart?\",\"A classical composer\"\n"
            "\"What is ice?\",\"Frozen water\"\n "
            "Questions and answers must each be surrounded by quotes. The question must be separated from the answer with a comma. "
            "Different questions and answers must be separated with a new line. "
            "If the original response has a different formatting, fix it. "
            "Return only the cleaned response. This is the original response to be cleaned: "
            f"[[[{response}]]]"
            )

        clean_response, tokens = self.llm_client.query(prompt, system_message)
        return (clean_response, tokens)
        

    def create_flashcards_from_response(self, response, user, deck):
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

        self.logger.info("Turning LLM output into flashcards...")
        
        # Remove leading/trailing whitespace
        response = response.strip()  
    
        # Ensure the response has a trailing newline
        if not response.endswith('\n'):
            response += '\n'

        self.logger.debug(f"string from which generate we must flashcards:\n{repr(response)}")

        # Use StringIO to treat the response as a file-like object for the CSV reader
        response_io = StringIO(response)
        reader = csv.reader(response_io, quotechar='"', escapechar='\\')

        flashcards = []
        flashcard_errors = 0
        # Iterate over each row in the CSV response
        for idx, row in enumerate(reader):
            try:
                # Attempt to unpack the row into question and answer
                question, answer = row # this may already raise a ValueError if there aren't exactly 2 items to unpack
                len_question, len_answer = len(question), len(answer)
                if len_question==0 or len_answer==0: # when 2 items were unpacked, but some of them are empty
                    raise ValueError(f"Question length: {len_question}. Answer length: {len_answer}")

                # Create and append the flashcard
                card_i = Flashcard(
                    question=question.strip(), 
                    answer=answer.strip(), 
                    user=user,
                    deck=deck,
                    accepted=False
                )
                flashcards.append(card_i)
            except ValueError as ve:
                flashcard_errors += 1
                # Log the error with details about the problematic row
                self.logger.error(f"Row {idx+1} is invalid or malformed: {row}. Error: {ve}")
                # Skip the row and continue
                continue

        self.logger.debug(f"length of flashcards list is: {len(flashcards)}")
        if len(flashcards)==0:
            self.logger.error("No valid flashcards were created. The string may be malformed or empty.")
            raise ValueError("No valid flashcards generated.")

        proportion_errors = flashcard_errors/(idx+1)
        if proportion_errors>0.5:
            self.logger.error(f"{proportion_errors*100}% of rows contained errors")
            raise ValueError(f"Over 50% of rows with errors")

        self.logger.info("Flashcards were created")
        return flashcards

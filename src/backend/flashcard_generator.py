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
        # flashcards = self.parse_response(response)
        return response

    def parse_response(self, response):
        """
        Parse the LLM's response into a list of tuples representing flashcards.
        """
        # Assuming the LLM returns output in the format:
        # "Question: What is X?\nAnswer: X is Y.\n..."
        lines = response.split("\n")
        flashcards = []
        for line in lines:
            if line.startswith("Question:") and "Answer:" in line:
                question, answer = line.split("Answer:", 1)
                flashcards.append((question.replace("Question:", "").strip(),
                                   answer.strip()))
        return flashcards

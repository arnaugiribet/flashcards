import uuid
from datetime import datetime, date

class Flashcard:
    def __init__(self, question, answer, due_date="today"):
        """
        Initialize a new Flashcard instance.
        
        :param question: The question or prompt for the flashcard
        :param answer: The answer or explanation for the flashcard
        :param due_date: The specific date when the flashcard is due (default is today)
        """
        self._id = str(uuid.uuid4())  # Generate a unique identifier
        self._question = question
        self._answer = answer
        self._creation_date = datetime.now().date()
        
        # Explicitly set due date based on the input
        self._due = self._creation_date if due_date == "today" else due_date

    # Getter for ID (read-only)
    @property
    def id(self):
        """Get the unique identifier for the flashcard."""
        return self._id

    # Getter and Setter for Question
    @property
    def question(self):
        """Get the flashcard's question."""
        return self._question
    
    @question.setter
    def question(self, value):
        """Set the flashcard's question."""
        self._question = value

    # Getter and Setter for Answer
    @property
    def answer(self):
        """Get the flashcard's answer."""
        return self._answer
    
    @answer.setter
    def answer(self, value):
        """Set the flashcard's answer."""
        self._answer = value

    # Getter for Creation Date (read-only)
    @property
    def creation_date(self):
        """Get the flashcard's creation date."""
        return self._creation_date

    # Getter and Setter for Due Date
    @property
    def due(self):
        """Get the flashcard's due date."""
        return self._due
    
    @due.setter
    def due(self, value):
        """Set the flashcard's due date."""
        self._due = value

    def __str__(self):
        """
        String representation of the Flashcard.
        
        :return: A formatted string with flashcard details
        """
        return (f"Flashcard (ID: {self._id})\n"
                f"Question: {self._question}\n"
                f"Answer: {self._answer}\n"
                f"Created: {self._creation_date}\n"
                f"Due: {self._due}")
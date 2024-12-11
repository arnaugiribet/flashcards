from django.db import models
import uuid
from datetime import date

class Flashcard(models.Model):
    """
    Django model representing a flashcard.
    
    Key Design Goals:
    - Maintain unique ID generation
    - Keep creation and due date functionality
    - Enable seamless transition from custom class to database model
    """
    
    # Fields corresponding to the database
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField()  # Direct field (no need for _question)
    answer = models.TextField()    # Direct field (no need for _answer)
    creation_date = models.DateField(auto_now_add=True)
    due = models.DateField(default=date.today)

    def __str__(self):
        """
        String representation of the Flashcard.
        Matches the original class's __str__ method.
        """
        return (f"Flashcard ID: {self.id}\n"
                f"Question: {self.question}\n"
                f"Answer: {self.answer}\n"
                f"Created: {self.creation_date}\n"
                f"Due: {self.due}")

    def short_str(self):
        """
        Short string representation, preserving original method.
        """
        return (f"Question: {self.question}\n"
                f"Answer: {self.answer}")

    # Optionally, override save method if you have custom logic to implement
    def save(self, *args, **kwargs):
        """
        Override save method to handle any custom saving logic.
        This allows you to add additional processing if needed.
        """
        super().save(*args, **kwargs)

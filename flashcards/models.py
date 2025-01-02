from django.db import models
import uuid
from datetime import date
from django.contrib.auth.models import User
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class Deck(models.Model):
    """
    Model representing a deck of flashcards.
    
    A deck can contain other decks (nested decks) and belongs to a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    parent_deck = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subdeck')
    
    def __str__(self):
        return f"{self.name} (User: {self.user.username})"

class Flashcard(models.Model):
    """
    Django model representing a flashcard.
    
    Each flashcard belongs to a specific deck and user.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField()
    answer = models.TextField()
    creation_date = models.DateField(auto_now_add=True)
    due = models.DateField(default=date.today)
    current_interval = models.IntegerField(default=1)  # Interval in days
    ease_factor = models.FloatField(default=2.5)  # Starting ease factor
    history = models.JSONField(default=list)

    # Relationship to Deck and User
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='flashcards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
        
    def __str__(self):
        return (f"Flashcard ID: {self.id}\n"
                f"Question: {self.question}\n"
                f"Deck: {self.deck.name}\n"
                f"User: {self.user.username}\n"
                f"Due: {self.due}\n"
                f"Interval: {self.current_interval}\n"
                f"Ease Factor: {self.ease_factor}")

    def short_str(self):
        """
        Short string representation.
        """
        return (f"Question: {self.question}\n"
                f"Answer: {self.answer}")

    def save(self, *args, **kwargs):
        """
        Override save method to ensure user is associated with the card's deck.
        """
        super().save(*args, **kwargs)

    def update_review(self, quality: str):
        """
        Updates the flashcard's review state based on custom quality levels.
        
        Args:
            quality (str): The review quality ('Again', 'Hard', 'Good', 'Easy').
        
        Raises:
            ValueError: If the quality is not one of the allowed values.
        """
        logger.debug(f"Updating the due date")

        # Map quality levels to numeric values
        quality_map = {
            "again": 0,
            "hard": 2,
            "good": 3,
            "easy": 4
        }

        # Validate quality
        if quality not in quality_map:
            raise ValueError(f"Invalid quality '{quality}'. Must be one of: {', '.join(quality_map.keys())}")
        
        # Get the numeric value for the given quality
        quality_value = quality_map[quality]
        old_due_date = self.due  # to print in the log

        if quality_value == 0:  # 'Again'
            # Reset interval and ease factor for failed reviews
            self.current_interval = 0
        else:
            # Update the ease factor
            adjustment = 0.1 - (5 - quality_value) * (0.08 + (5 - quality_value) * 0.02)
            self.ease_factor = max(1.3, self.ease_factor + adjustment)
            
            # Update the interval
            adjusted_current_interval = self.current_interval
            if self.current_interval == 0:
                adjusted_current_interval = 1
            self.current_interval = round(adjusted_current_interval * self.ease_factor)
        
        # Update the due date
        self.due = date.today() + timedelta(days=self.current_interval)

        # Append the review event to the history
        review_event = {
            "date": str(date.today()),
            "quality": quality,
            "interval": self.current_interval,
            "ease_factor": self.ease_factor
        }
        self.history.append(review_event)

        # Log the change
        logger.info(f"Updated card ID {self.id} for user {self.user.id} from due date {old_due_date} to {self.due} (result: {quality})")
        self.save()

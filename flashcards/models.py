from django.db import models
import uuid
from datetime import date
from django.contrib.auth.models import User

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
        """
        # Map quality levels to numeric values
        quality_map = {
            "Again": 0,
            "Hard": 2,
            "Good": 3,
            "Easy": 4
        }
        
        # Get the numeric value for the given quality
        quality_value = quality_map.get(quality, 0)  # Default to 'Again' if invalid input
        
        if quality_value == 0:  # 'Again'
            # Reset interval and ease factor for failed reviews
            self.current_interval = 1
        else:
            # Update the ease factor
            adjustment = 0.1 - (5 - quality_value) * (0.08 + (5 - quality_value) * 0.02)
            self.ease_factor = max(1.3, self.ease_factor + adjustment)
            
            # Update the interval
            self.current_interval = round(self.current_interval * self.ease_factor)
        
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

        self.save()
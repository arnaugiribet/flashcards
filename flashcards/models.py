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
 
    @classmethod
    def order_decks(cls, decks):
        """
        Orders decks such that children follow their parent decks.
        """
        ordered_decks = []

        # A mapping from deck ID to deck object for quick lookups
        deck_map = {deck.id: deck for deck in decks}

        # Helper function to recursively add decks and their children
        def add_deck_and_children(deck):
            if deck not in ordered_decks:  # Avoid duplicates
                ordered_decks.append(deck)
                # Find all children of the current deck
                children = [d for d in decks if d.parent_deck == deck]
                # Sort children (optional, by name or another attribute)
                children.sort(key=lambda d: d.name)
                for child in children:
                    add_deck_and_children(child)

        # Start with root decks (parent_deck is None)
        root_decks = [deck for deck in decks if deck.parent_deck is None]
        root_decks.sort(key=lambda d: d.name)  # Sort roots by name, optional

        for root_deck in root_decks:
            add_deck_and_children(root_deck)

        return ordered_decks


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
    ease_factor = models.FloatField(default=1.5)  # Starting ease factor
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

    def get_next_intervals_ease_factors(self):
        """
        Calculate the next review intervals and corresponding ease factors for each quality level.

        This method simulates the review process to predict the intervals (in days) and ease factors 
        for the four quality levels: "Again," "Hard," "Good," and "Easy." 
        These predictions help determine the outcomes of each possible review quality.

        Returns:
            tuple: A pair of dictionaries:
                - intervals (dict): Maps each quality ("again", "hard", "good", "easy") to the corresponding interval in days.
                - ease_factors (dict): Maps each quality to the new ease factor after applying the review adjustment.
        """
        # Mapping of review qualities to numeric values
        quality_map = {
            "again": 0,  # Quality: "Again" -> Reset the interval
            "hard": 2,   # Quality: "Hard" -> Minimal progress
            "good": 6,   # Quality: "Good" -> Default progress
            "easy": 10    # Quality: "Easy" -> Accelerated progress
        }

        # Initialize dictionaries for intervals and ease factors
        intervals = {}
        ease_factors = {}

        # Simulate outcomes for each quality level
        for quality, quality_value in quality_map.items():
            # Start with the current ease factor
            new_ease_factor = self.ease_factor
            
            if quality_value == 0:  # "Again" -> Reset the interval to 0
                interval = 0
            else:
                # Calculate the adjustment to the ease factor based on the quality value
                adjustment = 0.15 * (quality_value - 5)
                new_ease_factor = max(1.1, self.ease_factor + adjustment)  # Ensure ease factor doesn't drop below X
                
                # Calculate the next interval
                adjusted_current_interval = self.current_interval if self.current_interval > 0 else 1
                interval = round(adjusted_current_interval * new_ease_factor)

            # Store results for the current quality level
            intervals[quality] = interval
            ease_factors[quality] = new_ease_factor

        # Return the predicted intervals and ease factors
        return intervals, ease_factors



    def update_review(self, quality: str):
        """
        Updates the flashcard's review state based on custom quality levels.
        
        Args:
            quality (str): The review quality ('Again', 'Hard', 'Good', 'Easy').
        
        Raises:
            ValueError: If the quality is not one of the keys in the returned intervals.
        """
        # Dynamically retrieve valid qualities from the intervals dictionary
        intervals, ease_factors = self.get_next_intervals_ease_factors()
        valid_qualities = intervals.keys()

        # Validate the input quality
        if quality not in valid_qualities:
            raise ValueError(f"Invalid quality '{quality}'. Must be one of: {', '.join(valid_qualities)}")

        # Capture the old state for logging
        old_due_date = self.due
        old_interval = self.current_interval
        old_ease_factor = self.ease_factor

        # Update the flashcard based on the selected quality
        self.current_interval = intervals[quality]
        self.ease_factor = ease_factors[quality]
        self.due = date.today() + timedelta(days=self.current_interval)

        # Append the review event to the history
        review_event = {
            "date": str(date.today()),
            "quality": quality,
            "interval": self.current_interval,
            "ease_factor": self.ease_factor
        }
        self.history.append(review_event)

        # Log the detailed changes
        logger.info(
            f"Flashcard ID {self.id} for user {self.user.id} updated:"
            f"\n  Due date: {old_due_date} -> {self.due}"
            f"\n  Interval: {old_interval} -> {self.current_interval}"
            f"\n  Ease factor: {old_ease_factor:.2f} -> {self.ease_factor:.2f}"
        )

        # Save the updated state
        self.save()

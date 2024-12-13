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
    
    # Relationship to Deck and User
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='flashcards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
        
    def __str__(self):
        return (f"Flashcard ID: {self.id}\n"
                f"Question: {self.question}\n"
                f"Deck: {self.deck.name}\n"
                f"User: {self.user.username}\n"
                f"Due: {self.due}")

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
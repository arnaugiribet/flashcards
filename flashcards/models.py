from django.db import models
import uuid
from datetime import date, timedelta
from django.contrib.auth.models import User
import logging
from django.utils import timezone
from django.db.models import Sum, Max
from django.conf import settings

logger = logging.getLogger(__name__)

class UserPlan(models.Model):
    
    FREE = 'free'
    PRO = 'pro'
    ENTERPRISE = 'enterprise'

    PLAN_CHOICES = [
        (FREE, 'free'),
        (PRO, 'pro'),
        (ENTERPRISE, 'enterprise'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to default User model
    plan_type = models.CharField(
        max_length=50,
        choices=PLAN_CHOICES,
        default=FREE  # Default to 'free'
    )
    total_tokens_allowed = models.IntegerField(default=10000)  # Default to 10000

    class Meta:
        db_table = 'user_plan'

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_type_display()} - {self.total_tokens_allowed} tokens"

class TokenUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='token_usage')
    tokens_used = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'token_usage'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} used {self.tokens_used} tokens at {self.timestamp}"

    @classmethod
    def get_period_usage(cls, user, hours):
        """
        Get total tokens used by user in the last specified hours
        """
        period = timezone.now() - timedelta(hours=hours)
        total_tokens = cls.objects.filter(
            user=user,
            timestamp__gte=period
        ).aggregate(total=Sum('tokens_used'))['total'] or 0
        
        return total_tokens

    @classmethod
    def get_total_usage(cls, user):
        """
        Get all-time total tokens used by user
        """
        return cls.objects.filter(user=user).aggregate(
            total=Sum('tokens_used'))['total'] or 0
    
    @classmethod
    def get_most_recent_timestamp(cls, user):
        """
        Get the most recent timestamp of token usage for a user
        """
        recent_timestamp = cls.objects.filter(user=user).aggregate(latest=Max('timestamp'))['latest']
        return recent_timestamp
            
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
        
    def get_descendants(self):
        """
        Recursively retrieve all descendant decks (children, grandchildren, etc.).
        """
        descendants = []
        children = self.subdeck.all()  # Get immediate sub-decks
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())  # Recursive call for deeper levels
        return descendants

    @property
    def has_document(self):
        return self.documents.exists()

    def document_id(self):
        doc = self.documents.first()
        return doc.id if doc else None


class UserDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # pdf, txt, docx
    s3_key = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='documents')

    def __str__(self):
        return f"{self.s3_key} ({self.file_type}) {self.user} - {self.uploaded_at}"

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
    document = models.ForeignKey(UserDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name='flashcards')
    bounding_box = models.JSONField(default=list, null=True, blank=True)
    accepted = models.BooleanField(default=True)
    
    # Relationship to Deck and User
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='flashcards')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flashcards')
        
    def __str__(self):
        return (f"Flashcard ID: {self.id}\n"
                f"Question: {self.question}\n"
                f"Answer: {self.answer[:40]}...\n"
                f"Deck: {self.deck.name if hasattr(self, 'deck') else 'No Deck'}\n"
                f"User: {self.user.username}\n"
                f"Due: {self.due}\n"
                f"Interval: {self.current_interval}\n"
                f"Ease Factor: {self.ease_factor}\n"
                f"Document: {self.document}\n"
                f"Bounding Box: {self.bounding_box}")

    def short_str(self):
        """
        Short string representation.
        """
        return (f"Question: {self.question}\n"
                f"Answer: {self.answer}")
        
    def short_id_question(self):
        """
        Shorter string representation.
        """
        return f"{self.id}\n{self.question[:10]}\n{self.answer[:10]}"

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



class FailedFeedback(models.Model):
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField()
    feedback_type = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically store when feedback was created

    def __str__(self):
        # If username exists and is a valid User, return a link to their profile, else show the email
        if self.username:
            return f"Feedback from {self.name} ({self.username}) - {self.email}"
        return f"Feedback from {self.name} ({self.email})"
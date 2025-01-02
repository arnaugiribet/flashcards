import logging
from datetime import timedelta
from django.utils import timezone

# Set up logger
logger = logging.getLogger(__name__)  # Use your module's name to name the logger

def spaced_repetition(card, result):
    """
    Update the due date of a flashcard based on the spaced repetition algorithm,
    depending on the result of the user's review.
    """
    current_date = timezone.now().date()
    
    # Spaced repetition intervals (modify these as per your algorithm's needs)
    interval_map = {
        'again': timedelta(seconds=600),  # Reset to shortest interval (e.g., 10 minutes)
        'hard': timedelta(days=1),        # Slightly longer interval (e.g., 1 day)
        'good': timedelta(days=3),        # Moderate interval (e.g., 3 days)
        'easy': timedelta(days=5)         # Longest interval (e.g., 5 days)
    }
    
    # Get the interval based on the result
    interval = interval_map.get(result)
    
    if not interval:
        raise ValueError("Invalid result value: must be one of ['again', 'hard', 'good', 'easy']")
    
    # Update the card's due date
    old_due_date = card.due  # Capture the old due date before modifying it
    card.due = current_date + interval
    card.save(update_fields=['due'])

    # Log the change
    logger.info(f"Updated card ID {card.id} for user {card.user.id} from due date {old_due_date} to {card.due} (result: {result})")

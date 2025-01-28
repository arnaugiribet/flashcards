import logging
from flashcards.models import TokenUsage

# Logger set up
logger = logging.getLogger("src/backend/usage_limits.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class InsufficientTokensError(Exception):
    """Raised when user doesn't have enough tokens available"""
    pass

def assert_input_length(input_text):
    logger.info('Checking length of input text...')
    len_input_text = len(input_text)
    logger.debug(f'The text has {len_input_text} characters')
    if len_input_text > 30000:
        raise ValueError(f"Input text length {len(input_text)} exceeds maximum allowed length of 30000 characters")

def estimate_tokens(text):
    """
    Quick and dirty token estimation:
    - Average English word is ~1.3 tokens
    - Add 20% buffer for safety
    """
    input_tokens = int(len(text.split()) * 1.3 * 1.2)
    output_tokens = 750
    return input_tokens + output_tokens

def assert_enough_tokens(user, input_text):
    logger.info('Checking user has enough tokens to proceed...')

    ### Available tokens
    # Get tokens used in the current time period (4 hours)
    hours = 4
    tokens_used_during_period = TokenUsage.get_period_usage(user, hours)
    logger.debug(f'User {user.username} consumed {tokens_used_during_period} tokens within the last {hours} hours')
    # Get maximum available tokens per period, from UserPlan table
    user_plan = user.userplan  # Using the OneToOne reverse relation
    max_tokens_per_period = user_plan.total_tokens_allowed
    logger.debug(f'User {user.username} has {max_tokens_per_period} tokens per period')
    # Calculate available tokens in current period
    available_tokens = max_tokens_per_period - tokens_used_during_period
    logger.debug(f'User {user.username} has {available_tokens} available tokens in this period')

    ### Expected token cost
    tokens_needed_estimate = estimate_tokens(input_text)
    
    ### Logic
    if available_tokens >= tokens_needed_estimate:
        logger.debug('Enough tokens left')
        return True
    else:
        logger.info('Not enough tokens left!')
        most_recent_usage_timestamp = TokenUsage.get_most_recent_timestamp(user)
        logger.info(f'Last token consumption happend at {most_recent_usage_timestamp}')

        error = InsufficientTokensError(
            f"Insufficient tokens. Plan limit: {max_tokens_per_period}, "
            f"Used: {tokens_used_during_period}, Available: {available_tokens}, "
            f"Needed: {tokens_needed_estimate}"
        )

        error.most_recent_usage_timestamp = most_recent_usage_timestamp
        raise error

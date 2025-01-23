from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
from src.backend.usage_limits import assert_input_length, assert_enough_tokens
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def generate_flashcards(content, content_format, context, user):
    """
    Service function to generate flashcards from the input file and context.

    Args:
        content: File object or StringIO object containing the input content
        content_format: String indicating the format ('txt' or 'string')
        context: Additional context string from the HTTP request

    Returns:
        A list of generated flashcards.

    Raises:
        ValueError: If no valid input is provided or if file format is invalid
        RuntimeError: If flashcard generation fails
    """
    logger.debug(f"Generating flashcards with format: {content_format}")
    llm_api_key = settings.LLM_API_KEY
    llm_client = LLMClient(llm_api_key)
    generator = FlashcardGenerator(llm_client)

    # Combine file and context inputs
    input_text = context or ""

    # Process content based on format
    if content_format == '.txt':
        # For file uploads
        input_text += "\n" + content.read().decode('utf-8')
    elif content_format == 'string':
        # For string input
        input_text += "\n" + content.getvalue()
    else:
        raise ValueError(f"Unsupported content format: {content_format}")

    if not input_text.strip():
        raise ValueError("No input provided to generate flashcards")

    # Check length of inut text and user token consumption before proceeding
    assert_input_length(input_text)
    assert_enough_tokens(user, input_text)

    try:
        # Generate flashcards using the pipeline
        flashcards = generator.generate_flashcards(text_input=input_text)
        return flashcards
    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        raise RuntimeError("Failed to generate flashcards") from e
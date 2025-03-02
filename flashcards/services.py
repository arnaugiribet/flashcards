from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
from src.backend.usage_limits import assert_input_length, assert_enough_tokens
from src.backend.input_content_processors import get_docx, get_pdf
import logging
from django.conf import settings
from .models import TokenUsage

logger = logging.getLogger("services.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_matched_flashcards_to_text(doc_id, text, page, boxes, user):
    logger.debug(f"Processing selected text...")

    flashcards = generate_flashcards(content=text, content_format='raw_string', context='', user=user)
    for flashcard in flashcards:
        match_flashcard_to_text(flashcard, doc_id, text, page, boxes)

    return True

def match_flashcard_to_text(flashcard, doc_id, text, page, boxes):

    pass

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
        raw_user_text = content.read().decode('utf-8')
        logger.debug(f"input .txt was read as:\n{raw_user_text}")
        input_text += "\n" + raw_user_text

    elif content_format == '.docx':
        raw_user_text = get_docx(content)
        logger.debug(f"input .docx was read as:\n{raw_user_text}")
        input_text += "\n" + raw_user_text

    elif content_format == '.pdf':
        raw_user_text = get_pdf(content)
        logger.debug(f"input .pdf was read as:\n{raw_user_text}")
        input_text += "\n" + raw_user_text

    elif content_format == 'string':
        # For stringIO input
        raw_user_text = content.getvalue()
        input_text += "\n" + raw_user_text
    
    elif content_format == 'raw_string':
        # For raw string input
        raw_user_text = content
        input_text += "\n" + raw_user_text

    else:
        raise ValueError(f"Unsupported content format: {content_format}")

    if not input_text.strip():
        raise ValueError("No input provided to generate flashcards")

    # Check length of inut text and user token consumption before proceeding
    assert_input_length(raw_user_text)
    assert_enough_tokens(user, input_text)

    try:
        # Generate flashcards using the pipeline
        flashcards, tokens = generator.generate_flashcards(text_input=input_text)

        # Update TokenUsage database
        logger.debug(f"Total tokens used: {tokens}")
        TokenUsage.objects.create(
            user=user,
            tokens_used=tokens
        )

        return flashcards
    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        raise RuntimeError("Failed to generate flashcards") from e
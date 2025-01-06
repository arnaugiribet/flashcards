from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Service function for processing the file and context
def generate_flashcards(file, context):
    """
    Service function to generate flashcards from the input file and context.

    :param file: File object from the HTTP request.
    :param context: Additional context string from the HTTP request.
    :return: A list of generated flashcards.
    """
    logger.debug(f"Generating flashcards...")
    llm_api_key = settings.LLM_API_KEY
    logger.debug(f"api_key is: {llm_api_key}")
    llm_client = LLMClient(llm_api_key)
    generator = FlashcardGenerator(llm_client)

    # Combine file and context inputs
    input_text = context or ""
    if file:
        try:
            input_text += "\n" + file.read().decode('utf-8')  # Assuming UTF-8 encoding
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise ValueError("Invalid file format or encoding")

    if not input_text.strip():
        raise ValueError("No input provided to generate flashcards")

    try:
        # Generate flashcards using the pipeline
        flashcards = generator.generate_flashcards(text_input=input_text)
        return flashcards
    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        raise RuntimeError("Failed to generate flashcards") from e

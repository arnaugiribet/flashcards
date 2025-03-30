from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
from src.backend.usage_limits import assert_input_length, assert_enough_tokens
from src.backend.input_content_processors import get_docx, get_pdf
import logging
from django.conf import settings
from flashcards.models import TokenUsage, UserDocument
from rapidfuzz.distance import Levenshtein

logger = logging.getLogger("services.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def match_selected_text_to_word_boxes(text, words):
    logger.debug(f"Matching selected text to word boxes...")
    words_list = [word['text'] for word in words]
    # Example usage
    best_start, best_end, best_score = find_best_match_edit_distance(text, words_list)

    if best_start is not None:
        logger.debug(f"Best Match: {' '.join(words_list[best_start:best_end])}")
        logger.debug(f"Start Index: {best_start}, End Index: {best_end - 1}")
        logger.debug(f"Distance: {best_score}")

    return True
    

def find_best_match_edit_distance(text, words):
    # Split text into words and spaces
    vectored_text = text.split()
    vectored_text_with_spaces = [" "] * (len(vectored_text) * 2 - 1)
    vectored_text_with_spaces[::2] = vectored_text
    
    best_score = float('inf')
    best_start, best_end = None, None
    
    logger.debug(f"Text original: {text}")
    logger.debug(f"Words original: {words}")
    logger.debug(f"vectored_text: {vectored_text}")
    logger.debug(f"vectored_text_with_spaces: {vectored_text_with_spaces}")
    for i in range(len(words) - len(vectored_text_with_spaces) + 1):
        span = words[i:i + len(vectored_text_with_spaces)]
        logger.debug(f"Now checking span: {span}")
        distance = Levenshtein.distance("".join(vectored_text_with_spaces), " ".join(span))
        logger.debug(f"Distance: {distance}")
        if distance < best_score:
            best_score = distance
            best_start, best_end = i, i + len(vectored_text_with_spaces)

    return best_start, best_end, best_score


def get_matched_flashcards_to_text(doc_id, text, page, boxes, user):
    logger.debug(f"Processing selected text...")

    flashcards = generate_flashcards(content=text, content_format='raw_string', context='', user=user)
    for flashcard in flashcards:
        logger.debug(f"Matching flashcard:\n{flashcard}")
        match_flashcard_to_text(flashcard, doc_id, text, page, boxes)
        flashcard.save()
        logger.debug(f"Stored flashcard in db")

    return True

def format_boxes(boxes):
    logger.debug(f"Formatting boxes...")
    formatted_boxes = []
    for idx, box in enumerate(boxes):
        formatted_boxes.append(f"{idx},{box['text']}")

    formatted_boxes = '\n'.join(formatted_boxes)
    return formatted_boxes

def match_flashcard_to_text(flashcard, doc_id, text, page, boxes):

    formatted_boxes = format_boxes(boxes)
# Prepare prompt for the LLM
    prompt = f"""
CONTEXT:
I have a document with extracted text and a flashcard generated from this text.
I need to identify which specific text boxes the flashcard information came from.

FLASHCARD:
Question: {flashcard.question}
Answer: {flashcard.answer}

TEXT BOXES, in the format of idx,text\n
{formatted_boxes}

TASK:
Return ONLY the indices of the boxes that contain the information used to create this flashcard.
The indices should be provided as a comma-separated list of integers (e.g., "0, 3, 5").
If multiple boxes contributed to the flashcard, include all relevant indices.
If no boxes seem relevant, return "None".
"""
    system_message = "You are an expert at matching flashcards to their source text locations."

    # Call the LLM with the prompt
    llm_api_key = settings.LLM_API_KEY
    llm_client = LLMClient(llm_api_key)
    indices_response, tokens = llm_client.query(prompt, system_message)
    
    # Parse the response to get the box indices
    try:
        if indices_response.lower() == "none":
            box_indices = []
        else:
            box_indices = [int(idx.strip()) for idx in indices_response.split(",")]
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        logger.error(f"Original response: {indices_response}")
        box_indices = []
    
    # Store in flashcard: page, docId and boxes
    user_document = UserDocument.objects.get(id=doc_id)
    flashcard.page_number = page
    flashcard.document = user_document
    for idx in box_indices:
        if 0 <= idx < len(boxes):
            box_i = boxes[idx]['box']
            flashcard.bounding_box.append(box_i)
        
    print(flashcard)
    logger.debug(f"Matched flashcard to {len(box_indices)} boxes")
    logger.debug(f"Matched indices are:\n{box_indices}")
    return True

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
        flashcards, tokens = generator.generate_flashcards(text_input=input_text, user=user)

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
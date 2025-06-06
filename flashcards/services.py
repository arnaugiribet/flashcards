from src.backend.flashcard_generator import FlashcardGenerator
from src.backend.llm_client import LLMClient
from src.backend.usage_limits import assert_input_length, assert_enough_tokens
from src.backend.input_content_processors import get_docx, get_pdf
import logging
from django.conf import settings
from flashcards.models import TokenUsage, UserDocument
from rapidfuzz.distance import Levenshtein
from botocore.exceptions import ClientError
from boto3 import client as boto3_client

logger = logging.getLogger("services.py")
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def delete_document_from_s3(document):
    s3_client = boto3_client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    try:
        s3_client.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=document.s3_key)
        document.delete()
        return True
    except ClientError as e:
        logger.error(f"Error deleting document {document.id} from S3: {e}")
        return False

def match_selected_text_to_word_boxes(text, words):
    logger.debug(f"Matching selected text to word boxes...")
    words_list = [word['text'] for word in words]
    
    best_start, best_end, best_score = find_best_match_edit_distance(text, words_list)
    logger.debug(f"best_start: {best_start}, best_end: {best_end}")

    logger.debug(f"Best Match: {' '.join(words_list[best_start:best_end])}")
    logger.debug(f"Start Index: {best_start}, End Index: {best_end - 1}")
    logger.debug(f"Distance: {best_score}")

    # Return selected boxes
    boxes = words[best_start:best_end]

    return boxes
    

def find_best_match_edit_distance(text, words):
    # Split text into words and spaces
    vectored_text = text.split()
    
    best_score = float('inf')
    best_start, best_end = None, None
    
    logger.debug(f"Starting loop to check for best match. len(words): {len(words)}, len(vectored_text): {len(vectored_text)}")
    for i in range(len(words)):
        span = []
        j = i
        while j < len(words) and len("".join(span).split()) < len(vectored_text):
            span.append(words[j])
            j += 1

        # Only calculate distance if we have a valid span
        if len("".join(span).split()) >= len(vectored_text):
            current_text = " ".join(span)
            distance = Levenshtein.distance(" ".join(vectored_text), current_text)
            
            if distance < best_score:
                best_score = distance
                best_start, best_end = i, j

    return best_start, best_end, best_score


def get_matched_flashcards_to_text(doc_id, text, boxes, aiContext, user, deck):
    logger.debug(f"Processing selected text...")

    flashcards = generate_flashcards(content=text, content_format='raw_string', context=aiContext, user=user, deck=deck)
    logger.debug(f"Trying to match flashcards and store them in db...")
    for flashcard in flashcards:
        logger.debug(f"Matching flashcard:\n{flashcard}")
        match_flashcard_to_text(flashcard, doc_id, text, boxes)
        logger.debug(f"Trying to store flashcards in db...")
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

def match_flashcard_to_text(flashcard, doc_id, text, boxes):

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
    
    # Store in flashcard: docId and boxes
    user_document = UserDocument.objects.get(id=doc_id)
    flashcard.document = user_document
    for idx in box_indices:
        if 0 <= idx < len(boxes):
            box_i = boxes[idx]
            flashcard.bounding_box.append(box_i)
        
    print(flashcard)
    logger.debug(f"Matched flashcard to {len(box_indices)} boxes")
    logger.debug(f"Matched indices are:\n{box_indices}")
    return True

def generate_flashcards(content, content_format, context, user, deck):
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

    if not content.strip():
        raise ValueError("No input provided to generate flashcards")

    # Check length of inut text and user token consumption before proceeding
    assert_input_length(content)
    assert_enough_tokens(user, content)

    try:
        # Generate flashcards using the pipeline
        flashcards, tokens = generator.generate_flashcards(text_input=content, context=context, user=user, deck=deck)

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
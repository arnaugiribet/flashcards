from django.shortcuts import render
from django.conf import settings
import os

# Import your existing backend classes
from llm_client import LLMClient
from flashcard_generator import FlashcardGenerator
from flashcard_class import Flashcard

from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to the Flashcards app!")
    
def generate_flashcards(request):
    # Example of using your generator
    api_key = os.getenv('OPENAI_API_KEY')  # Use environment variables!
    llm_client = LLMClient(api_key)
    generator = FlashcardGenerator(llm_client)

    # You'll want to add form handling here to get text input
    text_input = "Example study material..."
    flashcards = generator.generate_flashcards(text_input)

    return render(request, 'flashcards/generate.html', {
        'flashcards': flashcards
    })
from django.shortcuts import render
from django.conf import settings
import os
from flashcards.models import Flashcard

# Import your existing backend classes
from llm_client import LLMClient

from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to the Flashcards app!")

def flashcard_list(request):
    """
    Retrieve all flashcards and render them in a template.
    Can be extended to support filtering, pagination, etc.
    """
    flashcards = Flashcard.objects.all()
    return render(request, 'flashcards/list_all_flashcards.html', {
        'flashcards': flashcards
    })

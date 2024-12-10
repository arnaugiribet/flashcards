from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
import os
from flashcards.models import Flashcard

# Import your existing backend classes
from llm_client import LLMClient

from django.http import HttpResponse

def home(request):
    return render(request, "home.html")

def flashcard_list(request):
    """
    Retrieve all flashcards and render them in a template.
    Can be extended to support filtering, pagination, etc.
    """
    flashcards = Flashcard.objects.all()
    return render(request, 'flashcards/list_all_flashcards.html', {
        'flashcards': flashcards
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login page after successful signup
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

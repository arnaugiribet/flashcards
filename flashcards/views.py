from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from flashcards.models import Flashcard
from django.utils.translation import activate

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
            # Check if username already exists
            username = form.cleaned_data.get('username')
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'A user with that username already exists.')
                return render(request, 'registration/signup.html', {'form': form})
            
            # Save the new user
            user = form.save()
            login(request, user)

            # Set the language to english
            activate('en')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})
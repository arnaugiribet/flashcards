from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
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

def account_settings(request):
    return HttpResponse(status=204)
    
def add_flashcards(request):
    return HttpResponse(status=204)
    
@login_required
def study(request):
    """
    Study view that shows cards due today for the logged-in user.
    
    The view supports:
    - Showing only cards due today
    - Filtering cards by the logged-in user
    - Handling card review interactions
    """
    # Get cards due today for the current user
    due_cards = Flashcard.objects.filter(
        user=request.user, 
        due__lte=timezone.now().date()
    ).order_by('due')
    
    # If no cards are due, render a specific template
    if not due_cards.exists():
        return render(request, 'study/no_cards_due.html')
    
    # Prepare the first card for study
    current_card = due_cards.first()
    
    return render(request, 'study/study_mode.html', {
        'card': current_card,
        'total_due_cards': due_cards.count()
    })

@login_required
def review_card(request):
    """
    Handle card review interactions.
    
    Expects a POST request with:
    - card_id: ID of the card being reviewed
    - result: 'correct' or 'incorrect'
    """
    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        result = request.POST.get('result')
        
        try:
            card = Flashcard.objects.get(id=card_id, user=request.user)
            
            # Logic for updating card's due date based on review result
            if result == 'correct':
                # Increase interval between reviews
                card.due = timezone.now().date() + timedelta(days=1)  # Simple implementation
            else:
                # Reset to shorter interval if card is marked incorrect
                card.due = timezone.now().date()
            
            card.save()
            
            # Get the next due card
            next_card = Flashcard.objects.filter(
                user=request.user, 
                due__lte=timezone.now().date()
            ).exclude(id=card_id).order_by('due').first()
            
            if next_card:
                return JsonResponse({
                    'status': 'success', 
                    'next_card_id': str(next_card.id),
                    'question': next_card.question,
                    'answer': next_card.answer
                })
            else:
                return JsonResponse({
                    'status': 'completed',
                    'message': 'No more cards to review'
                })
        
        except Flashcard.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Card not found'}, status=404)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    
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
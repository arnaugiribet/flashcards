from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from flashcards.models import Flashcard, Deck
from django.utils.translation import activate
import json
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Prefetch

# Import your existing backend classes
from llm_client import LLMClient

from django.http import HttpResponse

def home(request):
    if request.user.is_authenticated:
        return redirect('user_decks')  # Redirect logged-in users to their decks
    return render(request, "home.html")  # Default home page for guests

def account_settings(request):
    return HttpResponse(status=204)
    
def add_flashcards(request):
    return HttpResponse(status=204)

@login_required
def user_decks(request):
    today = timezone.now().date()
    
    user_decks = (
        Deck.objects.filter(user=request.user)
        .annotate(
            due_cards_today=Count(
                'flashcards', 
                filter=Q(flashcards__due=today)
            )
        )
        .select_related('parent_deck')
        .prefetch_related(
            Prefetch(
                'subdeck',
                queryset=Deck.objects.annotate(
                    due_cards_today=Count(
                        'flashcards',
                        filter=Q(flashcards__due=today)
                    )
                )
            )
        )
    )

    return render(request, 'home_decks/user_decks.html', {'decks': user_decks})

@login_required
def study(request):
    """
    Study view that shows cards due today for the logged-in user from a specific deck and its children.
    """
    deck_id = request.GET.get('deck_id')
    
    if not deck_id:
        return redirect('user_decks')
    
    # Get the deck and all its children
    def get_all_child_deck_ids(deck_id):
        deck_ids = [deck_id]
        children = Deck.objects.filter(parent_deck_id=deck_id)
        for child in children:
            deck_ids.extend(get_all_child_deck_ids(child.id))
        return deck_ids
    
    deck_ids = get_all_child_deck_ids(deck_id)
    
    # Get cards due today for the current user from the selected deck and its children
    due_cards = Flashcard.objects.filter(
        user=request.user,
        deck_id__in=deck_ids,
        due__lte=timezone.now().date()
    ).order_by('due')
    
    # If no cards are due, render a specific template
    if not due_cards.exists():
        return render(request, 'study/no_cards_due.html')
    
    # Prepare the first card for study
    current_card = due_cards.first()
    
    return render(request, 'study/study_mode.html', {
        'card': current_card,
        'total_due_cards': due_cards.count(),
        'deck_id': deck_id  # Pass the deck_id to maintain context
    })

@login_required
@require_http_methods(["POST"])
def review_card(request):
    """
    Handle card review with optimized performance and detailed interval calculation.
    """
    try:
        # Parse JSON data
        data = json.loads(request.body)
        card_id = data.get('card_id')
        result = data.get('result')
        
        # Validate input
        if not card_id or result not in ['again', 'hard', 'good', 'easy']:
            return JsonResponse({'status': 'error', 'message': 'Invalid input'}, status=400)
        
        # Fetch card with minimal fields
        card = Flashcard.objects.only('id', 'user', 'due').get(
            id=card_id, 
            user=request.user
        )
        
        # Calculate new due date based on review result
        current_date = timezone.now().date()
        
        # Sophisticated interval calculation
        interval_map = {
            'again': timedelta(seconds=600),   # Reset to shortest interval
            'hard': timedelta(days=1),    # Slightly longer interval
            'good': timedelta(days=3),    # Moderate interval
            'easy': timedelta(days=5)     # Longest interval
        }
        
        # Update card's due date
        card.due = current_date + interval_map[result]
        card.save(update_fields=['due'])
        
        # Efficiently get remaining due cards
        due_cards = Flashcard.objects.filter(
            user=request.user, 
            due__lte=current_date
        ).order_by('due')
        
        # If no more cards due
        if not due_cards.exists():
            return JsonResponse({
                'status': 'completed',
                'message': 'No more cards to review'
            })
        
        # Get next card
        next_card = due_cards.first()
        
        return JsonResponse({
            'status': 'success', 
            'next_card_id': str(next_card.id),
            'question': next_card.question,
            'answer': next_card.answer,
            'remaining_cards': due_cards.count()
        })
    
    except Flashcard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Unexpected error in review_card: {e}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)
    
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
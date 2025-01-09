from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from flashcards.models import Flashcard, Deck
from django.utils.translation import activate
import json
from .services import generate_flashcards
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Prefetch
import random
import logging

# Import your existing backend classes
from llm_client import LLMClient

from django.http import HttpResponse

logger = logging.getLogger(__name__)

def home(request):
    if request.user.is_authenticated:
        return redirect('user_decks')  # Redirect logged-in users to their decks
    return render(request, "home.html")  # Default home page for guests

def account_settings(request):
    return HttpResponse(status=204)

@login_required
def manage_cards(request):
    user_flashcards = Flashcard.objects.filter(user=request.user).select_related('deck')
    user_decks = Deck.objects.filter(user=request.user)
    ordered_decks = Deck.order_decks(user_decks)

    # Handle sorting
    sort_by = request.GET.get('sort_by', 'due')  # Default sort by 'due'
    if sort_by in ['question', 'answer', 'deck__name', 'due', 'creation_date']:
        user_flashcards = user_flashcards.order_by(sort_by)

    context = {
        'cards': user_flashcards,
        'decks': ordered_decks,
    }
    return render(request, "manage_cards/manage_cards.html", context)

@login_required
def update_card_field(request, card_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')

        try:
            card = Flashcard.objects.get(id=card_id)
            if field == 'deck':
                deck = Deck.objects.get(id=value)
                card.deck = deck
            else:
                setattr(card, field, value)
            card.save()
            return JsonResponse({'success': True})
        except Flashcard.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Card not found.'})
        except Deck.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Deck not found.'})

    return JsonResponse({'success': False, 'message': 'Invalid method.'})

@login_required
def delete_card(request, card_id):
    if request.method == 'POST':
        try:
            card = Flashcard.objects.get(id=card_id)  # Attempt to retrieve the card
            card.delete()  # Delete the card
            return JsonResponse({'success': True})
        except Flashcard.DoesNotExist:
            raise Http404("Card not found")  # Raise a 404 if the card doesn't exist
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required
def user_decks(request):

    def set_indentation_level(deck, all_decks, level=0):
        deck.indentation_level = level
        # Recursively set levels for child decks
        child_decks = [d for d in all_decks if d.parent_deck == deck]
        for child_deck in child_decks:
            set_indentation_level(child_deck, all_decks, level + 1)

    def aggregate_due_count(decks):
        """
        Aggregates the `due_cards_today` count from child decks to their parent decks.
        """
        # Sort decks by descending indentation level to start from the bottom
        decks.sort(key=lambda deck: deck.indentation_level, reverse=True)

        # A mapping of deck IDs for quick lookup
        deck_map = {deck.id: deck for deck in decks}

        for deck in decks:
            if deck.parent_deck:
                parent_deck = deck_map.get(deck.parent_deck.id)
                if parent_deck:
                    parent_deck.due_cards_today += deck.due_cards_today

        return decks

    today = timezone.now().date()

    # Fetch the decks and convert the queryset to a list
    decks_queryset = Deck.objects.filter(user=request.user).annotate(
        flashcards_count=Count('flashcards')
    ).select_related('parent_deck')

    # Convert queryset to a list
    decks = list(decks_queryset)

    # Process decks and add indentation levels
    root_decks = [deck for deck in decks if deck.parent_deck is None]
    for root_deck in root_decks:
        set_indentation_level(root_deck, decks, 0)

    # Add due cards today count
    for deck in decks:
        deck.due_cards_today = deck.flashcards.filter(due__lte=today).count()

    # Order the decks hierarchically using the class method
    ordered_decks = Deck.order_decks(decks)

    # Aggregate due cards count from children to parents
    decks = aggregate_due_count(decks)

    # Pass the list to the template
    return render(request, 'home_decks/user_decks.html', {'decks': ordered_decks})

@login_required
def no_cards_due(request):
    """
    View that shows the message when there are no cards due for review.
    """
    return render(request, 'study/no_cards_due.html')

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

    try:
        # Get predicted review intervals for each quality level
        intervals, ease_factors = current_card.get_next_intervals_ease_factors()
    except Exception as e:
        logger.error(f"Error calculating intervals for card ID {current_card.id}: {e}")
        # Optionally, redirect to an error page or provide a fallback
        return render(request, 'study/error.html', {
            'error_message': 'There was an error calculating the review intervals. Please try again later.'
        })

    return render(request, 'study/study_mode.html', {
        'card': current_card,
        'total_due_cards': due_cards.count(),
        'deck_id': deck_id,
        'intervals': intervals
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
        deck_id = data.get('deck_id')  # Get the deck_id from the request
        
        # Validate input
        if not card_id or result not in ['again', 'hard', 'good', 'easy'] or not deck_id:
            return JsonResponse({'status': 'error', 'message': 'Invalid input'}, status=400)
        
        # Fetch the deck and all its child decks
        def get_all_child_deck_ids(deck_id):
            deck_ids = [deck_id]
            children = Deck.objects.filter(parent_deck_id=deck_id)
            for child in children:
                deck_ids.extend(get_all_child_deck_ids(child.id))
            return deck_ids
        
        # Get all deck IDs that belong to the parent deck and its children
        deck_ids = get_all_child_deck_ids(deck_id)
        
        # Fetch the flashcard for review based on the card_id and deck_id (and its children)
        card = Flashcard.objects.only('id', 'user', 'deck_id', 'question', 'answer', 'due').get(
            id=card_id,
            user=request.user,
            deck_id__in=deck_ids  # Make sure the card belongs to the specified deck or its children
        )
        
        # Update the due date based on the review result
        try:
            card.update_review(result)
        except ValueError as e:
            logger.error(f"Error in review_card: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        # Get current date
        current_date = timezone.now().date()
        
        # Efficiently get remaining due cards for the current deck and its children
        due_cards = Flashcard.objects.filter(
            user=request.user,
            deck_id__in=deck_ids,  # Filter by deck_id and its children
            due__lte=current_date
        ).order_by('due')

        # If there is more than one card in the due cards list, handle the "again" card
        if due_cards.count() > 1 and card in due_cards:
            # Convert to a list to allow manipulation
            due_cards = list(due_cards)
            # Remove the reviewed card
            logger.debug(f"\nremoving card {card}")
            due_cards.remove(card)
            # Add it back to the end of the list
            due_cards.append(card)
            # Shuffle the cards from position 2 onward (to ensure the "again" card isn't the first)
            random.shuffle(due_cards[1:])
            logger.debug(f"\nthese are the due cards: {due_cards}")

        # If there are no more cards to review
        if not due_cards:
            return JsonResponse({
                'status': 'completed',
                'message': 'No more cards to review'
            })
        
        # Get the next due card (first in the list)
        next_card = due_cards[0]  # The first card now is not the "again" card
    
        logger.debug(f"\nNext card should be: {next_card}")

        # Return the response
        return JsonResponse({
            'status': 'success', 
            'next_card_id': str(next_card.id),
            'question': next_card.question,
            'answer': next_card.answer,
            'remaining_cards': len(due_cards)
        })
    
    except Flashcard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Unexpected error in review_card: {e}")
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)

@login_required
@require_http_methods(["POST"])
def process_file_and_context(request):
    """
    View to handle file and context submission for creating flashcards.
    """
    file = request.FILES.get('file')
    context = request.POST.get('context', '')

    try:
        # Call the service function
        flashcards = generate_flashcards(file, context)
        flashcards_data = [
            {"question": fc.question, "answer": fc.answer} for fc in flashcards
        ]
        return JsonResponse({"success": True, "flashcards": flashcards_data})
    except ValueError as ve:
        return JsonResponse({"success": False, "error": str(ve)}, status=400)
    except RuntimeError as re:
        return JsonResponse({"success": False, "error": "Internal error"}, status=500)

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

@login_required
def create_manually(request):
    """
    View to handle manual creation of flashcards.
    """
    if request.method == "POST":
        deck_id = request.POST.get('deck_id')
        question = request.POST.get('question')
        answer = request.POST.get('answer')

        # Ensure all required fields are present
        if not (deck_id and question and answer):
            return render(request, 'add_cards/create_manually.html', {'error': 'All fields are required.'})

        try:
            # Validate and create flashcard
            deck = Deck.objects.get(id=deck_id, user=request.user)
            Flashcard.objects.create(deck=deck, question=question, answer=answer, user=request.user)
            # Add success message
            messages.success(request, 'Card successfully created.')
            # Return to the same create manually page
            return redirect('create_manually')
        except Deck.DoesNotExist:
            return render(request, 'add_cards/create_manually.html', {'error': 'Invalid deck selected.'})

    # Fetch user's decks to display in the form
    decks = Deck.objects.filter(user=request.user)
    return render(request, 'add_cards/create_manually.html', {'decks': decks})

@login_required
def create_automatically(request):
    """
    View for automatic flashcard creation with the ability to save a single flashcard.
    """
    if request.method == "POST":
        # Extract data from POST request
        deck_id = request.POST.get('deck_id')
        question = request.POST.get('question')
        answer = request.POST.get('answer')
        # Ensure all required fields are present
        if not (deck_id and question and answer):
            return JsonResponse({'success': False, 'error': 'All fields (deck, question, answer) are required.'}, status=400)
        try:
            # Validate the deck and create the flashcard
            deck = Deck.objects.get(id=deck_id, user=request.user)
            Flashcard.objects.create(deck=deck, question=question, answer=answer, user=request.user)
            return JsonResponse({'success': True, 'message': 'Flashcard saved successfully.'})
        except Deck.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid deck selected.'}, status=400)
    # Handle GET request to fetch decks for the template
    decks_queryset = Deck.objects.filter(user=request.user)
    decks = list(decks_queryset)
    ordered_decks = Deck.order_decks(decks)
    return render(request, 'add_cards/create_automatically.html', {
        'ordered_decks': ordered_decks
    })


@login_required
def create_deck(request):
    if request.method == "POST":
        deck_name = request.POST.get('deck_name')
        parent_deck_id = request.POST.get('parent_deck')

        # Ensure that the deck name is provided
        if not deck_name:
            return JsonResponse({"success": False, "message": "Deck name is required."})

        parent_deck = None
        if parent_deck_id:
            try:
                parent_deck = Deck.objects.get(id=parent_deck_id, user=request.user)
            except Deck.DoesNotExist:
                return JsonResponse({"success": False, "message": "Invalid parent deck."})

        # Create the new deck
        new_deck = Deck.objects.create(
            name=deck_name,
            user=request.user,
            parent_deck=parent_deck,
        )

        return JsonResponse({"success": True, "message": "Deck created successfully."})

    return JsonResponse({"success": False, "message": "Invalid request method."})
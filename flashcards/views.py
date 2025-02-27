from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from flashcards.models import Flashcard, Deck, FailedFeedback, UserDocument
from flashcards.forms import DocumentUploadForm
from django.utils.translation import activate
import json
from .services import generate_flashcards
from .forms import CustomUserCreationForm
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Prefetch
import random
import logging
import io
import os
from src.backend.usage_limits import InsufficientTokensError
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.urls import reverse
from botocore.exceptions import ClientError
from llm_client import LLMClient
from django.http import HttpResponse
from boto3 import client as boto3_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def home(request):
    logger.debug("Redirecting home...")
    if request.user.is_authenticated:
        return redirect('user_decks')  # Redirect logged-in users to their decks
    return render(request, "home.html")  # Default home page for guests

@login_required
def account_settings(request):
    if request.method == "POST":
        # Handle username update
        new_username = request.POST.get("username")
        if new_username:
            request.user.username = new_username
            request.user.save()
            messages.success(request, "Your username has been updated.")
            return redirect("account_settings")
    return render(request, "account/account_settings.html")

@login_required
def change_username(request):
    if request.method == 'POST':
        # Block username change for test_user
        if request.user.username == "test_user":
            messages.error(request, 'This username cannot be changed.', extra_tags='username')
        else:
            new_username = request.POST.get('new_username')
            if new_username:
                if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                    messages.error(request, 'Username is already taken.', extra_tags='username')
                else:
                    request.user.username = new_username
                    request.user.save()
                    messages.success(request, 'Username updated successfully.', extra_tags='username')
    return render(request, 'account/change_username.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        # Block password change for 'test_user'
        if request.user.username == "test_user":
            messages.error(request, 'This account cannot be deleted.', extra_tags='password')
            form = PasswordChangeForm(request.user, request.POST)
            return render(request, 'account/change_password.html', {'form': form})
        else:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password was successfully updated!', extra_tags='password')
            else:
                pass
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'account/change_password.html', {'form': form})
    
# views.py
@login_required
def delete_account(request):
    if request.method == 'POST':
        # Block deletion for 'test_user'
        if request.user.username == "test_user":
            messages.error(request, "This account cannot be deleted.", extra_tags='delete_account')
            return render(request, 'account/account_settings.html', {'show_delete_modal': True})
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)
        if user is not None:
            request.user.delete()
            messages.success(request, "Your account has been deleted.")
            return redirect('home')
        else:
            messages.error(request, "The password you entered is incorrect.", extra_tags='delete_account')
            return render(request, 'account/account_settings.html', {'show_delete_modal': True})
    return redirect('account_settings')

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
def delete_deck(request, deck_id):
    """
    View to delete a deck and all its nested sub-decks along with their flashcards.
    """
    logger.debug("Deleting deck...")
    if request.method == 'POST':
        try:
            # Attempt to retrieve the deck
            deck = Deck.objects.get(id=deck_id, user=request.user)
            
            # Get all descendant decks and include the current deck
            all_decks = deck.get_descendants()
            all_decks.append(deck)

            # Collect all flashcards associated with these decks
            flashcards_to_delete = Flashcard.objects.filter(deck__in=all_decks)

            # Delete all collected flashcards and decks
            flashcards_to_delete.delete()
            for d in all_decks:
                d.delete()

            return JsonResponse({'success': True})

        except Deck.DoesNotExist:
            raise Http404("Deck not found")  # Raise a 404 if the deck doesn't exist

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required
def user_documents(request):
    user_documents = UserDocument.objects.filter(user=request.user)
    return render(request, 'documents/user_documents.html', {'user_documents': user_documents})

@login_required
def get_document_url(request, document_id):
    logger.debug(f"Received request to generate presigned URL for document_id: {document_id}")
    try:
        document = get_object_or_404(UserDocument, id=document_id, user=request.user)
        logger.debug(f"Document found: {document.id}, S3 Key: {document.s3_key}")
    except Exception as e:
        logger.error(f"Document lookup failed: {e}")
        return JsonResponse({'error': 'Document not found'}, status=404)
    
    s3_client = boto3_client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    # Generate a presigned URL
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,  # Use the bucket from settings
                'Key': document.s3_key  # The S3 object key stored in the model
            },
            ExpiresIn=3600  # Link expires in 1 hour
        )
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        return JsonResponse({'error': str(e)}, status=500)
        
    logger.debug(f"Presigned URL generated successfully: {presigned_url}")
    return JsonResponse({'url': presigned_url})

@login_required
def get_document_flashcards(request, document_id):
    """
    API endpoint that returns all flashcards associated with a specific document.
    Returns flashcard data including page numbers and bounding boxes.
    """
    try:
        # Ensure the document exists and belongs to the current user
        document = UserDocument.objects.get(id=document_id, user=request.user)
        
        # Get all flashcards for this document
        flashcards = Flashcard.objects.filter(document=document)
        
        # Format the response data
        flashcard_data = []
        for card in flashcards:
            if card.page_number is not None and card.bounding_box is not None:
                flashcard_data.append({
                    'id': str(card.id),
                    'page': card.page_number,
                    'bbox': card.bounding_box,
                })
        
        return JsonResponse({'flashcards': flashcard_data})
    
    except UserDocument.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)

@login_required
def upload_document(request):
    logger.debug(f"Upload function called")
    if request.method == 'POST':
        logger.info(f"POST request received for file upload to s3")
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            logger.debug(f"Form is valid request received for file upload to s3")
            document = form.cleaned_data['document']
            file_type = document.name.split('.')[-1].lower()
            name = document.name
            
            # Create the UserDocument instance but don't save yet
            user_document = form.save(commit=False)
            user_document.user = request.user
            user_document.file_type = file_type
            user_document.name = name
            
            logger.debug(f"Generating S3 key")
            # Generate S3 key
            s3_key = f'documents/{request.user.id}/{user_document.id}.{file_type}'
            user_document.s3_key = s3_key
            
            # Upload to S3
            try:
                logger.debug(f"Trying to upload to S3")
                s3_client = boto3_client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                
                logger.debug(f"S3 client created, uploading...")
                s3_client.upload_fileobj(
                    document,
                    settings.AWS_STORAGE_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ContentType': document.content_type,
                        'ACL': 'private'
                    }
                )
                # Save the document record
                logger.debug(f"File uploaded. Saving user_document")
                user_document.save()

                logger.debug(f"user_document saved. Redirecting...")
                return redirect('user_documents')  # Redirect to your documents list view
                
            except ClientError as e:
                form.add_error(None, 'Failed to upload document. Please try again.')
        else:
            logger.error(f"Form errors: {form.errors}")  # <-- Debugging
    else:
        form = DocumentUploadForm()
    
    return render(request, 'documents/user_documents.html', {'form': form})

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
    View to handle file/text input and context submission for creating flashcards.
    """
    logger.debug("Processing file and context...")

    context = request.POST.get('context', '')
    input_type = request.POST.get('input_type')
    user = request.user
    
    try:
        if input_type == 'file':
            file = request.FILES.get('file')
            if not file:
                raise ValueError("No file uploaded")
            # Extract the file extension
            _, file_extension = os.path.splitext(file.name)
            content_format = file_extension.lower()
            content = file
            
        else:  # input_type == 'text'
            text_input = request.POST.get('input_text')
            if not text_input:
                raise ValueError("No text provided")
            # Convert text input to a file-like object to maintain compatibility
            content = io.StringIO(text_input)
            content_format = "string"

        logger.debug(f"File is of type {content_format}")


        # Call the service function - it can now handle either a file or StringIO object
        flashcards = generate_flashcards(content, content_format, context, user)
        flashcards_data = [
            {"question": fc.question, "answer": fc.answer} for fc in flashcards
        ]
        return JsonResponse({"success": True, "flashcards": flashcards_data})

    except InsufficientTokensError as e:
        # Handle the specific InsufficientTokensError
        logger.error(f"Insufficient tokens: {str(e)}", exc_info=True)
        
        last_usage_timestamps = e.most_recent_usage_timestamp
        time_in_4_hours = last_usage_timestamps + timedelta(hours=4) + timedelta(minutes=1)
        formatted_time = time_in_4_hours.strftime('%I:%M %p')
        if formatted_time.startswith('0'): # trick to avoid the preceding 0 
            formatted_time = formatted_time[1:]

        return JsonResponse({
            "success": False, 
            "error": f"You are out of tokens until {formatted_time}. Unlimited Pro version coming soon."
        }, status=200)

    except Exception as e:
        # Log the exception for debugging purposes
        logger.error(f"An error occurred when generating cards: {str(e)}", exc_info=True)

        # Check if the format is not supported
        if isinstance(e, ValueError) and "Unsupported content format" in str(e):
            return JsonResponse({
                "success": False, 
                "error": "Supported formats are txt, docx and pdf."
            }, status=200)
        
        # Check if the text was too long
        if isinstance(e, ValueError) and "exceeds maximum allowed length" in str(e):
            return JsonResponse({
                "success": False, 
                "error": "The input text is too long. Please reduce it to 30,000 characters or less. Unlimited Pro version coming soon."
            }, status=200)

        # Return an error message to the user
        return JsonResponse({"success": False, "error": "There was an error while generating your cards. Please try again."}, status=200)

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Create user as inactive
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            logger.debug(f"starting registration process for {user} with email {user.email}")

            # Generate verification token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            current_site = get_current_site(request)
            subject = "Activate Your Account"
            context = {
                'user': user,
                'domain': current_site.domain,
                'uid': uid,
                'token': token,
            }
            text_content = render_to_string('registration/activation_email.txt', context)
            html_content = render_to_string('registration/activation_email.html', context)
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            logger.debug(f"activation email was sent")
            return render(request, 'registration/email_sent.html')

    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

def resend_activation_email(request, user_id):
    """View to handle resending verification email"""
    try:
        user = User.objects.get(id=user_id, is_active=False)
        
        # Generate new verification token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Resend verification email
        current_site = get_current_site(request)
        subject = "Activate Your Account"
        context = {
            'user': user,
            'domain': current_site.domain,
            'uid': uid,
            'token': token,
        }
        text_content = render_to_string('registration/activation_email.txt', context)
        html_content = render_to_string('registration/activation_email.html', context)
        
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        logger.debug(f"new activation email was sent")

    except User.DoesNotExist:
        messages.error(request, 'User does not exist.')
    
    return render(request, 'registration/email_sent.html')

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)  # Log the user in after activation
        return render(request, 'registration/activation_success.html')  # Show success page
    else:
        return render(request, 'registration/activation_failed.html')  # Show failure page


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

def feedback_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        username = request.POST.get("username", "") # may be authenticated or not
        feedback_type = request.POST.get("feedbackType")
        message = request.POST.get("message")

        try:
            # Send the feedback email
            send_mail(
                subject=f"Feedback from {name}",
                message=f"Name: {name}\nEmail: {email}\nUsername: {username}\nType: {feedback_type.capitalize()}\n\n{message}",
                from_email=settings.EMAIL_HOST_USER,  # Use the user's email for the "from" field
                recipient_list=[settings.EMAIL_HOST_USER],  # Send to your admin email
                fail_silently=False,
            )
            logger.debug(f"Feedback email successfully sent")

        except Exception as e:
            # if the email fails, we store the feedback in the db
            logger.error(f"Error sending feedback email: {e}")
            FailedFeedback.objects.create(
                name=name,
                username=username,
                email=email,
                feedback_type=feedback_type,
                message=message,
            )
            logger.debug(f"Feedback stored in FailedFeedback table")
        
        return JsonResponse({'status': 'success'})

    return render(request, 'feedback.html')
from django.contrib import admin
from flashcards.models import Flashcard, Deck
from .models import UserPlan

# Register your models here.

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('question', 'creation_date', 'due')
    search_fields = ('question', 'answer')

@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'user', 'parent_deck')
    search_fields = ('name', 'description')

@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_type', 'total_tokens_allowed')  # Fields to display in the list view
    list_filter = ('plan_type',)  # Optionally, add filters on the plan type
    search_fields = ('user__username',)  # Allows searching by user username
    list_editable = ('plan_type', 'total_tokens_allowed')  # These fields can now be edited in the list view
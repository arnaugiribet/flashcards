from django.contrib import admin
from flashcards.models import Flashcard, Deck

# Register your models here.

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('question', 'creation_date', 'due')
    search_fields = ('question', 'answer')

# Register the Deck model
@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'user', 'parent_deck')
    search_fields = ('name', 'description')
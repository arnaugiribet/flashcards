from django.contrib import admin
from flashcards.models import Flashcard

# Register your models here.

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('question', 'creation_date', 'due')
    search_fields = ('question', 'answer')
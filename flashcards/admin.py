from django.contrib import admin
from flashcards.models import Flashcard, Deck, FailedFeedback
from .models import UserPlan, TokenUsage

# Register your models here.
@admin.register(FailedFeedback)
class FailedFeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'feedback_type', 'created_at')
    search_fields = ('name', 'email', 'feedback_type')
    def has_change_permission(self, request, obj=None):
        return False
    def has_add_permission(self, request):
        return False

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

@admin.register(TokenUsage)
class TokenUsageAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'tokens_used', 'timestamp')
    list_filter = ['timestamp']
    search_fields = ['user__username']
    date_hierarchy = 'timestamp'
    
    # Values not editable
    readonly_fields = ('user', 'tokens_used', 'timestamp')

    @admin.display(description='User')  # This is the modern way to set column header
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'User'  # Column header in admin

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
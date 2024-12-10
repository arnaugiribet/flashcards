from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Root path (e.g., '/')
    path('flashcards/', views.flashcard_list, name='flashcard_list'),
    path('signup/', views.signup, name='signup'),
]

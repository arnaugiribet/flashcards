from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Root path (e.g., '/')
    path('generate/', views.generate_flashcards, name='generate_flashcards'),  # '/generate/' path
]

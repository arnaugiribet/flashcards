import os
import sys

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import django

# Set the DJANGO_SETTINGS_MODULE to your settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flashcard_project.settings')

# Initialize Django
django.setup()

from flashcards.models import Flashcard
from datetime import date

# Create individual cards
card1 = Flashcard(
    question="What is Django?", 
    answer="A high-level Python web framework that encourages rapid development and clean, pragmatic design."
)
card1.save()

card2 = Flashcard(
    question="What does ORM stand for?", 
    answer="Object-Relational Mapping, which allows you to interact with databases using Python objects instead of SQL."
)
card2.save()
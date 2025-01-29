# setup
# Add the project root to the Python path
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from io import StringIO
import csv
from src.backend.flashcard_class import Flashcard

response = '"¿Cuál es el ejercicio 1 a realizar?",\n"Bajar éste trailer y musicalizar hasta el 0:40 usando músicas existentes y una parte de música propia, manteniendo el tempo de alguna de las músicas existentes y marcando narrativamente los momentos importantes del tráiler."\n"¿Dónde se debe bajar el trailer para el ejercicio 1?",\n"https://www.youtube.com/watch?v=6ydoiA4gXwo"\n"¿Qué se debe presentar como resultado del ejercicio 1?",\n"Un .mov o similar del tráiler con música, presentado solo con música, marcando narrativamente los momentos importantes."'
# Remove leading/trailing whitespace
response = response.strip()  

# Ensure the response has a trailing newline
if not response.endswith('\n'):
    response += '\n'
print(f"string from which generate we must flashcards:\n{repr(response)}")
# Use StringIO to treat the response as a file-like object for the CSV reader
response_io = StringIO(response)
reader = csv.reader(response_io, quotechar='"', escapechar='\\')

flashcards = []
# Iterate over each row in the CSV response
for idx, row in enumerate(reader):
    try:
        # Attempt to unpack the row into question and answer
        question, answer = row
        len_question, len_answer = len(question), len(answer)
        if len_question==0 or len_answer==0:
            raise ValueError(f"Question length: {len_question}. Answer length: {len_answer}")
        # Create and append the flashcard
        card_i = Flashcard(question.strip(), answer.strip())
        flashcards.append(card_i)
    except ValueError as ve:
        # Log the error with details about the problematic row
        print(f"Row {idx+1} is invalid or malformed: {row}. Error: {ve}")
        # Skip the row and continue
        continue

print("flashcards are:")
for fc in flashcards:
    print(fc.short_str())
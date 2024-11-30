import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from src.backend.llm_client import LLMClient
from src.backend.flashcard_generator import FlashcardGenerator

# Streamlit App
def main():
    st.title("Flashcard Generator")
    st.write("Generate flashcards from your text using an LLM.")

    # Input Section
    st.subheader("Input Text")
    text_input = st.text_area("Enter your text here:")

    # LLM API Key Section
    st.subheader("LLM API Configuration")
    api_key = st.text_input("Enter your LLM API Key:", type="password")

    # Generate Flashcards Button
    if st.button("Generate Flashcards"):
        if not text_input.strip():
            st.error("Please enter some text.")
        elif not api_key.strip():
            st.error("Please enter an API key.")
        else:
            try:
                # Initialize LLM Client and Flashcard Generator
                llm_client = LLMClient(api_key=api_key)
                flashcard_generator = FlashcardGenerator(llm_client)

                # Generate Flashcards
                flashcards = flashcard_generator.generate_flashcards(text_input)
                if flashcards:
                    for flashcard in flashcards:
                        st.success(f"Q: {flashcard.question}\nA: {flashcard.answer}")

                else:
                    st.warning("No flashcards were generated. Try revising your input.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import streamlit as st
from src.backend.llm_client import LLMClient
from src.backend.flashcard_generator import FlashcardGenerator
from typing import List, Optional

# Streamlit App
def main():
    st.title("Flashcard Generator")
    st.write("Generate flashcards from your text using an LLM.")

    # Initialize session state variables if they don't exist
    if 'generated_flashcards' not in st.session_state:
        st.session_state.generated_flashcards = None
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'original_text' not in st.session_state:
        st.session_state.original_text = ""

    # Input Section
    st.subheader("Input Text")
    text_input = st.text_area("Enter your text here:")

    # LLM API Key Section
    st.subheader("LLM API Configuration")
    api_key = st.text_input(
        "Enter your LLM API Key:", 
        type="password", 
        value=st.session_state.api_key
    )
    st.session_state.api_key = api_key

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
                    st.session_state.generated_flashcards = flashcards
                    st.session_state.original_text = text_input
                    
                    
                else:
                    st.warning("No flashcards were generated. Try revising your input.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # Flashcard Handling Section (only show if flashcards have been generated)
    if st.session_state.generated_flashcards:
        # Display Generated Flashcards
        st.subheader("Generated Flashcards")
        for i, flashcard in enumerate(st.session_state.generated_flashcards, 1):
            st.success(f"Flashcard {i}\nQ: {flashcard.question}\nA: {flashcard.answer}")

        # Radio button for Accept or Feedback
        action_choice = st.radio(
            "What would you like to do?", 
            ["Accept Flashcards", "Provide Feedback"]
        )
        
        if action_choice == "Accept Flashcards":
            if st.button("Confirm Accept"):
                st.success("Flashcards accepted!")
                # Here you might want to add functionality 
                # like saving or further processing
        
        elif action_choice == "Provide Feedback":
            regenerate_feedback = st.text_area("Provide detailed feedback for regeneration:")
            
            if st.button("Regenerate with Feedback"):
                if not regenerate_feedback.strip():
                    st.error("Please provide feedback for regeneration.")
                else:
                    try:
                        # Initialize LLM Client and Flashcard Generator
                        llm_client = LLMClient(api_key=st.session_state.api_key)
                        flashcard_generator = FlashcardGenerator(llm_client)

                        # Regenerate with feedback and previous flashcards
                        regenerated_flashcards = flashcard_generator.generate_flashcards(
                            st.session_state.original_text, 
                            proposed_flashcards=st.session_state.generated_flashcards, 
                            feedback=regenerate_feedback
                        )
                        
                        if regenerated_flashcards:
                            st.session_state.generated_flashcards = regenerated_flashcards
                            
                            # Display Regenerated Flashcards
                            st.subheader("Regenerated Flashcards")
                            for i, flashcard in enumerate(regenerated_flashcards, 1):
                                st.success(f"Flashcard {i}\nQ: {flashcard.question}\nA: {flashcard.answer}")
                        else:
                            st.warning("No flashcards were regenerated. Try different feedback.")
                    except Exception as e:
                        st.error(f"An error occurred during regeneration: {e}")

if __name__ == "__main__":
    main()
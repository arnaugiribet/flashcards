
// // Click handler for Manually button
document.getElementById('manualCardButton').addEventListener('click', () => {
    resetCreateState(); // Clear any stale state before showing
    navigateTo('createPanel');
});

// Back from manual creation to flashcards list
document.getElementById('backFromCreate').addEventListener('click', () => {
    exitSelectionMode();
    navigateTo('flashcardsContainer');
});

// Use the reusable function in your old button
document.getElementById('setTextPlacement').addEventListener('click', function() {
    toggleSelectionMode(this);
});

document.getElementById('saveNewFlashcard').addEventListener('click', () => {
    const question = document.getElementById('newQuestion').value.trim();
    const answer = document.getElementById('newAnswer').value.trim();

    if (!question || !answer) {
        // Show error message
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-yellow-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = 'Please fill in both question and answer fields';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 2000);
        return;
    }

    // Create the flashcard data to send to the server
    const flashcardData = {
        question: question,
        answer: answer,
        deck_id: currentDeckId,
        document_id: currentDocumentId
    };

    const saveButton = document.getElementById('saveNewFlashcard');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Creating...';
    saveButton.disabled = true;

    // Send the data to your server endpoint
    fetch('/create-flashcard/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(flashcardData)
    })
    .then(response => response.json())
    .then(data => {
        console.log("Flashcard created:", data);
        
        // Show success notification
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = 'Flashcard created successfully';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 2000);

        // Clear the input fields
        document.getElementById('newQuestion').value = '';
        document.getElementById('newAnswer').value = '';

        // Refresh the flashcards list
        fetchAndCreateHighlights(currentDocumentId);
        
    })
    .catch(error => {
        console.error("Error creating flashcard:", error);
        
        // Show error notification
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = `Error: ${error.message || 'Could not create flashcard'}`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    })
    .finally(() => {
        // Reset button state
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    });
});

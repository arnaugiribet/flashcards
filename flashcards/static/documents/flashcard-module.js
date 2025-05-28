
// Fetch flashcards for the current document and call create highlights
async function fetchAndCreateHighlights(documentId) {
    const flashcardsContainer = document.getElementById("flashcardsContainer");
    const previousScrollTop = flashcardsContainer ? flashcardsContainer.scrollTop : 0;

    try {
        const response = await fetch(`/document/${documentId}/flashcards/`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch flashcards');
        }
        
        const data = await response.json();
        window.flashcards = data.flashcards;

        displayFlashcards(data.flashcards);
        createHighlights(window.flashcards, true); // creates all highlights on pdf startup
        setupPageRenderingListeners(); // will listen for rendering of pdf pages to trigger createHighlights again

        // After rendering flashcards, restore scroll position
        requestAnimationFrame(() => {
            if (flashcardsContainer) {
                flashcardsContainer.scrollTop = previousScrollTop;
            }
        });

    } catch (error) {
        console.error("Error fetching flashcards:", error);
    }
}


// Function to display flashcards in the right column
function displayFlashcards(flashcards) {
    const flashcardsContainer = document.getElementById("flashcardsContainer");
    flashcardsContainer.innerHTML = ""; // Clear existing flashcards
    
    // Filter into two groups
    const unacceptedFlashcards = flashcards.filter(card => card.accepted !== true);
    const acceptedFlashcards = flashcards.filter(card => card.accepted === true);
    
    // Display unaccepted flashcards section if there are any
    if (unacceptedFlashcards.length > 0) {
        // Add section header for unaccepted cards
        const unacceptedHeader = document.createElement("div");
        unacceptedHeader.classList.add("py-2", "px-4", "bg-yellow-50", "font-medium", "text-yellow-800", "border-b");
        unacceptedHeader.textContent = `Pending Acceptance (${unacceptedFlashcards.length})`;
        flashcardsContainer.appendChild(unacceptedHeader);
        
        // Add the unaccepted flashcards
        unacceptedFlashcards.forEach(flashcard => {
            addFlashcardElement(flashcard, flashcardsContainer, false);
        });
    }

    // Display accepted flashcards section if there are any
    if (acceptedFlashcards.length > 0) {
        console.log("Showing accepted flashcards")
        // Add section header for accepted cards
        const acceptedHeader = document.createElement("div");
        acceptedHeader.classList.add("py-2", "px-4", "bg-green-50", "font-medium", "text-green-800", "border-b");
        acceptedHeader.textContent = `My Flashcards`;
        flashcardsContainer.appendChild(acceptedHeader);
        
        // Add the accepted flashcards
        acceptedFlashcards.forEach(flashcard => {
            addFlashcardElement(flashcard, flashcardsContainer, true);
        });
    }

    // Helper function to create and add a flashcard element
    function addFlashcardElement(flashcard, container, isAccepted) {
        const flashcardElement = document.createElement("div");
        flashcardElement.classList.add("p-4", "border-b", "cursor-pointer", "hover:bg-gray-50");

        flashcardElement.style.borderRadius = "8px";
        flashcardElement.style.margin = "0 4px 4px 0";
        flashcardElement.style.position = "relative";
        
        // Style based on acceptance status
        if (!isAccepted) {
            flashcardElement.style.backgroundColor = "#fffbeb"; // Light yellow for unaccepted
        }

        flashcardElement.dataset.flashcardId = flashcard.id;
        
        // Check if flashcard has bounding box
        const hasBBox = flashcard.bbox && flashcard.bbox.length > 0;

        // Populate flashcard content
        let flashcardContent = `
            <div class="flex flex-col">
                ${(!isAccepted || (!hasBBox)) ? `
                    <div class="flex justify-end mb-2 h-5">
                        ${!isAccepted ? `
                            <div class="flex space-x-2">
                                ${!hasBBox ? `
                                    <div class="tooltip-container" title="No text selection associated with this flashcard">
                                        <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                        </svg>
                                    </div>
                                ` : ''}
                                <button class="discard-card-btn flex items-center text-xs bg-red-50 border border-red-300 rounded-md px-2 py-1 text-red-600 hover:bg-red-100 transition-colors">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                    Discard
                                </button>
                                <button class="accept-card-btn flex items-center text-xs bg-green-50 border border-green-300 rounded-md px-2 py-1 text-green-600 hover:bg-green-100 transition-colors">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                    Accept
                                </button>
                            </div>
                        ` : !hasBBox ? `
                            <div class="tooltip-container" title="No text selection associated with this flashcard">
                                <svg class="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                </svg>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                <div>
                    <p class="font-semibold">${flashcard.question}</p>
                    <p class="text-gray-600">${flashcard.answer}</p>
                </div>
            </div>
        `;
        
        // Add the "Edit" button
        flashcardContent += `
            <button class="edit-card-btn absolute bottom-2 right-2 flex items-center text-xs bg-white border border-gray-300 rounded-md px-2 py-1 text-gray-600 hover:bg-gray-50 hover:text-blue-600 transition-colors">
                <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                </svg>
                Edit
            </button>
        `;
        
        flashcardElement.innerHTML = flashcardContent;
        
        // Add click handler for the flashcard body (same as original)
        flashcardElement.addEventListener('click', (e) => {
            amplifyFlashcard(flashcardElement);
            scrollToHighlight(flashcardElement);
        });
        
        // Add separate click handler for the edit button
        const editButton = flashcardElement.querySelector('.edit-card-btn');
        editButton.addEventListener('click', (e) => {
            e.stopPropagation();
            amplifyFlashcard(flashcardElement);
            scrollToHighlight(flashcardElement);
            showEditPanel(flashcard);
        });

        // Add click handlers for accept and discard buttons for unaccepted cards
        if (!isAccepted) {
            const acceptButton = flashcardElement.querySelector('.accept-card-btn');
            acceptButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering the card click
                acceptFlashcard(flashcard.id);
            });
            
            const discardButton = flashcardElement.querySelector('.discard-card-btn');
            discardButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent triggering the card click
                discardFlashcard(flashcard.id);
            });
        }

        // Add hover handlers - only activate highlights if the card is not selected
        flashcardElement.addEventListener('mouseenter', () => {
            if (!flashcardElement.classList.contains('bg-blue-50')) {
                const flashcardId = flashcard.id;
                document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${flashcardId}"]`).forEach(highlight => {
                    highlight.classList.add('active');
                });
            }
        });

        flashcardElement.addEventListener('mouseleave', () => {
            if (!flashcardElement.classList.contains('bg-blue-50')) {
                const flashcardId = flashcard.id;
                document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${flashcardId}"]`).forEach(highlight => {
                    highlight.classList.remove('active');
                });
            }
        });
        
        container.appendChild(flashcardElement);
    }
}

// Amplify flashcard
function amplifyFlashcard(flashcardElement){
    // Remove selected class from all flashcards and deactivate all highlights
    document.querySelectorAll('#flashcardsContainer > div').forEach(card => {
        if (!card.classList.contains('py-2')) { // Skip section headers
            card.classList.remove('bg-blue-50', 'border-blue-200');
            const cardId = card.dataset.flashcardId;
            if (cardId) {
                document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${cardId}"]`).forEach(highlight => {
                    highlight.classList.remove('active');
                });
            }
        }
    });

    // Add selected class and activate highlights
    flashcardElement.classList.add('bg-blue-50', 'border-blue-200');
    
    const flashcardId = flashcardElement.dataset.flashcardId;
    const highlights = document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${flashcardId}"]`);
    
    // Activate all highlights for this flashcard
    highlights.forEach(highlight => {
        highlight.classList.add('active');
    });
    
}

// Scroll to highlight
function scrollToHighlight(flashcardElement){
    const flashcardId = flashcardElement.dataset.flashcardId;
    const highlights = document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${flashcardId}"]`);

    // Get the first highlight element to scroll to
    if (highlights.length > 0) {
        const firstHighlight = highlights[0];
        const pdfContainer = document.querySelector('#viewerContainer');
        
        // Get the highlight's position relative to the container
        const highlightRect = firstHighlight.getBoundingClientRect();
        const containerRect = pdfContainer.getBoundingClientRect();
        
        // Calculate the scroll position (adding some padding above)
        const scrollTop = highlightRect.top - containerRect.top + pdfContainer.scrollTop - 100;
        
        // Smooth scroll to the highlight
        pdfContainer.scrollTo({
            top: scrollTop,
            behavior: 'smooth'
        });
    }
}

// Handle accept and discard actions
function acceptFlashcard(flashcardId) {
  console.log(`Accepting flashcard with ID: ${flashcardId}`);
  
  // Call your backend API to update the flashcard
  fetch(`/accept_card/${flashcardId}/`, { 
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    }
  })
  .then(response => {
    if (!response.ok) throw new Error('Network response was not ok');
    return response.json();
  })
  .then(data => {
    console.log('Flashcard accepted successfully');
    // Refresh UI
    fetchAndCreateHighlights(currentDocumentId);
  })
  .catch(error => {
    console.error("Error accepting flashcard:", error);
  });
}

function discardFlashcard(flashcardId) {
  const modal = document.getElementById('confirm-discard-flashcard');
  const yesBtn = document.getElementById('confirm-yes');
  const noBtn = document.getElementById('confirm-no');

  modal.classList.remove('hidden');

  yesBtn.onclick = () => {
    modal.classList.add('hidden');

    fetch(`/delete_card/${flashcardId}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
    })
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    })
    .then(data => {
      if (data.success) {
        console.log('Flashcard discarded successfully');
        fetchAndCreateHighlights(currentDocumentId);
      } else {
        console.error('Failed to discard flashcard:', data.message);
      }
    })
    .catch(error => {
      console.error('Error discarding flashcard:', error);
    });
  };

  noBtn.onclick = () => {
    modal.classList.add('hidden');
  };
}


// Function to show flashcard tooltip
function showFlashcardTooltip(flashcard, highlightElement) {
    // Remove any existing tooltip
    hideFlashcardTooltip();
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.id = 'flashcard-tooltip';
    tooltip.className = 'flashcard-tooltip';
    tooltip.innerHTML = `
        <div class="flashcard-content">
            <div class="flashcard-question">${flashcard.question || 'Question not available'}</div>
            <div class="flashcard-answer">${flashcard.answer || 'Answer not available'}</div>
        </div>
    `;
    
    // Style the tooltip
    tooltip.style.position = 'absolute';
    tooltip.style.backgroundColor = 'white';
    tooltip.style.border = '1px solid #ccc';
    tooltip.style.borderRadius = '4px';
    tooltip.style.padding = '10px';
    tooltip.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    tooltip.style.zIndex = '200';
    tooltip.style.maxWidth = '300px';
    
    // Position the tooltip near the highlight
    const rect = highlightElement.getBoundingClientRect();
    const pdfContainer = document.querySelector('.pdfViewer');
    const containerRect = pdfContainer.getBoundingClientRect();
    
    tooltip.style.left = `${rect.right - containerRect.left + 10}px`;
    tooltip.style.top = `${rect.top - containerRect.top}px`;
    
    // Add the tooltip to the container
    pdfContainer.appendChild(tooltip);
}

// Function to hide flashcard tooltip
function hideFlashcardTooltip() {
    const existingTooltip = document.getElementById('flashcard-tooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }
}

// Control the width of the flashcards right column
document.addEventListener('DOMContentLoaded', function() {
    const divider = document.getElementById('divider');
    const leftSection = document.getElementById('leftSection');
    const rightSection = document.getElementById('rightSection');
    const container = divider.parentElement;
    
    let isDragging = false;
    
    divider.addEventListener('mousedown', function(e) {
        isDragging = true;
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        
        const containerRect = container.getBoundingClientRect();
        const containerWidth = containerRect.width;
        const mouseX = e.clientX - containerRect.left;
        
        // Calculate percentage (clamped between 20% and 80%)
        const percentage = Math.max(60, Math.min(80, (mouseX / containerWidth) * 100));
        
        // Apply the new widths
        leftSection.style.width = `${percentage}%`;
        rightSection.style.width = `${100 - percentage}%`;
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
    });
});

// Function to show the edit panel
function showEditPanel(flashcard) {
    console.log("starting showEditPanel()")
    // Get containers
    const rightSection = document.getElementById('rightSection');
    const flashcardsContainer = document.getElementById('flashcardsContainer');
    
    // Hide the flashcards container
    flashcardsContainer.classList.add('hidden');
    
    // Create the edit panel if it doesn't exist
    let editPanel = document.getElementById('editPanel');
    if (!editPanel) {
        editPanel = document.createElement('div');
        editPanel.id = 'editPanel';
        editPanel.className = 'flex-1 flex flex-col p-4 overflow-auto';
        rightSection.appendChild(editPanel);
    }

    // Determine if the flashcard has a bbox
    const hasBBox = flashcard.bbox && flashcard.bbox.length > 0;
    const editTextPlacementLabel = hasBBox ? "Edit Text Placement" : "Set Text Placement";
    
    // Populate the edit panel
    editPanel.innerHTML = `
        <div class="flex items-center mb-4">
            <button id="backToFlashcards" class="p-2 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-full transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                </svg>
            </button>
            <span class="ml-2 text-lg font-medium">Edit Flashcard</span>
        </div>
        
        <div class="space-y-4">
            <div>
                <label for="question" class="block text-sm font-medium text-gray-700 mb-1">Question</label>
                <textarea id="question" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-24">${flashcard.question}</textarea>
            </div>
            
            <div>
                <label for="answer" class="block text-sm font-medium text-gray-700 mb-1">Answer</label>
                <textarea id="answer" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 h-24">${flashcard.answer}</textarea>
            </div>
            
            <!-- Edit selection preview -->
            <div id="selectionPreviewEdit" class="hidden">
                <label class="block text-sm font-medium text-gray-700 mb-1">Selected Text</label>
                <div class="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 h-24 overflow-auto">
                    <p id="selectedTextPreviewEdit" class="text-gray-600 italic">No text selected</p>
                </div>
            </div>

            <div class="flex justify-between items-center gap-4">
                <button id="editTextPlacement" data-flashcard-id="${flashcard.id}"class="flex items-center px-4 py-2 border ${hasBBox ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-yellow-50 border-yellow-300 text-yellow-800'} rounded-md hover:${hasBBox ? 'bg-emerald-100 hover:text-emerald-800' : 'bg-yellow-100'} transition-colors w-auto font-medium shadow-sm">
                    ${!hasBBox ? `<svg class="w-5 h-5 mr-2 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                    </svg>` : ''}
                    ${editTextPlacementLabel}
                </button>
                
                <button id="saveFlashcard" data-flashcard-id="${flashcard.id}" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                    Save Changes
                </button>
            </div>
        </div>
    `;
    
    // Display the edit panel
    editPanel.classList.remove('hidden');
                  
    // Back to flashcards list
    document.getElementById('backToFlashcards').addEventListener('click', () => {
        exitSelectionMode();
        navigateTo('flashcardsContainer');
    });

    // Click handler for edit text placement (in existing cards)
    document.getElementById('editTextPlacement').addEventListener('click', function() {
        console.log('Edit text placement clicked');
        const flashcardId = this.dataset.flashcardId;
        console.log('Edit text placement clicked for flashcard:', flashcardId);
        toggleSelectionMode(this);

    });
    
    // Add click handler for the save button (placeholder for now)
    document.getElementById('saveFlashcard').addEventListener('click', function() {
        const updatedQuestion = document.getElementById('question').value;
        const updatedAnswer = document.getElementById('answer').value;
        const flashcardId = this.dataset.flashcardId;
        
        // Here you would typically send the updated data to the server
        console.log('Saving changes to flashcard:', {
            id: flashcardId,
            question: updatedQuestion,
            answer: updatedAnswer
        });
        
        // For now, just update the local data and return to flashcards view
        const flashcard = window.flashcards.find(fc => fc.id == flashcardId);
        if (flashcard) {
            flashcard.question = updatedQuestion;
            flashcard.answer = updatedAnswer;
            
            // Update the displayed flashcard
            const flashcardElement = document.querySelector(`#flashcardsContainer > div[data-flashcard-id="${flashcardId}"]`);
            if (flashcardElement) {
                const questionEl = flashcardElement.querySelector('p:first-child');
                const answerEl = flashcardElement.querySelector('p:nth-child(2)');
                
                if (questionEl) questionEl.innerHTML = `Q: ${updatedQuestion}`;
                if (answerEl) answerEl.innerHTML = `A: ${updatedAnswer}`;
            }
        }
        
        hideEditPanel();
    });
}

// Function to hide the edit panel and return to flashcards view
function hideEditPanel() {
    // Get containers
    const rightSection = document.getElementById('rightSection');
    const flashcardsContainer = document.getElementById('flashcardsContainer');
    const editPanel = document.getElementById('editPanel');
    
    // Show the flashcards container
    flashcardsContainer.classList.remove('hidden');
    
    // Hide the edit panel
    if (editPanel) {
        editPanel.classList.add('hidden');
    }
}
// Clear any existing highlights
function clearHighlights() {
    const existingHighlights = document.querySelectorAll('.pdf-highlight');
    existingHighlights.forEach(highlight => highlight.remove());
}

async function getSelectionWordCoords(startPage, endPage) {
    const pdfViewer = window.appPdfViewer;
    let allWords = [];

    // Get coordinates for each page in the range
    for (let pageNum = startPage; pageNum <= endPage; pageNum++) {
        const page = pdfViewer.getPageView(pageNum - 1).pdfPage;
        const viewport = pdfViewer.getPageView(pageNum - 1).viewport;

        const textContent = await page.getTextContent();
        const pageWords = textContent.items.map(item => {
            const [x, y] = viewport.convertToViewportPoint(item.transform[4], item.transform[5]);
            return {
                text: item.str,
                x: x,
                y: viewport.height - y, // Flip Y-axis for correct PDF coordinate system
                width: item.width,
                height: item.height,
                page: pageNum
            };
        });
        allWords = allWords.concat(pageWords);
    }
    return allWords;
}

// Attach event listener to detect text selection
window.addEventListener('mouseup', function() {
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    const selectionText = selection.toString();
    const selectionLength = selectionText.length;
    if (selectionLength > 2) {
        // Get start and end pages
        const pages = getStartAndEndPage(range);
        if (pages) {
            // Get the coordinates of the selected text for all pages in range
            getSelectionWordCoords(pages.startPage, pages.endPage).then(data => {
                // Store the selection data
                lastSelectionData = {
                    text: selectionText,
                    words: data,
                    doc_id: currentDocumentId
                };
                console.log("Selected text is:", lastSelectionData);
                // Update UI to reflect selection
                hasSelectedText = true;
                updateAIButton();
            });
        }
    } else {
        // Clear selection data if no text is selected
        lastSelectionData = null;
        hasSelectedText = false;
        updateAIButton();
    }
});


function getStartAndEndPage(range) {
    let startNode = range.startContainer;
    let endNode = range.endContainer;
    
    // Navigate up to parent elements if we're in text nodes
    if (startNode.nodeType === Node.TEXT_NODE) startNode = startNode.parentElement;
    if (endNode.nodeType === Node.TEXT_NODE) endNode = endNode.parentElement;
    
    // Find the closest page elements
    const startPageElement = startNode.closest('.page');
    const endPageElement = endNode.closest('.page');
    
    // If either element is present, use it for both
    if (startPageElement || endPageElement) {
        startPage = startPageElement ? parseInt(startPageElement.dataset.pageNumber, 10) : null;
        endPage = endPageElement ? parseInt(endPageElement.dataset.pageNumber, 10) : null;
        
        // If one is missing, copy the other one
        if (startPage && !endPage) {
            endPage = startPage;
        }
        if (!startPage && endPage) {
            startPage = endPage;
        }
        
        console.log("startPage:", startPage);
        console.log("endPage:", endPage);
        return {
            startPage: startPage,
            endPage: endPage
        };
    }
    return null;
}



function updateAIButton() {
    const aiButton = document.getElementById('aiButton');
    if (hasSelectedText) {
        aiButton.disabled = false;
        aiButton.classList.remove('text-gray-400', 'cursor-not-allowed', 'disabled:hover:text-gray-400');
        aiButton.classList.add('text-gray-600', 'hover:text-gray-900', 'button-flash');
        aiButton.title = "AI will generate cards from your selection";
        
        // Remove the animation class after it completes
        aiButton.addEventListener('animationend', () => {
            aiButton.classList.remove('button-flash');
        }, { once: true });
    } else {
        aiButton.disabled = true;
        aiButton.classList.remove('text-gray-600', 'hover:text-gray-900', 'button-flash');
        aiButton.classList.add('text-gray-400', 'cursor-not-allowed', 'disabled:hover:text-gray-400');
        aiButton.title = "Select text to generate AI cards";
    }
}

// Add click handler for AI button
document.getElementById('aiButton').addEventListener('click', function(e) {
    if (this.disabled || !lastSelectionData) {
        // Show a tooltip or notification that text needs to be selected
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = 'Please select text first';
        document.body.appendChild(notification);
        
        // Remove the notification after 2 seconds
        setTimeout(() => {
            notification.remove();
        }, 2000);
        return;
    }
    
    // Send the selection data to the server
    console.log("Sending selection data to server:", lastSelectionData);

    fetch('/process-selection/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            selection: lastSelectionData,
            deck_id: currentDeckId
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Server response:", data);
        // Refresh the flashcards after successful processing
        if (currentDocumentId) {
            fetchAndCreateHighlights(currentDocumentId);
        }
    })
    .catch(error => {
        console.error("Error:", error);
        // Show error notification
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = 'Error processing selection. Please try again.';
        document.body.appendChild(notification);
        
        // Remove the notification after 2 seconds
        setTimeout(() => {
            notification.remove();
        }, 2000);
    });
});


// Function to create highlights
function createHighlights(flashcards, showFlashcardsLog) {
    if (showFlashcardsLog === true) {
        console.log("Creating highlights...");
    }
    clearHighlights();

    // Get the PDF viewer using the same reference as in the getSelectionWordCoords function
    const pdfViewer = window.appPdfViewer;
    if (!pdfViewer) {
        if (showFlashcardsLog === true) {
            console.error('PDF viewer not found');
        }
        return;
    }

    flashcards.forEach((flashcard, index) => {
        // It's possible that some cards do not have a bbox
        
        // Log the flashcard info if showFlashcardsLog is true
        if (showFlashcardsLog === true) {
            console.log(`Flashcard ${index + 1}:`, {
                id: flashcard.id,
                q: flashcard.question,
                bboxes: flashcard.bbox
            });
        }

        // Process each bbox in the array
        flashcard.bbox.forEach((bbox, bboxIndex) => {
            // Skip if this specific bbox is missing required properties
            if (!bbox.x || !bbox.y || !bbox.page) {
                if (showFlashcardsLog === true) {
                    console.warn(`Skipping invalid bbox at index ${bboxIndex} for flashcard:`, flashcard.id);
                    console.warn(`Bbox properties:`, bbox);
                }
                return;
            }
            
            // Get the correct page container
            const pageView = pdfViewer.getPageView(bbox.page - 1);
            if (!pageView || !pageView.div) {
                if (showFlashcardsLog === true) {
                    console.warn(`Page ${bbox.page} view not found for highlight`);
                }
                return;
            }
            const pageContainer = pageView.div;

            // Create highlight element
            const highlight = document.createElement('div');
            highlight.className = 'pdf-highlight';
            highlight.dataset.flashcardId = flashcard.id;
            highlight.id = `flashcard-highlight-${flashcard.id}-${bboxIndex}`;

            // Apply styles
            highlight.style.position = 'absolute';
            highlight.style.left = `${bbox.x}px`;
            highlight.style.top = `${pageView.viewport.height - bbox.y - bbox.height}px`;
            highlight.style.width = `${bbox.width}px`;
            highlight.style.height = `${bbox.height}px`;
            let bgColor = 'rgba(255, 255, 0, 0.2)'; // accepted: yellow
            if (flashcard.accepted !== true) {
                bgColor = 'rgba(112, 128, 144, 0.3)'; // not accepted: 
            }

            highlight.style.backgroundColor = bgColor; 
            highlight.style.pointerEvents = 'auto';
            highlight.style.zIndex = '100';
            highlight.style.cursor = 'pointer';  // Add pointer cursor
            
            // Add hover event to show flashcard content
            highlight.addEventListener('mouseenter', function() {
                console.log('Mouse entering bbox')
                showFlashcardTooltip(flashcard, highlight);
            });
            
            highlight.addEventListener('mouseleave', function() {
                hideFlashcardTooltip();
            });

            // Add click handler to select and scroll to the corresponding flashcard
            highlight.addEventListener('click', function() {
                const flashcardId = flashcard.id;
                const flashcardElement = document.querySelector(`#flashcardsContainer > div[data-flashcard-id="${flashcardId}"]`);
                
                if (flashcardElement) {
                    // Remove selected class from all flashcards and deactivate all highlights
                    document.querySelectorAll('#flashcardsContainer > div').forEach(card => {
                        card.classList.remove('bg-blue-50', 'border-blue-200');
                        const cardId = card.dataset.flashcardId;
                        document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${cardId}"]`).forEach(highlight => {
                            highlight.classList.remove('active');
                        });
                    });
                    
                    // Add selected class to the clicked flashcard and activate its highlights
                    flashcardElement.classList.add('bg-blue-50', 'border-blue-200');
                    document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${flashcardId}"]`).forEach(highlight => {
                        highlight.classList.add('active');
                    });

                    // Scroll the flashcard into view
                    flashcardElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });

            pageContainer.appendChild(highlight);
        });
    });
}

// Event listener to track the Ctrl key state, allow selecting highlighted texts
document.addEventListener('keydown', function(e) {
    if (e.key === 'Control') {
        // Change pointer-events for all highlights when Ctrl is pressed
        document.querySelectorAll('.pdf-highlight').forEach(highlight => {
            highlight.style.pointerEvents = 'none';
        });
    }
});

// Event listener to track the Ctrl key state, allow selecting highlighted texts
document.addEventListener('keyup', function(e) {
    if (e.key === 'Control') {
        // Restore pointer-events when Ctrl is released
        document.querySelectorAll('.pdf-highlight').forEach(highlight => {
            highlight.style.pointerEvents = 'auto';
        });
    }
});

// Add click handler to clear selection when clicking outside highlights
document.getElementById('viewerContainer').addEventListener('click', function(e) {
    // Check if the click was on a highlight
    if (!e.target.classList.contains('pdf-highlight')) {
        // Remove selected class from all flashcards and deactivate all highlights
        document.querySelectorAll('#flashcardsContainer > div').forEach(card => {
            card.classList.remove('bg-blue-50', 'border-blue-200');
            const cardId = card.dataset.flashcardId;
            document.querySelectorAll(`.pdf-highlight[data-flashcard-id="${cardId}"]`).forEach(highlight => {
                highlight.classList.remove('active');
            });
        });
    }
});
// Add these global variables
let inSelectionMode = false;
let lastSelectionData = null;
let buttonIdTextSelection = null;
let updateTextPlacement = false;

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

// Event listener for mouseup that waits for text selection and handles what happens
window.addEventListener('mouseup', async function () {
    const selectionData = await generateSelectionData();
    if (!selectionData) return;
    console.log("selectionData is: ", selectionData)

    // This object is where we store the selected data. Acessible from everywhere
    lastSelectionData = selectionData;

    // If the selection happened in create with AI
    if (buttonIdTextSelection == "startTextSelectionAI") {
        console.log('selection happened in create with AI')
        // Show selection in the preview area
        document.getElementById('selectionPreviewAI').classList.remove('hidden');
        const previewElement = document.getElementById('selectedTextPreviewAI');
        const selectionText = selectionData.text;
        if (selectionText.length > 200) {
            previewElement.textContent = 
                selectionText.substring(0, 100) + ' [...] ' + selectionText.substring(selectionText.length - 100);
        } else {
            previewElement.textContent = selectionText;
        }

        // Enable the submit button
        document.getElementById('submitAiFlashcard').disabled = false;
        document.getElementById('submitAiFlashcard').classList.remove('opacity-50', 'cursor-not-allowed');

        // Restart buttons
        document.getElementById('startTextSelectionAI').textContent = 'Start Selection';
        document.getElementById('startTextSelectionAI').classList.remove('bg-yellow-200', 'border-yellow-400');
    }

    // If the selection happened in create Manually
    if (buttonIdTextSelection == "setTextPlacement"){
        console.log('selection happened in create Manually')
        // Show selection in the preview area
        document.getElementById('selectionPreviewManually').classList.remove('hidden');
        const previewElement = document.getElementById('selectedTextPreviewManually');
        const selectionText = selectionData.text;
        if (selectionText.length > 200) {
            previewElement.textContent = 
                selectionText.substring(0, 100) + ' [...] ' + selectionText.substring(selectionText.length - 100);
        } else {
            previewElement.textContent = selectionText;
        }
        updateTextPlacement = true;
        
        // Restart buttons
        document.getElementById('setTextPlacement').textContent = 'Edit Text Placement';
        document.getElementById('setTextPlacement').classList.remove('bg-yellow-200', 'border-yellow-400');
    }

    // If the selection happened in edit Card
    if (buttonIdTextSelection == "editTextPlacement"){
        console.log('selection happened in edit Card')
        // Show selection in the preview area
        document.getElementById('selectionPreviewEdit').classList.remove('hidden');
        const previewElement = document.getElementById('selectedTextPreviewEdit');
        const selectionText = selectionData.text;
        if (selectionText.length > 200) {
            previewElement.textContent = 
                selectionText.substring(0, 100) + ' [...] ' + selectionText.substring(selectionText.length - 100);
        } else {
            previewElement.textContent = selectionText;
        }
        updateTextPlacement = true;

        // Restart buttons
        document.getElementById('editTextPlacement').textContent = 'Edit Text Placement';
        document.getElementById('editTextPlacement').classList.remove('bg-yellow-200', 'border-yellow-400');
    }
    
    
    // Reset selection mode
    inSelectionMode = false;
    document.getElementById('viewerContainer').classList.remove('selection-mode');
});

// Set text placement in flashcard
async function setTextPlacement(boxes, card_id) {
    const response = await fetch('/set-text-placement/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            boxes: boxes,
            card_id: card_id
        })
    });

    if (!response.ok) {
        throw new Error('Failed to process selection');
    }

    const data = await response.json();
    return data.boxes;

}

// Generates the selection data we need to pass to the card generator
async function generateSelectionData() {
    if (!inSelectionMode) return null;

    const selection = window.getSelection();
    const selectionText = selection.toString();
    const selectionLength = selectionText.length;

    if (selectionLength <= 2) return null;

    const range = selection.getRangeAt(0);
    const pages = getStartAndEndPage(range);
    if (!pages) return null;

    const wordCoords = await getSelectionWordCoords(pages.startPage, pages.endPage);

    return {
        text: selectionText,
        words: wordCoords,
        doc_id: currentDocumentId
    };
}

// Get start and end page of selected data
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

// Generate Cards submit button event listener
document.getElementById('submitAiFlashcard').addEventListener('click', async function() {
    if (!lastSelectionData) {
        return;
    }
    
    // Disable button while processing, show message
    const submitButton = document.getElementById('submitAiFlashcard');
    showLoading("Generating Cards...");

    // Save original text if not already saved
    if (!submitButton.dataset.originalText) {
        submitButton.dataset.originalText = submitButton.textContent;
    }

    // Disable button and show overlay
    submitButton.disabled = true;
    submitButton.classList.add('opacity-50', 'cursor-not-allowed');
    submitButton.textContent = 'Generating Cards...';

    // Get context from input
    const aiContext = document.getElementById('aiContext').value;
    console.log("aiContext is: ", aiContext)
    try{
        // Step 1: Process selection and get boxes
        const boxes = await processSelection(lastSelectionData);
        console.log('Boxes from text-to-boxes:', boxes);

        // Step 2: Get matched flashcards to text using boxes
        await matchFlashcardsToText(lastSelectionData, aiContext, boxes, currentDeckId);

        // Refresh the flashcards after successful processing
        if (currentDocumentId) {
            console.log("currentDocumentId found, calling fetchAndCreateHighlights()...")
            fetchAndCreateHighlights(currentDocumentId);
        }

        // Return to flashcards view
        document.getElementById('flashcardsContainer').classList.remove('hidden');
        document.getElementById('aiSelectionPanel').classList.add('hidden');
    } catch (error) {
        console.error("Error:", error);
        // Show error notification
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 right-4 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
        notification.textContent = 'Error processing selection. Please try again.';
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 2000);
    } finally {
        submitButton.disabled = false;
        submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
        submitButton.textContent = submitButton.dataset.originalText;
        hideLoading();
    }
});

// Function 1: Call /text-to-boxes/
async function processSelection(selection, context) {
    const response = await fetch('/text-to-boxes/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            selection: selection
        })
    });

    if (!response.ok) {
        throw new Error('Failed to process selection');
    }

    const data = await response.json();
    return data.boxes;
}

// Function 2: Call /match-flashcards-to-text/
async function matchFlashcardsToText(selection, aiContext, boxes, deckId) {
    const response = await fetch('/match-flashcards-to-text/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            selection: selection,
            aiContext: aiContext,
            boxes: boxes,
            deck_id: deckId
        })
    });

    if (!response.ok) {
        throw new Error('Failed to get matched flashcards');
    }

    await response.json();
}


// Click handler for AI button
document.getElementById('aiButton').addEventListener('click', () => {
    resetCreateState(); // Clear before entering AI view
    navigateTo('aiSelectionPanel');
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

// text selection mode
function toggleSelectionMode(button) {
    if (inSelectionMode) {
        // Exit selection mode
        exitSelectionMode();
        button.classList.remove('bg-yellow-200', 'border-yellow-400');
        button.textContent = button.dataset.originalText;
    } else {
        // Enter selection mode
        inSelectionMode = true;
        buttonIdTextSelection = button.id;
        
        // Save original text if not saved yet
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.textContent;
        }
        
        button.classList.add('bg-yellow-200', 'border-yellow-400');
        button.textContent = 'Cancel';
        
        const notification = document.createElement('div');
        notification.className = 'absolute bottom-4 right-4 transform bg-gray-800 text-white px-4 py-2 rounded-lg shadow z-10';
        notification.textContent = 'Select text in the document. Hold Ctrl to select over already linked text.';
        
        const viewer = document.getElementById('documentViewerModal');
        viewer.style.position = 'relative';
        viewer.appendChild(notification);
        
        setTimeout(() => notification.remove(), 3000);
    }
}

// Toggle selection mode when clicking on select text from create with AI
document.getElementById('startTextSelectionAI').addEventListener('click', function() {
    toggleSelectionMode(this);
});

// reset any var inside the create with AI or create Manually
function resetCreateState() {
    // Exit selection mode if active
    if (inSelectionMode) {
        exitSelectionMode();
    }

    // Reset Manual Create inputs
    const manualQuestion = document.getElementById('newQuestion');
    const manualAnswer = document.getElementById('newAnswer');
    if (manualQuestion) manualQuestion.value = '';
    if (manualAnswer) manualAnswer.value = '';

    // Reset AI Create inputs
    const aiContext = document.getElementById('aiContext');
    if (aiContext) aiContext.value = '';

    // Reset AI selection preview
    const selectedTextPreviewAI = document.getElementById('selectedTextPreviewAI');
    if (selectedTextPreviewAI) selectedTextPreviewAI.textContent = 'No text selected';
    const selectionPreviewAI = document.getElementById('selectionPreviewAI');
    if (selectionPreviewAI) selectionPreviewAI.classList.add('hidden');

    // Reset manual selection preview
    const selectedTextPreviewManually = document.getElementById('selectedTextPreviewManually');
    if (selectedTextPreviewManually) selectedTextPreviewManually.textContent = 'No text selected';
    const selectionPreviewManually = document.getElementById('selectionPreviewManually');
    if (selectionPreviewManually) selectionPreviewManually.classList.add('hidden');

    // Reset edit selection preview
    const selectedTextPreviewEdit = document.getElementById('selectedTextPreviewEdit');
    if (selectedTextPreviewEdit) selectedTextPreviewEdit.textContent = 'No new text placement';
    const selectionPreviewEdit = document.getElementById('selectionPreviewEdit');
    if (selectionPreviewEdit) selectionPreviewEdit.classList.add('hidden');

    // Reset selection mode variables & buttons
    inSelectionMode = false;
    lastSelectionData = null;
    const startTextBtn = document.getElementById('startTextSelectionAI');
    if (startTextBtn) {
        startTextBtn.textContent = 'Start Selection';
        startTextBtn.classList.remove('bg-yellow-200', 'border-yellow-400');
    }
    const setTextBtn = document.getElementById('setTextPlacement');
    if (setTextBtn) {
        setTextBtn.textContent = 'Set Text Placement';
        setTextBtn.classList.remove('bg-yellow-200', 'border-yellow-400');
    }

    // Disable AI submit button
    const submitBtn = document.getElementById('submitAiFlashcard');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    // // Clear any highlights if used
    // document.querySelectorAll('.highlight').forEach(el => el.classList.remove('highlight'));
}


// Navigate to a panel. Hide all panels, show only the one we navigate to
function navigateTo(view) {
    const panels = ['flashcardsContainer', 'createPanel', 'aiSelectionPanel', 'editPanel'];
    panels.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.classList.add('hidden');
        }
    });

    const target = document.getElementById(view);
    if (target) {
        target.classList.remove('hidden');
    } else {
        console.warn(`Element with ID '${view}' not found.`);
    }
}



// Handle exiting selection mode
function exitSelectionMode() {
    inSelectionMode = false;
    document.getElementById('viewerContainer').classList.remove('selection-mode');
    document.getElementById('startTextSelectionAI').textContent = 'Start Selection';
    document.getElementById('startTextSelectionAI').classList.remove('bg-yellow-200', 'border-yellow-400');
}

// Back from AI selection to flashcards list
document.getElementById('backFromAiSelection').addEventListener('click', () => {
    exitSelectionMode();
    navigateTo('flashcardsContainer');
});

// Initialize PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
const pdfjsViewer = window.pdfjsViewer;

async function viewDocument(documentId, documentName) {
    console.log("Retrieving document with id:", documentId);

    // Reset UI state - make sure the create panels are hidden and the flashcard list is visible
    document.getElementById('createPanel').classList.add('hidden');
    document.getElementById('aiSelectionPanel').classList.add('hidden');
    if (document.querySelector('.px-4.py-2.border-b')) {
        document.querySelector('.px-4.py-2.border-b').style.display = '';
    }
    if (document.getElementById('flashcardsContainer')) {
        document.getElementById('flashcardsContainer').classList.remove('hidden');
    }
    // Clear any form inputs from previous sessions
    if (document.getElementById('newQuestion')) {
        document.getElementById('newQuestion').value = '';
    }
    if (document.getElementById('newAnswer')) {
        document.getElementById('newAnswer').value = '';
    }
    
    document.getElementById('outerContainerModal').classList.remove('hidden');
    currentDocumentId = documentId;

    try {
        const response = await fetch(`/document/${documentId}/url/`);
        const data = await response.json();
        
        // Store the deck information globally
        currentDeckId = data.deck_id;
        const displayDeckName = data.deck_name;
        console.log("Document belongs to deck:", displayDeckName, currentDeckId);

        // Update the viewer title
        document.getElementById("viewerTitle").innerText = documentName;

        // Update the deck info in the right sidebar
        const deckInfoElement = document.querySelector('#rightSection .mt-1.text-sm');
        if (deckInfoElement) {
            // Create the URL for the deck
            const deckUrl = `/study/?deck_id=${currentDeckId}`;
            deckInfoElement.innerHTML = `Deck: <a href="${deckUrl}" class="text-blue-500 hover:underline">${displayDeckName}</a>`;
        } else {
            console.error("Deck info element not found");
        }

        const container = document.getElementById('viewerContainer');
        const viewer = document.getElementById('viewer');
        
        // Create an event bus to listen for rendering events
        const eventBus = new pdfjsViewer.EventBus();

        // Setup event listener for when pages are rendered
        eventBus.on('pagesloaded', function() {
            console.log("PDF pages loaded, fetching flashcards...");
            fetchAndCreateHighlights(documentId);
        });

        const pdfDoc = await pdfjsLib.getDocument(data.url).promise;
        const pdfViewer = new pdfjsViewer.PDFViewer({
            container: container,
            viewer: viewer,
            eventBus: eventBus,
        });
        
        pdfViewer.setDocument(pdfDoc);
        window.appPdfViewer = pdfViewer; // Store the viewer instance globally

    } catch (error) {
        console.error("Error loading PDF:", error);
    }
}

// Close PDF Viewer Container
function closeViewer() {
    document.getElementById('outerContainerModal').classList.add('hidden');
    // Remove all existing highlights when closing the viewer
    clearHighlights();
    currentDocumentId = null;
}


// Set up listeners for PDF.js page rendering events
function setupPageRenderingListeners() {
    // Scrolling to new pages makes the DOM forget old pages
    // this means old highlights are removed
    // we need to create them all again
    console.log("launching setupPageRenderingListeners")
    const pdfViewer = window.appPdfViewer;
    if (!pdfViewer || !pdfViewer.eventBus) {
        console.error('PDF viewer or eventBus not found');
        return;
    }
    
    // Listen for page rendering events
    pdfViewer.eventBus.on('pagerendered', function(evt) {
        const pageNumber = evt.pageNumber;
        // console.log("Page", pageNumber, "rendered")
        createHighlights(window.flashcards, false);
    });
}

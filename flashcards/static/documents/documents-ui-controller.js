// Show loading overlay with custom text
function showLoading(text = "Loading...") {
    document.getElementById('loadingText').innerText = text;
    document.getElementById('loadingOverlay').classList.remove('hidden');
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').classList.add('hidden');
}

// === Upload Modal Logic ===
const openBtn = document.getElementById('open-upload-modal');
const modal = document.getElementById('upload-modal');
const cancelBtn = document.getElementById('cancel-upload');

openBtn.addEventListener('click', () => {
    modal.classList.remove('hidden');
});

cancelBtn.addEventListener('click', () => {
    modal.classList.add('hidden');
});

function confirmDelete(documentId, documentName, deckName) {
    // Update dialog message
    const messageEl = document.getElementById('deleteMessage');
    messageEl.innerHTML = `Are you sure you want to delete <strong>${documentName}</strong>?<br><br>This action will also delete the associated deck <strong>${deckName}</strong> and all of its flashcards and subdecks.`;
    
    // Set up confirm button to call delete with the current document info
    const confirmBtn = document.getElementById('confirmDeleteButton');
    
    // Remove any existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    // Add new event listener with document info closure
    newConfirmBtn.addEventListener('click', function() {
        deleteDocument(documentId, documentName);
        document.getElementById('deleteDialog').classList.add('hidden');
    });
    
    // Show the dialog
    document.getElementById('deleteDialog').classList.remove('hidden');
}

function deleteDocument(documentId, documentName) {
    console.log(`Deleting document: ${documentName} (ID: ${documentId})`);
    
    const spinner = document.getElementById('delete-spinner');
    spinner.classList.remove('hidden');  // Show the spinner

    const deleteUrl = `/documents/delete/${documentId}/`;
    fetch(deleteUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
        },
    })
    .then(response => {
        spinner.classList.add('hidden');  // Hide the spinner after delete
        if (!response.ok) throw new Error('Delete failed');
        window.location.reload();
    })
    .catch(error => {
        spinner.classList.add('hidden');  // Hide the spinner if error
        alert('Delete failed. Please try again.');
        console.error(error);
    });
}

// Add some CSS to the page
const style = document.createElement('style');
style.textContent = `
    .flashcard-tooltip {
        transition: opacity 0.2s ease;
    }
    .flashcard-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .flashcard-question {
        font-weight: bold;
    }
    .flashcard-answer {
        color: #333;
    }
    .pdf-highlight {
        transition: all 0.2s ease;
    }
    .pdf-highlight.active {
        background-color: rgba(255, 196, 0, 0.5) !important;
        box-shadow: 0 0 8px rgba(255, 196, 0, 0.5);
        z-index: 101 !important;
    }
    #rightSection {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    #flashcardsContainer {
        flex: 1;
        overflow-y: auto;
        overflow-x: hidden;
    }
    #flashcardsContainer > div {
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    #flashcardsContainer > div:hover:not(.bg-blue-50) {
        background-color: rgb(243 244 246) !important;
    }
    #flashcardsContainer > div.bg-blue-50 {
        background-color: rgb(239 246 255) !important;
    }
    @keyframes buttonFlash {
        0% { 
            color: rgb(107, 114, 128);
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
        }
        25% { 
            color: rgb(34, 197, 94);
            transform: scale(1.03);
            box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
        }
        50% { 
            color: rgb(34, 197, 94);
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
        }
        75% { 
            color: rgb(34, 197, 94);
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
        }
        100% { 
            color: rgb(75, 85, 99);
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
        }
    }
    .button-flash {
        animation: buttonFlash 2s ease;
        position: relative;
        overflow: visible;
    }
    .button-flash svg {
        animation: buttonFlash 2s ease;
    }
`;
document.head.appendChild(style);


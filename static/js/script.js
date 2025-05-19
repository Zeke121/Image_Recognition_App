document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const imageUploadInput = document.getElementById('imageUpload');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorMessagesDiv = document.getElementById('errorMessages');
    const resultsContainer = document.getElementById('resultsContainer');
    const originalImageElem = document.getElementById('originalImage');
    const processedImageElem = document.getElementById('processedImage');
    const detectionDetailsContainer = document.getElementById('detectionDetails');
    const detectionListElem = document.getElementById('detectionList');

    // Logo carousel - basic seamless scroll. CSS handles animation.
    // If you need more complex JS-driven carousel, this would be the place.
    // For now, CSS animation should suffice as requested.

    imageUploadInput.addEventListener('change', function(event) {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            const reader = new FileReader();

            reader.onload = function(e) {
                originalImageElem.src = e.target.result;
                resultsContainer.style.display = 'flex'; // Show original image preview
                processedImageElem.src = '#'; // Clear previous processed
                detectionDetailsContainer.style.display = 'none';
                detectionListElem.innerHTML = '';
            }
            reader.readAsDataURL(file);

            // Automatically submit after selection
            submitForm();
        }
    });

    function submitForm() {
        const formData = new FormData(uploadForm);
        if (!imageUploadInput.files || imageUploadInput.files.length === 0) {
            showError("Please select an image file.");
            return;
        }

        loadingIndicator.style.display = 'block';
        errorMessagesDiv.style.display = 'none';
        errorMessagesDiv.textContent = '';
        // resultsContainer.style.display = 'none'; // Keep original visible
        processedImageElem.src = '#'; // Clear previous processed image
        detectionDetailsContainer.style.display = 'none';


        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                // Try to parse error message from JSON if server sends it
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            loadingIndicator.style.display = 'none';
            if (data.success) {
                originalImageElem.src = data.original_image_url + '?t=' + new Date().getTime(); // Cache buster
                processedImageElem.src = data.processed_image_url + '?t=' + new Date().getTime(); // Cache buster
                resultsContainer.style.display = 'flex';

                if (data.detections && data.detections.length > 0) {
                    detectionListElem.innerHTML = ''; // Clear previous detections
                    data.detections.forEach(det => {
                        const listItem = document.createElement('li');
                        listItem.textContent = `${det.label}: ${ (det.confidence * 100).toFixed(2) }%`;
                        detectionListElem.appendChild(listItem);
                    });
                    detectionDetailsContainer.style.display = 'block';
                } else {
                    detectionListElem.innerHTML = '<li>No objects detected with high confidence.</li>';
                    detectionDetailsContainer.style.display = 'block';
                }

            } else {
                showError(data.error || "An unknown error occurred during analysis.");
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            console.error('Error:', error);
            let errorMessage = "An error occurred while processing your request.";
            if (error && error.error) { // If server sent a JSON error
                errorMessage = error.error;
            } else if (error.message) { // Network error or other JS error
                 errorMessage = error.message;
            }
            showError(errorMessage);
        });
    }

    function showError(message) {
        errorMessagesDiv.textContent = message;
        errorMessagesDiv.style.display = 'block';
        resultsContainer.style.display = 'none';
        detectionDetailsContainer.style.display = 'none';
    }

    // If you want the main CTA button to also submit if a file is already selected:
    const mainCtaButton = document.querySelector('header .cta-button');
    if (mainCtaButton) {
        mainCtaButton.addEventListener('click', function() {
            if (imageUploadInput.files && imageUploadInput.files.length > 0) {
                // If a file is already selected and user clicks "Upload & Analyze" again
                // (e.g., after an error, or to re-process), re-submit.
                // submitForm(); // This might be redundant if file input's change event triggers it.
                // The current setup: CTA button just opens file dialog. Change event handles submit.
            } else {
                imageUploadInput.click(); // If no file, open dialog.
            }
        });
    }
});
document.addEventListener('DOMContentLoaded', function() {
    const analyzeButton = document.getElementById('analyzeButton');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');
    const loadingSpinner = document.querySelector('.loading');

    analyzeButton.addEventListener('click', async function() {
        // Update UI to show processing state
        analyzeButton.disabled = true;
        statusDiv.textContent = 'Analyzing terms and conditions...';
        loadingSpinner.style.display = 'inline-block';
        resultsDiv.style.display = 'none';
        
        try {
            // Get the active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // Check if we can inject content script into this tab
            if (!tab || !tab.url || tab.url.startsWith('chrome://')) {
                throw new Error('Cannot analyze terms on this page. Please try on a regular webpage.');
            }

            // Inject content script manually to ensure it's loaded
            try {
                await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content/content.js']
                });
            } catch (injectionError) {
                console.log('Content script already loaded or injection failed:', injectionError);
            }

            // Add a small delay to ensure content script is ready
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Request the text content from the content script
            const response = await chrome.tabs.sendMessage(tab.id, { action: 'getTermsAndConditions' })
                .catch(error => {
                    throw new Error('Failed to communicate with the page. Please refresh and try again.');
                });
            
            if (response && response.termsText) {
                // Send to background script for API processing
                const analysis = await chrome.runtime.sendMessage({
                    action: 'analyzeTerms',
                    terms: response.termsText
                });

                // Display the results
                displayResults(analysis);
                statusDiv.textContent = 'Analysis complete!';
            } else {
                throw new Error('No terms and conditions found on this page. Please select the text manually.');
            }
        } catch (error) {
            statusDiv.textContent = 'Error: ' + error.message;
            console.error('Error:', error);
        } finally {
            analyzeButton.disabled = false;
            loadingSpinner.style.display = 'none';
        }
    });

    function displayResults(analysis) {
        const riskySectionDiv = document.getElementById('concerningTerms');
        const generalSectionDiv = document.getElementById('generalTerms');
        
        // Update section titles with warning icons
        riskySectionDiv.querySelector('h2').innerHTML = '<i class="fas fa-exclamation-triangle"></i> Watch Out For These';
        generalSectionDiv.querySelector('h2').innerHTML = '<i class="fas fa-clipboard-list"></i> What You\'re Agreeing To';
        
        // Display risky clauses
        const riskyContent = riskySectionDiv.querySelector('.content');
        riskyContent.innerHTML = '';
        
        if (analysis.riskyClauses && analysis.riskyClauses.length > 0) {
            analysis.riskyClauses.forEach(item => {
                const clauseDiv = document.createElement('div');
                clauseDiv.className = 'risky-clause';
                clauseDiv.innerHTML = `<p class="clause-impact">${item.impact}</p>`;
                riskyContent.appendChild(clauseDiv);
            });
        } else {
            riskyContent.innerHTML = '<div class="risky-clause"><p>No unusual or concerning terms found.</p></div>';
        }
        
        // Display summary
        const generalContent = generalSectionDiv.querySelector('.content');
        generalContent.innerHTML = `<div class="summary-text">${analysis.summary || 'No summary available'}</div>`;
        
        // Show results
        resultsDiv.style.display = 'block';
    }

    // Initialize popup state
    function initializePopup() {
        statusDiv.textContent = 'Select terms and conditions text and Click \'Analyze\' .';
        loadingSpinner.style.display = 'none';
        resultsDiv.style.display = 'none';
        analyzeButton.disabled = false;
    }

    // Call initialization
    initializePopup();
});



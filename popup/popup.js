document.addEventListener('DOMContentLoaded', function() {
    const analyzeButton = document.getElementById('analyzeButton');
    const statusDiv = document.getElementById('status');
    const resultsDiv = document.getElementById('results');
    const concerningTermsDiv = document.getElementById('concerningTerms').querySelector('.content');
    const generalTermsDiv = document.getElementById('generalTerms').querySelector('.content');

    analyzeButton.addEventListener('click', async function() {
        // Update UI to show processing state
        analyzeButton.disabled = true;
        statusDiv.textContent = 'Analyzing terms and conditions...';
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
                // Continue execution as the script might already be loaded
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

                // Parse the markdown response
                const sections = parseAnalysisResponse(analysis);
                
                // Display results
                concerningTermsDiv.innerHTML = sections.concerning || 'No concerning terms found.';
                generalTermsDiv.innerHTML = sections.general || 'No general terms found.';
                resultsDiv.style.display = 'block';
                statusDiv.textContent = 'Analysis complete!';
            } else {
                statusDiv.textContent = 'No terms and conditions found on this page.';
            }
        } catch (error) {
            statusDiv.textContent = 'Error: ' + error.message;
            console.error('Error:', error);
        } finally {
            analyzeButton.disabled = false;
        }
    });

    function parseAnalysisResponse(markdownText) {
        const sections = {
            concerning: '',
            general: ''
        };

        // Simple markdown parsing
        const lines = markdownText.split('\n');
        let currentSection = null;

        for (const line of lines) {
            if (line.toLowerCase().includes('concerning and risky')) {
                currentSection = 'concerning';
                continue;
            } else if (line.toLowerCase().includes('general')) {
                currentSection = 'general';
                continue;
            }

            if (currentSection && line.trim()) {
                sections[currentSection] += line + '<br>';
            }
        }

        return sections;
    }
});
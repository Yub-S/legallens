// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getTermsAndConditions') {
        try {
            // Attempt to find terms and conditions content
            const termsText = findTermsAndConditions();
            sendResponse({ termsText });
        } catch (error) {
            sendResponse({ error: error.message });
        }
        return true; // Required for async response
    }
});

function findTermsAndConditions() {
    // Array of possible selectors where terms might be found
    const possibleSelectors = [
        // Common terms and conditions containers
        'div[class*="terms"]',
        'div[class*="condition"]',
        'div[class*="policy"]',
        'section[class*="terms"]',
        'article[class*="terms"]',
        // Common ID patterns
        '#terms',
        '#termsAndConditions',
        '#terms-and-conditions',
        '#terms-conditions',
        '#policy',
        '#privacy-policy',
        // Common text containers
        '.terms-content',
        '.policy-content',
        '.legal-content'
    ];

    let termsContent = '';

    // Try each selector
    for (const selector of possibleSelectors) {
        const elements = document.querySelectorAll(selector);
        for (const element of elements) {
            const text = element.innerText.trim();
            if (text.length > 100 && (
                text.toLowerCase().includes('terms') ||
                text.toLowerCase().includes('conditions') ||
                text.toLowerCase().includes('agreement')
            )) {
                termsContent = text;
                break;
            }
        }
        if (termsContent) break;
    }

    // If no specific terms container found, look for selected text
    if (!termsContent) {
        const selection = window.getSelection();
        if (selection && selection.toString().trim().length > 0) {
            termsContent = selection.toString().trim();
        }
    }

    return termsContent || 'No terms and conditions found. Please select the text manually.';
}
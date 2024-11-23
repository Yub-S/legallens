// Store your API key securely
// Note: In production, you should implement proper key management
const API_KEY = 'f2844e54-1e58-4b6a-b6f5-7de64c693b38';
const API_URL = 'https://api.sambanova.ai/v1/chat/completions';

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'analyzeTerms') {
        analyzeTerms(request.terms)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ error: error.message }));
        return true; // Required for async response
    }
});

async function analyzeTerms(termsText) {
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${API_KEY}`
            },
            body: JSON.stringify({
                model: 'Meta-Llama-3.1-405B-Instruct',
                messages: [{
                    role: 'user',
                    content: `here is a term and condition that the user is about to sign.
                    ${termsText}

                    Your job is to scan this and explain the user what's in it keeping everything concise and without leaving anything. 
                    your explanation should be like it's mentioned that you agree to .....(in simple and understandable way so that user don't need to read the entire term and condition.)
                    you are like a careful blocker or assistant that prevents the users from signing any harmful terms and condition.

                    before the explanation you should point out any sneaky/highly risky/some terms and conditions that are not relevant in any sense, and list them. 
                    and give explanation of what's the term and condition contains. without making it long.

                    if you have mentioned any term and condition up in the concerning section , no need to do it down. so it's better to categorize it into multiple section.
                    1. concerning and risky and 2. general.
                    each one would have what's written in the term and condition . and then the what it means in detail but concise.

                    respond it in a markdown.`
                }],
                temperature: 0.1
            })
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        const data = await response.json();
        return data.choices[0].message.content;
    } catch (error) {
        console.error('API Error:', error);
        throw new Error('Failed to analyze terms and conditions');
    }
}

// Add error handling for when API quota is exceeded
let requestCount = 0;
const MAX_REQUESTS_PER_MINUTE = 10;

setInterval(() => {
    requestCount = 0;
}, 60000); // Reset counter every minute
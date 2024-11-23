// background.js
import config from '../config.js';

const API_KEY = config.API_KEY;
const API_URL = config.API_URL;


// const API_KEY = "f2844e54-1e58-4b6a-b6f5-7de64c693b38";
// const API_URL = 'https://api.sambanova.ai/v1/chat/completions';

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'analyzeTerms') {
        analyzeTerms(request.terms)
            .then(response => {
                console.log('API Response:', response); // Debug log
                sendResponse(response);
            })
            .catch(error => {
                console.error('Analysis Error:', error); // Debug log
                sendResponse({ error: error.message });
            });
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
                    content: `Analyze these terms and conditions carefully and respond in JSON format:
                    ${termsText}

                    Your role is to identify potentially harmful or unusual terms and explain their real-world implications in simple language.

                    Create a JSON response with exactly this structure:
                    {
                        "riskyClauses": [
                            {
                                "impact": "Direct statement of what this means for the user in practical terms, focusing on consequences and risks"
                            }
                        ],
                        "summary": "A concise summary of entire term and condition like what it contains in a simple, easy and understandable way. Not that much long just couple of sentences."
                    }

                    Guidelines:
                    - Focus ONLY on identifying terms that:
                      * Could have unexpected consequences for users
                      * Involve financial risks or obligations
                      * Affect user rights or property
                      * Give unusual powers to the service provider
                      * Are not standard in typical terms
                    - For each risky clause:
                      * Skip the legal language completely
                      * State only the practical impact
                      * Use direct, consequence-focused language
                      * Explain why users should care
                    - Keep language simple and conversational
                    - Ensure the output is valid JSON
                    
                    Example impacts:
                    BAD: "You agree to grant unlimited usage rights to your content"
                    GOOD: "The company can use all your uploaded content however they want without paying you or asking permission"

                    BAD: "You consent to automatic payment processing"
                    GOOD: "They can automatically charge your card without asking you first"`
                }],
                temperature: 0.1
            })
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        const data = await response.json();
        let parsedContent;
        
        try {
            parsedContent = JSON.parse(data.choices[0].message.content);
        } catch (parseError) {
            const jsonMatch = data.choices[0].message.content.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                parsedContent = JSON.parse(jsonMatch[0]);
            } else {
                throw new Error('Failed to parse LLM response as JSON');
            }
        }

        // Validate expected structure
        if (!parsedContent.riskyClauses || !parsedContent.summary) {
            throw new Error('Invalid response structure from LLM');
        }

        return parsedContent;
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
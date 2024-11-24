# Legal Lens 🔍

Legal Lens is a browser extension that helps users understand Terms & Conditions easily. Select any text from Terms & Conditions on any webpage, click the extension, and get an AI-powered analysis of potential risks and important points.

## Features 

- 🚀 Quick text selection and analysis
- ⚠️ Clear identification of potentially harmful clauses
- 📝 Easy-to-understand summaries
- ⚡ Instant results

## Installation Guide

### 1. Get the Code

```bash
git clone [your-repository-url]
cd legal-lens
git checkout extension_branch
```

### 2. API Configuration

In `config.js` file, replace the "YOUR_API_KEY_HERE" with your actual sambanova api:

```javascript
const config = {
    API_KEY: "YOUR_API_KEY_HERE",
    API_URL: "https://api.sambanova.ai/v1/chat/completions"
};

export default config;
```

### 3. Load Extension in Chrome

1. Open Chrome browser
2. Type `chrome://extensions/` in the address bar
3. Enable "Developer mode" in the top right corner
4. Click "Load unpacked"
5. Browse to the legal-lens folder and select it
6. The extension icon should appear in your browser toolbar

## How to Use

1. Visit any website with Terms & Conditions
2. Select the text you want to analyze
3. Click on the Legal Lens extension icon in your browser
4. Click the "Analyze" button
5. Review the AI-powered analysis of the selected text

## Project Structure

```
legal-lens/
├── manifest.json
├── config.js          
├── popup/
│   ├── popup.html
│   ├── popup.css
│   └── popup.js
├── background/
│   └── background.js
├── content/
│   └── content.js
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```
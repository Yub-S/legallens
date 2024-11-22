# LegalLens

## 📝 Introduction
**LegalLens** is an agentic application that helps users understand and analyze their long legal contracts. It explains every clause in simple, understandable terms, verifies the legality of each clause, and suggests modifications or counteractions where necessary. Whether you're an individual, startup, or legal professional, LegalLens ensures nothing important slips through the cracks before signing a contract.

## ⚙️ How It Works

1. **User Uploads PDF**:
   - The user uploads a contract (PDF format) to LegalLens.
   
2. **Preliminary Analysis**:
   - LLaMA 3.2 Vision Model from SambaNova Cloud scans the PDF and extracts key details such as terms, conditions, obligations, and clauses.

3. **Detailed Analysis**:
   - LLaMA 3.1 405B Model interprets the extracted information and provides clear, concise explanations of each clause

4. **Legality Check**:
   - Crewai Agent searches across legal forums, documents, and databases (via SerperDevTool) to verify if each clause is legally sound.

5. **Recommendations**:
   - Based on the legality check, LegalLens suggests modifications, counters, or adjustments to improve the contract.


5. **User Decision**:
   - The user can accept, reject, or counter each clause based on the AI’s analysis and recommendations.

## 🛠️ How to Run It Locally

### Requirements

- Install all dependencies listed in `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application
1. Clone the repository:
    ```bash
    git clone https://github.com/Yub-S/legallens.git
    cd legallens
    ```

2. Run the app using Streamlit:
    ```bash
    streamlit run app.py
    ```

3. Make sure you have the necessary API keys set up in the `.env` file.

### .env File Format
```bash
SAMBANOVA_API_KEY="your_sambanova_api_key"
SERPER_API_KEY="your_serper_api_key"

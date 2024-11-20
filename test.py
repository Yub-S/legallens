import streamlit as st
import os
import openai
import fitz  # PyMuPDF
import base64
import json
import logging
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from crew import manage_crew_for_clause

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
def init_session_state():
    if 'contract_content' not in st.session_state:
        st.session_state.contract_content = None
    if 'clauses' not in st.session_state:
        st.session_state.clauses = []
    if 'responses' not in st.session_state:
        st.session_state.responses = {}
    if 'generated_email' not in st.session_state:
        st.session_state.generated_email = None
    if 'pdf_images' not in st.session_state:
        st.session_state.pdf_images = None
    if 'legal_analyses' not in st.session_state:
        st.session_state.legal_analyses = {}
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False

# Initialize OpenAI client
def init_openai_client():
    try:
        load_dotenv()
        api_key = os.environ.get("SAMBANOVA_API_KEY")
        base_url = "https://api.sambanova.ai/v1"
        return openai.OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        st.error("Failed to initialize API client. Please check your credentials.")
        return None

def convert_pdf_to_images(pdf_file):
    """Convert PDF pages to base64 encoded images with error handling"""
    try:
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        images = []
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buffered = BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            images.append(img_str)
        return images
    except Exception as e:
        logger.error(f"PDF processing error: {str(e)}")
        st.error("Error processing PDF. Please ensure the file is not corrupted.")
        return None

def extract_contract_content(client, images):
    """Extract content from contract images with improved error handling"""
    if not images:
        return None

    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        } for img in images
    ]

    vision_prompt = """You are a meticulous contract reviewer. Your task is to:
1. Carefully read through the entire contract
2. Extract ALL important points, terms, conditions, and obligations, clauses that the user must see and not miss in detail as they are. 
3. Include specific numbers, dates, and key details
4. Pay special attention to:
   - Financial terms
   - Deadlines and timelines
   - Obligations and responsibilities
   - clauses
   - Limitations and restrictions
   - Special conditions
   - Legal requirements

Provide your response as plain text, capturing all essential content from the contract."""

    try:
        response = client.chat.completions.create(
            model='Llama-3.2-90B-Vision-Instruct',
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": vision_prompt},
                    *image_contents
                ]
            }],
            temperature=0.1,
            top_p=0.1,
            timeout=60  # Add timeout
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Content extraction error: {str(e)}")
        st.error("Failed to extract contract content. Please try again.")
        return None

def analyze_contract_content(client, contract_text):
    """Analyze contract content with improved error handling"""
    if not contract_text:
        return []

    analysis_prompt = f"""As an expert legal analyst, analyze this contract content and structure it into clear, detailed clauses.
You can keep related sections into single clause for better understanding for the user.

Contract Content:
{contract_text}

For each important clause you identify:
1. Provide a clear, specific title
2. Give a detailed explanation that includes:
   - The exact terms stated in the contract, explaining to the user about the clause like this: "This clause states that you..."
   - A detailed clear explanation in plain language of what the signer is agreeing to, just as if you are the user's legal advisor.

Format your response as a valid JSON array with this structure:
[
    {{
        "clause_title": "Title of First Clause",
        "description": "Comprehensive explanation of first clause"
    }}
]
provide only the json ouput as above nothing else."""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-405B-Instruct',
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            timeout=30
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            st.error("Failed to parse analysis response")
            return []
            
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        st.error("Failed to analyze contract content")
        return []

def handle_file_upload():
    """Handle file upload with state management"""
    if st.session_state.uploaded_file is not None:
        with st.spinner('Processing contract...'):
            client = init_openai_client()
            if not client:
                return

            # Reset states
            st.session_state.pdf_images = None
            st.session_state.contract_content = None
            st.session_state.clauses = []
            st.session_state.legal_analyses = {}
            st.session_state.processing_complete = False

            # Process PDF
            images = convert_pdf_to_images(st.session_state.uploaded_file)
            if images:
                st.session_state.pdf_images = images
                st.session_state.contract_content = extract_contract_content(client, images)
                if st.session_state.contract_content:
                    st.session_state.clauses = analyze_contract_content(client, st.session_state.contract_content)
                    st.session_state.processing_complete = True

def update_response(clause_id: int, response_type: str, counter_text: str = ""):
    """Update response without triggering rerun"""
    st.session_state.responses[clause_id] = {
        'type': response_type,
        'counter_text': counter_text if response_type == 'Counter' else None
    }

def generate_counter_email(client, responses, clauses):
    """Generate response email with improved error handling"""
    if not responses or not clauses:
        return ""

    accepted_clauses = []
    rejected_clauses = []
    counter_proposals = []

    for clause in clauses:
        clause_id = hash(clause['clause_title'])
        if clause_id in responses:
            response = responses[clause_id]
            if response['type'] == 'Accept':
                accepted_clauses.append(clause['clause_title'])
            elif response['type'] == 'Reject':
                rejected_clauses.append(clause['clause_title'])
            elif response['type'] == 'Counter':
                counter_proposals.append({
                    'clause': clause['clause_title'],
                    'proposal': response['counter_text']
                })

    prompt = f"""As a legal professional, compose a formal contract review response email. 

Context:
- Accepted Clauses: {accepted_clauses}
- Rejected Clauses: {rejected_clauses}
- Counter Proposals: {counter_proposals}

Requirements:
1. Use a professional, courteous tone
2. Start with a brief introduction
3. Clearly organize the response into sections:
   - Accepted terms
   - Terms requiring modification (with specific counter-proposals)
   - Rejected terms (with brief explanations)
4. Conclude with next steps
5. Maintain a constructive, solution-focused approach"""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-70B-Instruct',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Email generation error: {str(e)}")
        st.error("Failed to generate email response")
        return ""

def render_sidebar():
    """Render the sidebar with file upload"""
    with st.sidebar:
        st.title("Upload Contract")
        st.file_uploader(
            "Choose a contract PDF file",
            type="pdf",
            key="uploaded_file",
            on_change=handle_file_upload
        )
        
        if st.session_state.processing_complete:
            if st.button("📤 Generate Response Email", type="primary"):
                client = init_openai_client()
                if client:
                    st.session_state.generated_email = generate_counter_email(
                        client,
                        st.session_state.responses,
                        st.session_state.clauses
                    )

def render_main_content():
    """Render the main content area"""
    if not st.session_state.contract_content:
        st.title("Professional Contract Analysis System")
        st.write("Please upload a contract PDF file to begin analysis.")
        return

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Contract Content")
        st.markdown(st.session_state.contract_content)

    with col2:
        st.subheader("Clause Analysis")
        for clause in st.session_state.clauses:
            clause_id = hash(clause['clause_title'])
            
            with st.expander(f"📄 {clause['clause_title']}", expanded=True):
                # Description
                st.markdown("**Description:**")
                st.write(clause['description'])
                
                # Legal Analysis
                if clause_id not in st.session_state.legal_analyses:
                    with st.spinner('Analyzing clause...'):
                        st.session_state.legal_analyses[clause_id] = manage_crew_for_clause(clause['description'])
                
                st.markdown("**Legal Analysis and Recommendation:**")
                st.write(st.session_state.legal_analyses[clause_id].raw)
                
                # Response UI
                response_col, counter_col = st.columns([1, 2])
                with response_col:
                    response_type = st.radio(
                        "Your response:",
                        ["Accept", "Reject", "Counter"],
                        key=f"response_type_{clause_id}",
                        on_change=update_response,
                        args=(clause_id, st.session_state.get(f"response_type_{clause_id}", "Accept"))
                    )
                
                if response_type == "Counter":
                    with counter_col:
                        counter_text = st.text_area(
                            "Enter your counter proposal:",
                            key=f"counter_text_{clause_id}",
                            on_change=update_response,
                            args=(clause_id, response_type, st.session_state.get(f"counter_text_{clause_id}", ""))
                        )

        # Display generated email if available
        if st.session_state.generated_email:
            st.subheader("📧 Generated Response Email")
            st.text_area(
                "Email Content",
                st.session_state.generated_email,
                height=400
            )

def main():
    st.set_page_config(layout="wide")
    init_session_state()
    
    # Custom CSS for better UI
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stButton button {
            width: 100%;
        }
        .clause-box {
            border: 1px solid #ddd;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    render_sidebar()
    render_main_content()

if __name__ == "__main__":
    main()
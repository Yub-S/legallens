import streamlit as st
import os
import openai
import fitz  # PyMuPDF
import base64
import json
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from crew import manage_crew_for_clause

load_dotenv()

# Initialize session state
if 'contract_content' not in st.session_state:
    st.session_state.contract_content = None
if 'clauses' not in st.session_state:
    st.session_state.clauses = []
if 'responses' not in st.session_state:
    st.session_state.responses = {}
if 'generated_email' not in st.session_state:
    st.session_state.generated_email = None

# OpenAI client initialization
api_key = os.environ.get("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"
client = openai.OpenAI(api_key=api_key, base_url=base_url)

def convert_pdf_to_images(pdf_file):
    """
    Convert PDF pages to base64 encoded images.
    Returns: List of base64 encoded images
    """
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
        st.error(f"Error processing PDF: {str(e)}")
        return None

def extract_contract_content(images):
    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        } for img in images
    ]

    vision_prompt = """You are a meticulous contract reviewer. Your task is to:
1. Carefully read through the entire contract
2. Extract ALL important points, terms, conditions, and obligations in detail. If it's very long, you can summarize it without any lost in the intent of that content.extract detailed information about the point,term,obligations and so on.
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
            top_p=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error extracting contract content: {str(e)}")
        return None

def analyze_contract_content(contract_text):
    analysis_prompt = f"""As an expert legal analyst, analyze this contract content and structure it into clear, detailed clauses.You can keep related sections into single clause for better understanding for the user.

Contract Content:
{contract_text}

For each important clause you identify:
1. Provide a clear, specific title
2. Give a detailed explanation that includes:
   - The exact terms stated in the contract
   - A detailed clear explanation in plain language of what the signer is agreeing to, just as if you are the user's legal advisor.

Format your response as a valid JSON array like this:
[
    {{
        "clause_title": "Title of First Clause",
        "description": "Comprehensive explanation of first clause"
    }}
]"""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-70B-Instruct',
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            st.error("Failed to parse analysis response as JSON")
            st.write("Raw response:", response.choices[0].message.content)
            return []
            
    except Exception as e:
        st.error(f"Error analyzing contract content: {str(e)}")
        return []

def handle_file_upload():
    if st.session_state.uploaded_file is not None:
        with st.spinner('Processing contract...'):
            images = convert_pdf_to_images(st.session_state.uploaded_file)
            st.session_state.contract_content = extract_contract_content(images)
            st.session_state.clauses = analyze_contract_content(st.session_state.contract_content)

def handle_response_change(clause_id):
    response_type = st.session_state[f"response_{clause_id}"]
    counter_text = st.session_state.get(f"counter_{clause_id}", "")
    
    st.session_state.responses[clause_id] = {
        'type': response_type,
        'counter_text': counter_text if response_type == 'Counter' else None
    }

def generate_counter_email(responses, clauses):
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
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating email: {str(e)}")
        return ""

def main():
    st.title("Professional Contract Analysis System")

    # File uploader
    st.file_uploader("Choose a contract PDF file", type="pdf", key="uploaded_file", on_change=handle_file_upload)

    # Display contract content if available
    if st.session_state.contract_content:
        with st.container():
            st.subheader("Contract Content")
            st.markdown(st.session_state.contract_content)
            
            st.subheader("Clause Analysis")
            for clause in st.session_state.clauses:
                clause_id = hash(clause['clause_title'])
                
                # Initialize response state for this clause if not exists
                if f"response_{clause_id}" not in st.session_state:
                    st.session_state[f"response_{clause_id}"] = "Accept"
                
                with st.expander(f"📄 {clause['clause_title']}", expanded=True):
                    st.markdown("**Description:**")
                    st.write(clause['description'])
                    
                    # Legal analysis
                    with st.spinner('Analyzing clause...'):
                        crew_result = manage_crew_for_clause(clause['description'])
                        st.markdown("**Legal Analysis and Recommendation:**")
                        st.write(crew_result.raw)
                    
                    # Response section
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.radio(
                            "Your response:",
                            ["Accept", "Reject", "Counter"],
                            key=f"response_{clause_id}",
                            on_change=handle_response_change,
                            args=(clause_id,)
                        )
                    
                    if st.session_state[f"response_{clause_id}"] == "Counter":
                        with col2:
                            st.text_area(
                                "Enter your counter proposal:",
                                key=f"counter_{clause_id}",
                                on_change=handle_response_change,
                                args=(clause_id,)
                            )

            # Generate email button
            if st.button("📤 Generate Response Email", type="primary"):
                st.session_state.generated_email = generate_counter_email(
                    st.session_state.responses,
                    st.session_state.clauses
                )
            
            # Display generated email if available
            if st.session_state.generated_email:
                st.subheader("📧 Generated Response Email")
                st.text_area("Email Content", st.session_state.generated_email, height=400)

if __name__ == "__main__":
    main()
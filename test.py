import streamlit as st
import os
import openai
import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image
import tempfile
from dotenv import load_dotenv

load_dotenv()
# Initialize OpenAI client
def init_client():
    return openai.OpenAI(
        api_key=os.environ.get("SAMBANOVA_API_KEY"),
        base_url="https://api.sambanova.ai/v1",
    )

def convert_pdf_to_images(pdf_file):
    """Convert PDF pages to images"""
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    images = []
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        images.append(img_str)
    return images

def analyze_page(client, image_base64):
    """Analyze a single page using the vision model"""
    response = client.chat.completions.create(
        model='Llama-3.2-11B-Vision-Instruct',
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "You are a contract analysis expert. Please carefully read this contract page and identify all important clauses and their implications. Provide a detailed explanation of each clause in a clear and structured format."
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            }]
        }],
        temperature=0.1,
        top_p=0.1
    )
    return response.choices[0].message.content

def generate_counter_email(client, clauses_summary):
    """Generate a professional counter-proposal email"""
    prompt = f"""As a legal professional, please create a formal email summarizing the following contract review:

{clauses_summary}

The email should:
1. Be professionally formatted
2. Clearly list accepted clauses
3. Explain rejected clauses with reasoning
4. Detail counter-proposals
5. Maintain a constructive and professional tone"""

    response = client.chat.completions.create(
        model='llama3.1-405B',
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content

def main():
    st.title("Contract Analysis Assistant")
    st.write("Upload a contract PDF for detailed analysis")

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        # Initialize session state for storing analysis results
        if 'clause_analyses' not in st.session_state:
            st.session_state.clause_analyses = []
            st.session_state.user_responses = {}
        
        # Convert PDF to images and analyze
        client = init_client()
        images = convert_pdf_to_images(uploaded_file)
        
        # Analyze each page
        for i, img in enumerate(images):
            st.subheader(f"Page {i+1} Analysis")
            
            # Only analyze if not already in session state
            if len(st.session_state.clause_analyses) <= i:
                with st.spinner(f'Analyzing page {i+1}...'):
                    analysis = analyze_page(client, img)
                    st.session_state.clause_analyses.append(analysis)
            
            # Display analysis and get user response
            st.write(st.session_state.clause_analyses[i])
            
            # Response options for each clause
            clause_key = f"page_{i}"
            response = st.radio(
                "Your response to this page's clauses:",
                ["Accept", "Reject", "Counter"],
                key=f"response_{i}"
            )
            
            # Counter proposal text area
            counter_text = ""
            if response == "Counter":
                counter_text = st.text_area(
                    "Enter your counter proposal:",
                    key=f"counter_{i}"
                )
            
            st.session_state.user_responses[clause_key] = {
                "response": response,
                "counter": counter_text if response == "Counter" else ""
            }
        
        # Finalize button
        if st.button("Finalize Analysis"):
            # Prepare summary for email generation
            summary = ""
            for i in range(len(images)):
                response = st.session_state.user_responses[f"page_{i}"]
                summary += f"\nPage {i+1}:\n"
                summary += f"Analysis: {st.session_state.clause_analyses[i]}\n"
                summary += f"Response: {response['response']}\n"
                if response['counter']:
                    summary += f"Counter Proposal: {response['counter']}\n"
            
            # Generate email
            with st.spinner('Generating response email...'):
                email = generate_counter_email(client, summary)
                st.subheader("Generated Response Email")
                st.text_area("Email Content", email, height=300)
                
                # Add download button for email
                st.download_button(
                    label="Download Email",
                    data=email,
                    file_name="contract_response.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
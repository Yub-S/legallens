import streamlit as st
import os
import openai
import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from crew import manage_crew_for_clause

load_dotenv()

# OpenAI client initialization
api_key = os.environ.get("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"
client = openai.OpenAI(api_key=api_key, base_url=base_url)

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

def analyze_page(image_base64):
    """Analyze a single page using the vision model"""
    response = client.chat.completions.create(
        model='Llama-3.2-90B-Vision-Instruct',
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": """You are an AI contract analysis expert. Please carefully read the entire contract page provided.
                           Identify and explain briefly the important clauses, terms, and information that should not be missed."""
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            }]
        }],
        temperature=0.1,
        top_p=0.1
    )
    return response.choices[0].message.content

def generate_counter_email(client, analysis_results):
    """Generate a professional counter-proposal email"""
    # Prepare a summary of all page analyses and user responses
    summary = "Contract Analysis Summary:\n\n"
    for page_num, page_analyses in enumerate(analysis_results):
        for analysis in page_analyses:
            summary += f"Page {page_num + 1}:\n"
            summary += f"Clause: {analysis['clause']}\n"
            summary += f"Legal Analysis: {analysis['legal_analysis']}\n"
            summary += f"Review Analysis: {analysis['review_analysis']}\n"
            
            # Add user response if available in session state
            response_key = f"response_{hash(analysis['clause'])}"
            if response_key in st.session_state:
                response = st.session_state[response_key]
                summary += f"User Response: {response}\n"
                
                if response == "Counter":
                    counter_key = f"counter_{hash(analysis['clause'])}"
                    if counter_key in st.session_state:
                        summary += f"Counter Proposal: {st.session_state[counter_key]}\n"
            
            summary += "\n"

    # Generate email using LLM
    prompt = f"""As a legal professional, please create a formal email summarizing the following contract review:

{summary}

The email should:
1. Be professionally formatted
2. Clearly list accepted and rejected clauses
3. Explain the reasoning behind each decision
4. Include counter-proposals where applicable
5. Maintain a constructive and professional tone"""

    response = client.chat.completions.create(
        model='llama3.1-405B',
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content

def main():
    st.title("Advanced Contract Analysis with Multi-Agent System")

    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file:

        # Convert PDF to images
        images = convert_pdf_to_images(uploaded_file)

        # Analysis results container
        analysis_results = []

        # Analyze each page
        for i, img in enumerate(images):
            st.subheader(f"Page {i+1} Analysis")

            # Vision-based clause extraction
            clause = analyze_page(img)
            
            # Analyze each clause
            page_analyses = []
            crew_result = manage_crew_for_clause(clause)
            page_analyses.append({
                'clause': clause,
                'legal_analysis': crew_result.tasks_output[0].raw,  # First task result
                'review_analysis': crew_result.tasks_output[1].raw  # Second task result
            })

            # Store and display results
            analysis_results.append(page_analyses)

            # Display results with accept/reject/counter options
            for analysis in page_analyses:
                st.write(f"**Clause:** {analysis['clause']}")
                st.write(f"**Legal Analysis:** {analysis['legal_analysis']}")
                st.write(f"**Clause Review:** {analysis['review_analysis']}")

                response = st.radio(
                    "Your response:",
                    ["Accept", "Reject", "Counter"],
                    key=f"response_{hash(analysis['clause'])}"
                )

                if response == "Counter":
                    st.text_area("Enter your counter proposal:",
                                 key=f"counter_{hash(analysis['clause'])}")

        # Generate email button
        if st.button("Generate Response Email"):
            # Generate email
            with st.spinner('Generating response email...'):
                email = generate_counter_email(client, analysis_results)
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
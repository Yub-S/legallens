import streamlit as st
import openai
import fitz
import base64
import json
import logging
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import os
from crew import manage_crew_for_clause

load_dotenv()

# Initialize session state
if 'responses' not in st.session_state:
    st.session_state.responses = {}
if 'generated_email' not in st.session_state:
    st.session_state.generated_email = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'clauses' not in st.session_state:
    st.session_state.clauses = []
if 'show_email' not in st.session_state:
    st.session_state.show_email = False

api_key = os.environ.get("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"
client = openai.OpenAI(api_key=api_key, base_url=base_url)

def convert_pdf_to_images(pdf_file):
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
        st.error("Error processing PDF. Please ensure the file is not corrupted.")
        return None

def extract_contract_content(images):
    image_contents = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"}
        } for img in images
    ]

    vision_prompt = """You are a highly capable contract analyzer. Your role is to help users quickly analyze lengthy contracts, which otherwise would take hours. Your responsibilities are:

1. Carefully read each clause or term in the contract.
2. If the terms or conditions are general or straightforward, summarize them while maintaining their technicality and meaning.
3. If the terms, conditions, clauses, or obligations are advanced, complex, or crucial (e.g., legal or financial terms with significant implications), you must extract the exact full text without summarizing or omitting any part. The user must not miss these critical details, as further analysis will depend on your output.
4. Use a structured format with appropriate titles for each clause, making it easier for the next system or agent to analyze further.
5. Always prioritize accuracy, ensuring no important detail is left out.

Provide your response as normal text with clear titles and subheadings for readability. Be precise and meticulous in distinguishing between general terms and critical clauses.
"""

    try:
        response = client.chat.completions.create(
            model='Llama-3.2-11B-Vision-Instruct',
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": vision_prompt},
                    *image_contents
                ]
            }],
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error("Failed to extract contract content.")
        return None

def analyze_contract_content(contract_text):
    analysis_prompt = f"""You are an expert legal analyst acting as the user's personal legal lawyer. Your role is to analyze the user's contract and provide clear explanations of each clause with the following responsibilities:

1. **Explain Clearly:** Break down each clause in plain, easy-to-understand language. Ensure the user understands what is written and its implications. 
2. **Focus on Critical Clauses:** Pay special attention to clauses, terms, or conditions that may be tricky, complex, or have significant legal or financial implications. Highlight these clearly and explain why they are important, ensuring the user is fully aware of their potential impact.
3. **Handle General Clauses Efficiently:** For general clauses or terms that do not pose significant risks or complexities, you may merge similar clauses and provide a concise explanation. Reassure the user if there is nothing to worry about in these sections.
4. **Prioritize User Understanding:** Your primary goal is to make the contract as clear and accessible as possible for the user. Avoid legal jargon where unnecessary but retain technical accuracy.

Format as JSON array:
[
    {{
        "clause_title": "Title",
        "description": "Explanation"
    }}
]
provide only the json output nothing else. no any other test.

   here is the contract :
   {contract_text}"""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-405B-Instruct',
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error("Failed to analyze contract content")
        return []

def generate_email(clauses,responses):
    if not responses or not clauses:
        return ""

    decisions = []
    for clause in clauses:
        clause_id = str(hash(clause['clause_title']))
        if clause_id in responses:
            response = responses[clause_id]
            decision = {
                'clause': clause['clause_title'],
                'decision': response['type'],
                'counter_proposal': response.get('counter_text', '')
            }
            decisions.append(decision)

    prompt = f"""Generate a formal contract review email based on these decisions:
{json.dumps(decisions, indent=2)}

Include:
1. Professional introduction
2. Accepted terms
3. Terms requiring modification with counter-proposals
4. Rejected terms
5. Next steps"""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-70B-Instruct',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error("Failed to generate email")
        return ""

def update_response(clause_id, response_type, counter_text=''):
    st.session_state.responses[clause_id] = {
        'type': response_type,
        'counter_text': counter_text if response_type == 'Counter' else ''
    }

def main():
    st.title("Contract Analyzer")
    
    # File upload
    uploaded_file = st.file_uploader("Upload Contract (PDF)", type="pdf")
    
    if uploaded_file:
        # Analyze button
        if st.button("Analyze Contract"):
            with st.spinner("Processing contract..."):
                images = convert_pdf_to_images(uploaded_file)
                
                if images:
                    contract_text = extract_contract_content(images)
                    print(contract_text)
                    if contract_text:
                        st.session_state.clauses = analyze_contract_content(contract_text)
                        st.session_state.processing_complete = True
                        st.rerun()

    # Display clauses and analysis
    if st.session_state.processing_complete:
        for idx, clause in enumerate(st.session_state.clauses):
            clause_id = str(hash(clause['clause_title']))

            st.markdown(f"### Clause {idx + 1}: {clause['clause_title']}")
            st.markdown(clause['description'])

            # Get crew analysis if not already present
            if clause_id not in st.session_state:
                st.session_state[clause_id] = {}

            if 'implications' not in st.session_state[clause_id]:
                with st.spinner("Analyzing implications..."):
                    analysis = manage_crew_for_clause(clause['description'])
                    st.session_state[clause_id]['implications'] = analysis.raw

            # Display the implications
            st.write(st.session_state[clause_id]['implications'])

            # Response options
            col1, col2 = st.columns([1, 2])
            with col1:
                response_type = st.radio(
                    "Your Decision",
                    ["Accept", "Reject", "Counter"],
                    key=f"response_{clause_id}",
                    on_change=update_response,
                    args=(clause_id, st.session_state.get(f"response_{clause_id}", "Accept"))
                )

            with col2:
                if response_type == "Counter":
                    counter_text = st.text_area(
                        "Counter Proposal",
                        key=f"counter_{clause_id}",
                        on_change=update_response,
                        args=(clause_id, "Counter", st.session_state.get(f"counter_{clause_id}", ""))
                    )

            st.markdown("---")

        # Finalize contract button
        if st.button("Finalize Contract"):
            with st.spinner("Generating response email..."):
                email = generate_email(st.session_state.clauses, st.session_state.responses)
                st.session_state.generated_email = email
                st.session_state.show_email = True

        # Display generated email
        if st.session_state.show_email and st.session_state.generated_email:
            st.markdown("### Generated Response Email")
            st.text_area("", st.session_state.generated_email, height=400)

if __name__ == "__main__":
    main()
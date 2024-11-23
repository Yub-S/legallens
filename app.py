#added to resolve the deployment issues in streamlit
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
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
import time
from crew import manage_crew_for_clause

load_dotenv()

# Initialize session state
# Initialize session state
if 'responses' not in st.session_state:
    st.session_state.responses = {}
if 'generated_email' not in st.session_state:
    st.session_state.generated_email = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'clauses' not in st.session_state:
    st.session_state.clauses = []
if 'summary_clauses' not in st.session_state:
    st.session_state.summary_clauses = []
if 'show_email' not in st.session_state:
    st.session_state.show_email = False
if 'contract_finalized' not in st.session_state:
    st.session_state.contract_finalized = False
if 'analysis_mode' not in st.session_state:
    st.session_state.analysis_mode = None

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

def extract_contract_content(image):
    max_retries = 20  # Maximum number of retries defined for any sort of error 
    retries = 0

    vision_prompt = """You are a highly capable contract analyzer. Your role is to help users quickly analyze lengthy contracts, which otherwise would take hours. Your responsibilities are:

1. Carefully read each clause or term or condition in the contract.
2. If the terms or conditions or clauses are general or straightforward, summarize them while maintaining their technicality and meaning.
3. If the terms, conditions, clauses, or obligations are advanced, complex, or crucial (e.g., legal or financial terms with significant implications), you must extract the exact full text without summarizing or omitting any part. The user must not miss these critical details, as further analysis will depend on your output.
4. Use a structured format with appropriate titles for each clause, making it easier for the next system or agent to analyze further.
5. Always prioritize accuracy, ensuring no important detail is left out.

never try to miss anything. because each detail matters. no need to provide any introduction of the page.

Provide your response as normal text with clear titles and subheadings for readability. Be precise and meticulous in distinguishing between general terms and critical clauses.
"""

    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model='Llama-3.2-11B-Vision-Instruct',
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
                    ]
                }],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            retries += 1
            if retries < max_retries:
                time.sleep(2)  # Wait before retrying
            else:
                st.error("Failed to extract contract content after multiple retries.")
                return None

def analyze_contract_content(contract_text):
    max_retries = 20  # Maximum number of retries defined for any sort of error
    retries = 0

    analysis_prompt =  f"""
You are a highly skilled legal expert analyzing a contract. Your role is to provide detailed explanations of each clause to ensure the user fully understands their rights, obligations, and potential risks.

1. **Clause Identification**: Break down the contract into individual clauses. For each clause, provide a clear and detailed explanation in plain language, keeping legal accuracy.

2. **Highlight Critical Clauses**: Pay special attention to clauses that:
   - are tricky and might posses ambuigious implications.
   - Pose potential legal or financial risks (e.g., indemnity, liability, exclusivity, termination conditions).
   - May have long-term consequences (e.g., renewal, non-compete, intellectual property).
   - Could be subject to varying interpretations. 
   
   For these critical clauses:
   - Provide an in-depth explanation of their potential implications. making the user aware about it.
   - Highlight why they are important and what the user needs to be cautious about.

3. **General Clauses**: For clauses that are standard or non-critical, provide concise explanations. Merge similar clauses where appropriate and assure the user when no significant risk is involved.

5. **Plain Language**: Ensure that all explanations are written in simple, clear language. Avoid legal jargon unless necessary, and when it is necessary, provide explanations for the terminology used.

provide upto 4 max clauses (i.e 1-4) , that should encorporate this entire contract part. you can merge similar generic clauses together for this but explain clearly.

Never miss anything because everything matters. try to explain the clauses in detail like this (it's mentioned that you .........) so user can understand clearly what's mentioned in the contract.

Format as JSON array:
[
    {{
        "clause_title": "Title",
        "description": "Detailed explanation about the clause with accurate technicality.Your explanation should cover most of the points."
    }}
]
Provide only the JSON output and nothing else.

Here is the contract:
{contract_text}"""

    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model='Meta-Llama-3.1-70B-Instruct',
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            retries += 1
            if retries < max_retries:
                time.sleep(2)  # Wait before retrying
            else:
                st.error("Failed to analyze contract content after multiple retries.")
                return []
            
def summarize_contract_content(contract_text):
    max_retries = 20
    retries = 0

    summary_prompt = f"""
Analyze this contract section and identify ONLY the potentially risky, sneaky, or serious clauses that the user should be aware of. Focus on clauses that:

1. Have significant financial implications
2. Restrict future opportunities or actions
3. Create binding long-term commitments
4. Have unusual or potentially unfair terms
5. Contain hidden obligations or penalties

For each identified serious clause, provide:
1. A topic that clearly indicates what the clause is about
2. A clear 2-3 sentence description that explains both what the clause means and its practical implications in everyday language. Focus on what exactly is written in the contract and how it will affect the user.

Format as JSON array:
[
    {{
        "topic": "Clear topic of the clause",
        "description": "2-3 sentences explaining what the clause means and its implications in simple terms referencing to the user like this, you will not or you agree to or you will(if suitable)........"
    }}
]

Only include clauses that have significant implications. Skip standard, non-controversial clauses.
If no serious clauses are found, return an empty array.

Here is the contract section:
{contract_text}"""

    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model='Meta-Llama-3.1-70B-Instruct',
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            retries += 1
            if retries < max_retries:
                time.sleep(2)
            else:
                st.error("Failed to summarize contract content after multiple retries.")
                return []

def generate_email(clauses, responses):
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
2. Detail on which clauses are accepted (a small relevant explanation ).
3. Detail on which clauses are countered, and explain the counter proposal.
4. Detail on rejected clauses.
5. Next steps.

respond in a simple text format."""

    try:
        response = client.chat.completions.create(
            model='Meta-Llama-3.1-405B-Instruct',
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
    st.title("LegalLens")
    
    uploaded_file = st.file_uploader("Upload Contract (PDF)", type="pdf")
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Detailed Analysis"):
                st.session_state.analysis_mode = "detailed"
                st.session_state.processing_complete = False
                st.session_state.clauses = []
                st.rerun()
        with col2:
            if st.button("Quick Summary"):
                st.session_state.analysis_mode = "summary"
                st.session_state.processing_complete = False
                st.session_state.summary_clauses = []
                st.rerun()

        if st.session_state.analysis_mode and not st.session_state.processing_complete:
            with st.spinner("Analyzing your contract..." if st.session_state.analysis_mode == "detailed" else "Finding important clauses..."):
                images = convert_pdf_to_images(uploaded_file)
                batch_size = 5
                overlap = 1

                start = 0
                while start < len(images):
                    batch = images[start:start + batch_size]
                    if not batch:
                        break

                    contract_text = ""
                    for img in batch:
                        content = extract_contract_content(img)
                        if content:
                            contract_text += "\n" + content

                    if contract_text:

                        if st.session_state.analysis_mode == "detailed":
                            new_clauses = analyze_contract_content(contract_text)
                            existing_titles = [clause['clause_title'] for clause in st.session_state.clauses]
                            for new_clause in new_clauses:
                                if new_clause['clause_title'] not in existing_titles:
                                    st.session_state.clauses.append(new_clause)

                        else:  # summary mode
                            summary_clauses = summarize_contract_content(contract_text)
                            # Avoid duplicates based on descriptions
                            existing_descriptions = [clause['description'] for clause in st.session_state.summary_clauses]
                            for clause in summary_clauses:
                                if clause['description'] not in existing_descriptions:
                                    st.session_state.summary_clauses.append(clause)

                    start += batch_size - overlap

                st.session_state.processing_complete = True
                st.rerun()

    # Display results based on mode
    if st.session_state.processing_complete:
        if st.session_state.analysis_mode == "detailed":
            # [Previous detailed analysis display code remains the same]
            for idx, clause in enumerate(st.session_state.clauses):
                clause_id = str(hash(clause['clause_title']))
                
                st.markdown(f"### Clause {idx + 1}: {clause['clause_title']}")
                st.markdown(clause['description'])
                
                #crew analysis
                if clause_id not in st.session_state:
                    st.session_state[clause_id] = {}

                if 'implications' not in st.session_state[clause_id]:
                    with st.spinner("Analyzing implications..."):
                        analysis = manage_crew_for_clause(clause['description'])
                        st.session_state[clause_id]['implications'] = analysis.raw

                st.write(st.session_state[clause_id]['implications'])

                col1, col2 = st.columns([1, 2])
                with col1:
                    response_type = st.radio(
                        "Your Decision",
                        ["Accept", "Reject", "Counter"],
                        key=f"response_{clause_id}_{idx}",
                    )
                    update_response(clause_id, response_type)

                with col2:
                    if response_type == "Counter":
                        counter_text = st.text_area(
                            "Counter Proposal",
                            key=f"counter_{clause_id}_{idx}",
                            value=st.session_state['responses'].get(clause_id, {}).get('counter_text', '')
                        )
                        update_response(clause_id, response_type, counter_text)

                st.markdown("---")

            if st.button("Finalize Contract"):
                with st.spinner("Generating final response..."):
                    email = generate_email(st.session_state.clauses, st.session_state.responses)
                    st.session_state.generated_email = email
                    st.session_state.show_email = True

            if st.session_state.show_email and st.session_state.generated_email:
                st.markdown("### Generated Response Email")
                st.text_area("", st.session_state.generated_email, height=400)

        else:  # summary mode
            st.markdown("## Important Clauses to Review")
            if not st.session_state.summary_clauses:
                st.info("No potentially risky clauses found in this contract section.")
            else:
                for clause in st.session_state.summary_clauses:
                    st.markdown(f"### {clause['topic']}")
                    st.write(clause['description'])
                    st.markdown("---")

        if st.button("New Project / New Contract"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()

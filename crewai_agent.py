import streamlit as st
import os
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_community.llms import Ollama
import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image
import openai
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()


# Tools
search_tool = SerperDevTool()

api_key = os.environ.get("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"

# LLM and client Configuration

llm =LLM(
        model ="sambanova/Meta-Llama-3.1-70B-Instruct",
        api_key=api_key,
        base_url=base_url,
    )

client = openai.OpenAI(api_key=api_key,base_url=base_url)

# converting pdf to images
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

def analyze_page_with_vision(image_base64):
    """Analyze a single page using the vision model"""
    response = client.chat.completions.create(
        model='Llama-3.2-90B-Vision-Instruct',
        messages=[{
            "role": "user",
            "content": [{
                "type": "text",
                "text": "You are a contract analysis expert. Please carefully read this contract page and identify all important clauses and their implications. Provide a detailed explanation of each clause ."
            }, {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            }]
        }],
        temperature=0.1,
        top_p=0.1
    )
    return response.choices[0].message.content

# Agents Definition
def create_legal_analyzer_agent():
    return Agent(
        role="Legal Domain Analyst",
        goal="Verify if contract clauses are within legal boundaries",
        backstory="An expert legal researcher who thoroughly investigates the legal standing of contract clauses",
        tools=[search_tool],
        verbose=True,
        llm=llm
    )

def create_contract_reviewer_agent():
    return Agent(
        role="Contract Clause Reviewer",
        goal="Evaluate contract clauses for potential risks and advantages",
        backstory="A seasoned contract reviewer who provides comprehensive analysis of clause implications",
        tools=[search_tool],
        verbose=True,
        llm=llm
    )

def create_clause_analysis_tasks(legal_analyzer, reviewer, clause):
    """Create tasks for analyzing a specific clause"""
    legal_task = Task(
        description=f"Analyze the legal domain of the following contract clause: {clause}. Determine its legal standing and any potential legal issues.",
        expected_output="Comprehensive legal analysis of the clause, including its compliance with legal standards",
        agent=legal_analyzer
    )

    review_task = Task(
        description=f"Review the contract clause: {clause}. Assess its benefits, risks, and recommend potential counters or modifications.",
        expected_output="Detailed review with advantages, disadvantages, and recommended actions",
        agent=reviewer
    )

    return [legal_task, review_task]

def main():
    st.title("Advanced Contract Analysis with Multi-Agent System")
    
    # File upload
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        # Convert PDF to images
        images = convert_pdf_to_images(uploaded_file)
        
        # Initialize agents
        legal_analyzer = create_legal_analyzer_agent()
        contract_reviewer = create_contract_reviewer_agent()
        
        # Analysis results container
        analysis_results = []
        
        # Analyze each page
        for i, img in enumerate(images):
            st.subheader(f"Page {i+1} Analysis")
            
            # Vision-based clause extraction
            clauses = analyze_page_with_vision(img)
            st.markdown(clauses)
            # Analyze each clause
            page_analyses = []
            for clause in clauses.split('\n'):  # Assuming clauses are line-separated
                # Create crew for this specific clause
                tasks = create_clause_analysis_tasks(legal_analyzer, contract_reviewer, clause)
                
                crew = Crew(
                    agents=[legal_analyzer, contract_reviewer],
                    tasks=tasks,
                    process=Process.sequential
                )
                
                # Run analysis
                crew_result = crew.kickoff()
                
                page_analyses.append({
                    'clause': clause,
                    'legal_analysis': crew_result.split('\n')[0],  # First task result
                    'review_analysis': crew_result.split('\n')[1]  # Second task result
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

if __name__ == "__main__":
    main()
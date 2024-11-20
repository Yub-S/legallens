from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_community.llms import Ollama
import os
import json
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

# Tools
search_tool = SerperDevTool()

# LLM and client Configuration
api_key = os.environ.get("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"

llm = LLM(
    model="sambanova/Meta-Llama-3.1-70B-Instruct",
    api_key=api_key,
    base_url=base_url,
)

# Defining agents
legal_analyser_and_reviewer = Agent(
    role="Legal Domain Analyst and Contract Reviewer",
    goal="Verify if contract clauses are within legal boundaries and evaluate contract clauses for potential risks and implications",
    backstory="An expert legal researcher who thoroughly investigates the legal standing of contract clauses and provides comprehensive analysis of clause by compairing with standard clause and recommends counters to be made.",
    tools=[search_tool],
    verbose=True,
    llm=llm
)


def manage_crew_for_clause(clause):
    """Function to manage tasks and crew for each clause"""
    # defining tasks

    legal_analysis_and_review_task = Task(
        description=f"Analyze the legal domain of the following contract clause: {clause}. Determine its legal standing and any potential legal issues. Assess its benefits, risks, and recommend potential counters or modifications.",
        expected_output="Detailed explanation of legal analysis of the clause and recommended actions for counters or modifications in a single paragraph.",
        agent=legal_analyser_and_reviewer
    )


    # creating crew 
    crew = Crew(
        agents=[legal_analyser_and_reviewer],
        tasks=[legal_analysis_and_review_task],
        process=Process.sequential
    )

    crew_output = crew.kickoff()
    return crew_output

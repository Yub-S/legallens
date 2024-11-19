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
legal_analyzer = Agent(
    role="Legal Domain Analyst",
    goal="Verify if contract clauses are within legal boundaries",
    backstory="An expert legal researcher who thoroughly investigates the legal standing of contract clauses",
    tools=[search_tool],
    verbose=True,
    llm=llm
)

contract_reviewer = Agent(
    role="Contract Clause Reviewer",
    goal="Evaluate contract clauses for potential risks and advantages",
    backstory="A seasoned contract reviewer who provides comprehensive analysis of clause implications",
    tools=[search_tool],
    verbose=True,
    llm=llm
)

def manage_crew_for_clause(clause):
    """Function to manage tasks and crew for each clause"""
    # defining tasks

    legal_task = Task(
        description=f"Analyze the legal domain of the following contract clause: {clause}. Determine its legal standing and any potential legal issues.",
        expected_output="Comprehensive legal analysis of the clause, including its compliance with legal standards",
        agent=legal_analyzer
    )

    review_task = Task(
        description=f"Review the contract clause: {clause}. Assess its benefits, risks, and recommend potential counters or modifications.",
        expected_output="Detailed review with advantages, disadvantages, and recommended actions",
        agent=contract_reviewer
    )

    # creating crew 
    crew = Crew(
        agents=[legal_analyzer, contract_reviewer],
        tasks=[legal_task, review_task],
        process=Process.sequential
    )

    crew_output = crew.kickoff()
    return crew_output

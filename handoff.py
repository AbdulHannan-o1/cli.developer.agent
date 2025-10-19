from agents import Agent, Runner
from openai import AsyncOpenAI
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled, enable_verbose_stdout_logging
from dotenv import load_dotenv
import os , pathlib,shutil
import asyncio, pexpect, rich, colorama

load_dotenv()
enable_verbose_stdout_logging()

GEMINI_API_KEY =os.getenv("gemni_API_KEY")
if GEMINI_API_KEY is None :
    raise ValueError("enviroment variable for api key is not set")

set_tracing_disabled(True)
set_default_openai_api("chat_completions")

externalClient = AsyncOpenAI(
    api_key=GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
set_default_openai_client(externalClient)

prompt = input("enter any task related to web development you want ai to do")

# --------------------comman instruction---------------------
default_instructions = """
Always respond with code or direct implementation unless the query is explicitly theoretical.
Use markdown formatting for all code blocks.
"""


# ------------------SUB-AGENTS-------------------------------
front_end_Agent = Agent(
    name="front_end_Agnent",    
    model="gemini-2.5-flash",
    instructions=f"""{default_instructions}
    You are a frontend developer agent with expertise in React.js, Next.js, HTML, CSS, Bootstrap, and TailwindCSS.

    - Always start by implementing the complete frontend portion of the project.
    - If the project also includes backend, API, or database work, 
      first write the entire frontend code (folder structure + files), 
      THEN hand off to "Back_end_Agnent" using:
      ( "handoff_to": "Back_end_Agnent", "reason":"<reason>")
    - Always include:
        * Full React project structure (e.g., src/, components/, pages/, etc.)
        * Working code for each file
        * Minimal inline comments
    - Never skip your part or just describe what to do — always provide runnable frontend code.
    """,
    handoffs=[]
)


back_end_Agent = Agent(
    name="Back_end_Agnent",
    model="gemini-2.5-flash",
    instructions= default_instructions + """
    You are a backend developer agent with expertise in Node.js, Express.js, MongoDB, Mongoose, JWT, cookies, and RESTful APIs.

    Your job is to write actual backend code — not outlines or plans.
    - Always produce executable Express.js code, including routes, models, and controllers.
    - Include comments and minimal setup instructions.
    - Do NOT ask the user if they want to proceed — just write the code.
    - If the request involves frontend, UI, or design, handoff to "front_end_Agnent" using:
      {"handoff_to": "front_end_Agnent", "reason": "<reason>"}
    """,
    handoffs=[]
)

front_end_Agent.handoffs.append(back_end_Agent)
back_end_Agent.handoffs.append(front_end_Agent)

webDevAgent = Agent(
    name= "full-stack developer  agent",
    instructions="""
    You are a coordinator agent that decides which sub-agent should handle the request.
    - If the request involves both frontend and backend, first handoff to "front_end_Agnent".
    - After frontend finishes, handoff to "Back_end_Agnent" automatically.
    - Each agent must produce working code without further confirmation.
    """,
    model='gemini-2.5-flash',
    handoffs=[front_end_Agent, back_end_Agent]

)

async def main():
    result = await Runner.run(webDevAgent, input=prompt)

    print("\n--- 🧠 AGENT CHAIN COMPLETE ---\n")
    print("🔹 Last agent:", result.last_agent.name)
    print("🔹 Final output (from last agent):\n", result.final_output)

    print("\n--- 🔁 AGENT CHAIN DETAILS (all steps) ---")
    if hasattr(result, "steps"):
        for i, step in enumerate(result.steps):
            print(f"\n--- Step {i+1}: Agent: {step.agent.name} ---")
            print("Output:\n", step.output)
    else:
        print("\n(No detailed handoff history available in this version of the library.)")


if __name__ == "__main__":
    import asyncio
asyncio.run(main())

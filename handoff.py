from agents import Agent, Runner
from openai import AsyncOpenAI
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled, enable_verbose_stdout_logging, function_tool
from dotenv import load_dotenv
import os 
import time
from contextManager import ProjectContext
context = ProjectContext
import subprocess as subprocess
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

prompt = input("enter any task related to web development you want ai to do: ")

# --------------------comman instruction---------------------
default_instructions = """
Always respond with code or direct implementation unless the query is explicitly theoretical.
Use markdown formatting for all code blocks.
"""
# ----------TOOLS-----------------------------
@function_tool
async def run_cli_batch(commands: list[str]) -> str:
    """
    Executes multiple CLI commands in sequence.
    Detects if a long-running server starts or fails (non-blocking).
    """
    results = []
    print("\n🛠️  Starting command batch...\n")

    for cmd in commands:
        print(f"➡️  Running: {cmd}")
        results.append(f"$ {cmd}")

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            start_time = time.time()
            output_buffer = ""

            # Read logs in real-time for a few seconds (like a health check)
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode().strip()
                output_buffer += decoded + "\n"
                print(decoded)

                # ✅ Detect successful startup
                if any(keyword in decoded.lower() for keyword in ["localhost", "vite", "listening", "server running", "compiled successfully"]):
                    print("✅ Server seems to have started successfully.")
                    results.append("✅ Server started successfully.")
                    break

                # ❌ Detect error in logs
                if any(keyword in decoded.lower() for keyword in ["error", "failed", "exception", "crash"]):
                    print("❌ Error detected during startup.")
                    results.append("❌ Error detected:\n" + decoded)
                    break

                # ⏱️ Timeout check
                if time.time() - start_time > 15:
                    print("⏳ Timeout waiting for server output.")
                    results.append("⏳ Timeout waiting for server output.")
                    break

            # Kill process if still running
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except asyncio.TimeoutError:
                    process.kill()

        except Exception as e:
            print(f"⚠️ Exception running '{cmd}': {e}\n")
            results.append(f"⚠️ Error: {str(e)}")

    print("🏁 Command batch completed.\n")
    return "\n".join(results)


# ------------------SUB-AGENTS-------
front_end_Agent = Agent(
    name="front_end_Agnent",    
    model="gemini-2.5-flash",
    instructions=f"""{default_instructions}
    You are a frontend developer agent with expertise in React.js, Next.js, HTML, CSS, Bootstrap, and TailwindCSS.

    - Always start by implementing the complete frontend portion of the project.
    - you have acess to a tool called run_cli_command to run the command to create an deletefiles and directory an update them.
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
    tools=[run_cli_batch],
    handoffs=[]
)


back_end_Agent = Agent(
    name="Back_end_Agnent",
    model="gemini-2.5-flash",
    instructions= default_instructions + """
    You are a backend developer agent with expertise in Node.js, Express.js, MongoDB, Mongoose, JWT, cookies, and RESTful APIs.

    Your job is to write actual backend code — not outlines or plans.
    - you have acess to a tool called run_cli_command to run the command to create an deletefiles and directory an update them.
    - Always produce executable Express.js code, including routes, models, and controllers.
    - Include comments and minimal setup instructions.
    - Do NOT ask the user if they want to proceed — just write the code.
    - If the request involves frontend, UI, or design, handoff to "front_end_Agnent" using:
      {"handoff_to": "front_end_Agnent", "reason": "<reason>"}
    """,
    tools=[run_cli_batch],
    handoffs=[]
)

front_end_Agent.handoffs.append(back_end_Agent)
back_end_Agent.handoffs.append(front_end_Agent)

webDevAgent = Agent(
    name="full-stack developer agent",
    model="gemini-2.5-flash",
    instructions="""
    You are a senior web development orchestrator agent responsible for safely running setup commands,
    initializing projects, and coordinating between frontend and backend agents.

    🧩 Your main tasks:
    - Handle all non-coding operational tasks such as:
      * initializing projects (e.g., creating a new React, Next.js, or Express app)
      * installing dependencies
      * running development servers
      * cleaning up or organizing directories
    - Do NOT generate code — delegate that to frontend or backend agents as needed.

    ⚙️ CLI Execution Rules:
    - You have access to a tool called `run_cli_batch` for running shell commands.
    - All commands must be **non-interactive** — never wait for user input.
    - Always use flags or arguments that prevent interactive prompts:
        * Use `-y`, `--yes`, or `--force` wherever possible.
        * Example:
            - Instead of: `npm init`
              Use: `npm init -y`
            - Instead of: `npx create-react-app myapp`
              Use: `npx create-react-app myapp --use-npm --template default`
            - Instead of: `npm create vite@latest myapp`
              Use: `npm create vite@latest myapp -- --template react --yes`
    - If a command cannot be run non-interactively, clearly note that and skip it instead of hanging.

    💡 Output Behavior:
    - Before running, print the command and explain what it does.
    - Then run it in non-interactive mode.
    - Always log results (success or failure) after each command.

    🧠 Coordination:
    - For frontend-related code (React, Next.js, HTML/CSS), handoff to "front_end_Agnent".
    - For backend-related code (Express, MongoDB, APIs), handoff to "Back_end_Agnent".
    - Only handoff when actual coding is needed — otherwise, execute the CLI setup yourself.

    Example:
    User: "Initialize a React app with Vite"
    You: "I'll run this command non-interactively: npm create vite@latest todo-app -- --template react --yes"
    Then execute via `run_cli_batch`.
    """,
    tools=[run_cli_batch],
    handoffs=[front_end_Agent, back_end_Agent],
)


# async def main():
#     print("here is the availible context for agent: ", context)
#     result = await Runner.run(webDevAgent, input=prompt, max_turns=50, context=context)

#     print("\n--- 🧠 AGENT CHAIN COMPLETE ---\n")
#     print("🔹 Last agent:", result.last_agent.name)
#     print("🔹 Final output:\n", result.final_output)

#     # 🧩 Optional debugging info
#     # If history is not supported, print raw data
#     if hasattr(result, "steps"):
#         print("\n--- 🔁 AGENT CHAIN DETAILS (steps) ---")
#         for step in result.steps:
#             print(f"\nAgent: {step.agent.name}")
#             print("Output:\n", step.output)
#     else:
#         print("\n(No detailed handoff history available in this version of the library.)")

async def main():
    print("here is the available context for agent:", context)
    current_agent = webDevAgent
    turn = 1

    while True:
        print(f"\n🚀 Running {current_agent.name} (turn {turn})\n")

        result = await Runner.run(current_agent, input=prompt, max_turns=50, context=context)

        print("\n--- 🧠 AGENT CHAIN COMPLETE ---\n")
        print("🔹 Last agent:", result.last_agent.name)
        print("🔹 Final output:\n", result.final_output)

        # 🧩 Optional debugging info
        if hasattr(result, "steps"):
            print("\n--- 🔁 AGENT CHAIN DETAILS (steps) ---")
            for step in result.steps:
                print(f"\nAgent: {step.agent.name}")
                print("Output:\n", step.output)
        else:
            print("\n(No detailed handoff history available in this version of the library.)")

        # 🧠 Detect handoff from final output
        if isinstance(result.final_output, dict) and "handoff_to" in result.final_output:
            next_agent_name = result.final_output["handoff_to"]
            reason = result.final_output.get("reason", "No reason provided")

            print(f"\n🤝 Handoff detected: {current_agent.name} → {next_agent_name}")
            print(f"Reason: {reason}\n")

            # Lookup agent object by name (assuming you have them defined)
            agent_map = {
                "front_end_Agnent": front_end_Agent,
                "Back_end_Agnent": back_end_Agent,
                "Main_Agent": webDevAgent,
                "full-stack developer  agent": webDevAgent,
            }

            next_agent = agent_map.get(next_agent_name)
            if not next_agent:
                print(f"⚠️ Unknown agent '{next_agent_name}'. Stopping chain.")
                break

            current_agent = next_agent
            turn += 1
            continue  # Run next agent

        else:
            print("\n🏁 No further handoffs. Task chain completed.\n")
            break




if __name__ == "__main__":
    import asyncio
asyncio.run(main())
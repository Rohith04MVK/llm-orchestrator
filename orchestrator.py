import os
import subprocess
import json
import tempfile
import shutil
import uuid
import re
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
# Configure the Google AI client using the environment variable
try:
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=google_api_key)
    # --- OpenAI client initialization removed ---
    # client = OpenAI()
except ValueError as e:
    print(f"Configuration Error: {e}")
    # You might want to exit here if the key is essential
    # sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during Google AI configuration: {e}")
    # sys.exit(1)


# Map descriptive service names (from LLM) to actual Docker image names
SERVICE_TO_IMAGE_MAP = {
    "summarizer-service": "summarizer-app",
    "translator-service": "translator-app",
    # Add other services here
}

# --- Prompt remains largely the same, but ensure it strongly requests ONLY JSON ---
LLM_PROMPT_TEMPLATE = """
System Task:
You are a planning assistant. Analyze the user's request and determine the sequence of tools needed.
Respond ONLY with a valid JSON list containing the names of the tools in the correct order.
Do not include any other text, explanations, or markdown formatting (like ```json ... ```) around the JSON list.

Available Tools:
- 'summarizer-service': Creates a short summary of text.
- 'translator-service': Translates text to a specified language. Needs the target language (e.g., 'German', 'Spanish', 'French').

User Request: {user_request_text}

Your Plan (JSON list only):
"""

# --- Helper Functions ---

def get_llm_plan(user_request):
    """Calls the Google Generative AI LLM to get the execution plan."""
    print(f"\n[Orchestrator] Asking Google AI for plan for: '{user_request}'")

    if not google_api_key: # Check if configuration failed earlier
         print("[Orchestrator] Error: Google AI API Key not configured.")
         return None

    try:
        # --- Use Google Generative AI ---
        # Model Selection: gemini-1.5-flash is fast and capable, gemini-pro is also good.
        # Use gemini-1.5-pro if flash isn't sufficient or available.
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Configuration for generation - enforce JSON output
        generation_config = genai.GenerationConfig(
            temperature=0.0, # Deterministic planning
            response_mime_type="application/json" # Request JSON output directly
        )

        full_prompt = LLM_PROMPT_TEMPLATE.format(user_request_text=user_request)

        # Make the API call
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        # --- Parse Google AI Response ---
        # The response.text should contain the JSON string because of response_mime_type
        raw_json_response = response.text
        print(f"[Orchestrator] Google AI raw response text: {raw_json_response}")

        try:
            plan = json.loads(raw_json_response)
            # Basic validation: Check if it's a list of strings
            if isinstance(plan, list) and all(isinstance(item, str) for item in plan):
                 print(f"[Orchestrator] Google AI plan parsed: {plan}")
                 return plan
            else:
                 print("[Orchestrator] Error: LLM response is JSON but not a list of strings.")
                 return None
        except json.JSONDecodeError as json_err:
            print(f"[Orchestrator] Error: Failed to parse JSON from Google AI response. Error: {json_err}")
            print(f"Raw response was: {raw_json_response}")
            return None
        except Exception as e: # Catch other potential issues during parsing/validation
             print(f"[Orchestrator] Error processing Google AI response JSON: {e}")
             return None

    except Exception as e:
        # Catch errors during API call or model instantiation
        print(f"[Orchestrator] Error calling Google Generative AI: {e}")
        # You might want to inspect the specific exception type for more details
        # e.g., if it's an authentication error, permission error, etc.
        return None


def extract_language(user_request):
    """Simple language extraction (same as before)."""
    match = re.search(r'translate to (\w+)', user_request, re.IGNORECASE)
    lang_name = match.group(1).lower() if match else None
    lang_map = {"german": "de", "french": "fr", "spanish": "es", "japanese": "ja"} # Add more
    return lang_map.get(lang_name, "en")


def run_docker_task(image_name, host_data_dir, env_vars=None):
    """Runs a Docker container for a single task (same as before)."""
    container_name = f"{image_name}-{uuid.uuid4().hex[:8]}"
    # Ensure absolute path for volume mounting, especially robust on different OS
    abs_host_data_dir = os.path.abspath(host_data_dir)
    volume_mount = f"{abs_host_data_dir}:/data"
    command = ["docker", "run", "--rm", "--name", container_name, "-v", volume_mount]

    if env_vars:
        for key, value in env_vars.items():
            command.extend(["-e", f"{key}={value}"])

    command.append(image_name)

    print(f"\n[Orchestrator] Running container: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
        # Print stdout/stderr only if they contain content
        stdout_lines = result.stdout.strip().splitlines()
        stderr_lines = result.stderr.strip().splitlines()
        if stdout_lines:
             print(f"[Orchestrator] Container '{container_name}' stdout:")
             for line in stdout_lines: print(f"  > {line}")
        if stderr_lines:
             print(f"[Orchestrator] Container '{container_name}' stderr:")
             for line in stderr_lines: print(f"  > {line}")

        print(f"[Orchestrator] Container '{container_name}' completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Orchestrator] Error running container '{container_name}'. Return code: {e.returncode}")
        # Decode stderr/stdout if they are bytes
        stderr_output = e.stderr.strip() if e.stderr else "N/A"
        stdout_output = e.stdout.strip() if e.stdout else "N/A"
        print(f"Stderr:\n{stderr_output}")
        print(f"Stdout:\n{stdout_output}")
        return False
    except FileNotFoundError:
         print(f"[Orchestrator] Error: 'docker' command not found. Is Docker installed and in PATH?")
         return False
    except Exception as e:
        print(f"[Orchestrator] Unexpected error running container '{container_name}': {e}")
        return False

# --- Main Orchestration Logic (run_pipeline) ---
# This function remains the same as before, as it interacts with the results
# of get_llm_plan and run_docker_task, whose interfaces haven't changed.
# No modification needed here unless you change the function signatures above.

def run_pipeline(user_request, input_text):
    """Orchestrates the pipeline based on LLM plan."""

    # 1. Get plan from LLM
    plan = get_llm_plan(user_request)
    if not plan:
        print("[Orchestrator] Failed to get a valid plan from LLM.")
        return None, "Failed to get LLM plan."

    # Filter plan to only include known services
    valid_steps = [step for step in plan if step in SERVICE_TO_IMAGE_MAP]
    if not valid_steps:
        print("[Orchestrator] LLM plan contains no known services.")
        return None, "LLM plan had no actionable steps."
    if len(valid_steps) != len(plan):
        print(f"[Orchestrator] Warning: Some steps from LLM plan were ignored: {set(plan) - set(valid_steps)}")

    print(f"[Orchestrator] Executing plan: {valid_steps}")

    # 2. Prepare temporary directory for data exchange
    temp_dir = tempfile.mkdtemp(prefix="llm_orch_run_")
    print(f"[Orchestrator] Created temporary directory: {temp_dir}")

    current_input_file = os.path.join(temp_dir, "input.txt")
    current_output_file = os.path.join(temp_dir, "output.txt")

    try:
        # Write initial input
        with open(current_input_file, 'w', encoding='utf-8') as f:
            f.write(input_text)

        # 3. Execute steps in sequence
        for i, service_name in enumerate(valid_steps):
            print(f"\n[Orchestrator] --- Step {i+1}: {service_name} ---")
            image_name = SERVICE_TO_IMAGE_MAP[service_name]
            env_vars = {}

            # Special handling for services needing extra args
            if service_name == "translator-service":
                lang_code = extract_language(user_request)
                env_vars['TARGET_LANG'] = lang_code if lang_code else 'en' # Default to 'en'
                print(f"[Orchestrator] Setting TARGET_LANG={env_vars['TARGET_LANG']} for translator.")

            # Run the container
            success = run_docker_task(image_name, temp_dir, env_vars)

            if not success:
                error_detail = f"Pipeline failed at step {service_name}."
                # Try to read partial output for better error reporting
                try:
                    if os.path.exists(current_output_file):
                        with open(current_output_file, 'r', encoding='utf-8') as f_err:
                            last_output = f_err.read()
                        error_detail += f" Last output/error from container:\n{last_output}"
                except Exception as read_err:
                     error_detail += f" (Could not read output file: {read_err})"
                print(f"[Orchestrator] {error_detail}. Aborting pipeline.")
                return None, error_detail

            # Prepare for the next step (if any)
            if i < len(valid_steps) - 1:
                if os.path.exists(current_output_file):
                    os.rename(current_output_file, current_input_file)
                    print(f"[Orchestrator] Renamed output.txt to input.txt for next step.")
                else:
                    err_msg = f"Output file missing after step {service_name}. Aborting."
                    print(f"[Orchestrator] Error: {err_msg}")
                    return None, err_msg
            else:
                print("[Orchestrator] Final step completed.")

        # 4. Collect final output
        if os.path.exists(current_output_file):
            with open(current_output_file, 'r', encoding='utf-8') as f:
                final_result = f.read()
            print("[Orchestrator] Pipeline finished successfully.")
            return final_result, None # Return result, no error message
        else:
            err_msg = "Final output file is missing after last step."
            print(f"[Orchestrator] Error: {err_msg}")
            # This case might indicate an issue with the last container run,
            # though run_docker_task should ideally catch failures.
            return None, err_msg

    finally:
        # 5. Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            print(f"[Orchestrator] Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)
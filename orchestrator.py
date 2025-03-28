import os
import subprocess
import json
import tempfile
import shutil
import uuid
import re
import google.generativeai as genai
from dotenv import load_dotenv  # <--- Import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
try:
    # Now, os.getenv will read from the environment populated by load_dotenv
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not found in .env file or environment variables.")
    genai.configure(api_key=GOOGLE_API_KEY)
    print("[Orchestrator] LLM Engine configured successfully.")
except ValueError as e:
    print(f"[Orchestrator] Configuration Error: {e}")
    GOOGLE_API_KEY = None  # Ensure it's None if config fails
except Exception as e:
    print(
        f"[Orchestrator] An unexpected error occurred during LLM Engine configuration: {e}")
    GOOGLE_API_KEY = None

# Service information for orchestrator
SERVICE_INFO = {
    "summarizer-service":           {"image": "summarizer-app",          "needs_api_key": True, "description": "Generates a concise summary of the input text."},
    "translator-service":           {"image": "translator-app",          "needs_api_key": True, "description": "Translates text into a specified target language."},
    "anonymizer-service":           {"image": "anonymizer-app",          "needs_api_key": True, "description": "Attempts to identify and mask PII (names, dates, addresses, MRNs, etc.) in text."},
    "med-term-translator-service":  {"image": "med-term-translator-app", "needs_api_key": True, "description": "Attempts to simplify complex medical terms in text into layperson's language."},
}

LLM_PROMPT_TEMPLATE = """
System Task:
You are a planning assistant. Analyze the user's request and determine the sequence of tools needed from the list below.
Respond ONLY with a valid JSON list containing the names of the tools in the correct order.
Do not include any other text, explanations, or markdown formatting (like ```json ... ```) around the JSON list.

Available Tools:
- 'anonymizer-service': Attempts to identify and mask PII (names, dates, addresses, MRNs, etc.) in text using an LLM. Replace PII with placeholders like [NAME].
- 'med-term-translator-service': Attempts to simplify complex medical terms in text into layperson's language using an LLM.
- 'summarizer-service': Generates a concise summary of the input text using an LLM.
- 'translator-service': Translates text into a specified target language using an LLM. Needs the target language (e.g., 'German', 'Spanish', 'French', 'Japanese').

User Request: {user_request_text}

Your Plan (JSON list only):
"""


def get_llm_plan(user_request):
    print(f"\n[Orchestrator] Asking LLM Engine for plan for: '{user_request}'")
    if not GOOGLE_API_KEY:
        print("[Orchestrator] Error: LLM Engine API Key not configured (check .env).")
        return None
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json"
        )
        full_prompt = LLM_PROMPT_TEMPLATE.format(
            user_request_text=user_request)
        response = model.generate_content(
            full_prompt, generation_config=generation_config)
        raw_json_response = response.text
        print(
            f"[Orchestrator] LLM Engine raw response text: {raw_json_response}")
        plan = json.loads(raw_json_response)
        if isinstance(plan, list) and all(isinstance(item, str) for item in plan):
            print(f"[Orchestrator] LLM Engine plan parsed: {plan}")
            return plan
        else:
            print(
                "[Orchestrator] Error: LLM response is JSON but not a list of strings.")
            return None
    except json.JSONDecodeError as json_err:
        print(
            f"[Orchestrator] Error: Failed to parse JSON from LLM Engine response. Error: {json_err}")
        print(f"Raw response was: {raw_json_response}")
        return None
    except Exception as e:
        print(
            f"[Orchestrator] Error calling or processing Google Generative AI response: {e}")
        return None


def extract_language(user_request):
    match = re.search(r'translate to (\w+)', user_request, re.IGNORECASE)
    if not match:
        return 'en'  # Default
    lang_name = match.group(1).lower()
    lang_map = {"german": "de", "french": "fr",
                "spanish": "es", "japanese": "ja", "english": "en"}
    return lang_map.get(lang_name, 'en')  # Default to 'en' if name unknown


def run_docker_task(service_name, host_data_dir, env_vars=None):
    """Runs a Docker container, passing API key from host env (via dotenv) if needed."""
    if service_name not in SERVICE_INFO:
        print(
            f"[Orchestrator] Error: Unknown service '{service_name}'. Skipping.")
        return False

    service_details = SERVICE_INFO[service_name]
    image_name = service_details["image"]
    container_name = f"{image_name}-{uuid.uuid4().hex[:8]}"
    abs_host_data_dir = os.path.abspath(host_data_dir)
    volume_mount = f"{abs_host_data_dir}:/data"

    command = ["docker", "run", "--rm", "--name",
               container_name, "-v", volume_mount]

    # Prepare combined environment variables
    final_env_vars = env_vars.copy() if env_vars else {}

    # --- Check if service needs the key and if we have it ---
    if service_details["needs_api_key"]:
        # GOOGLE_API_KEY was loaded by load_dotenv() into the orchestrator's environment
        host_api_key = os.getenv("GOOGLE_API_KEY")  # Read it again here
        if host_api_key:
            # Add it to the dict that will be passed to the container
            final_env_vars["GOOGLE_API_KEY"] = host_api_key
            # No need to print the key itself here for security
            print(
                f"[Orchestrator] Preparing to pass GOOGLE_API_KEY to container '{container_name}'.")
        else:
            # This case should ideally be caught earlier, but as a safeguard
            print(
                f"[Orchestrator] Error: Service '{service_name}' needs API key, but GOOGLE_API_KEY is not loaded/found. Skipping container.")
            return False

    for key, value in final_env_vars.items():
        # Pass the variable using -e KEY=VALUE
        command.extend(["-e", f"{key}={value}"])

    command.append(image_name)  # Add image name at the end

    # Don't log full command with keys
    print(
        f"\n[Orchestrator] Running container command: docker run ... {image_name}")
    try:
        result = subprocess.run(
            command, check=True, text=True, capture_output=True, encoding='utf-8')
        # (stdout/stderr logging remains the same)
        stdout_lines = result.stdout.strip().splitlines()
        stderr_lines = result.stderr.strip().splitlines()
        if stdout_lines:
            print(f"[Orchestrator] Container '{container_name}' stdout:")
            for line in stdout_lines:
                print(f"  > {line}")
        if stderr_lines and not all('log messages before' in line for line in stderr_lines):
            print(f"[Orchestrator] Container '{container_name}' stderr:")
            for line in stderr_lines:
                print(f"  > {line}")
        print(
            f"[Orchestrator] Container '{container_name}' completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        # (Error handling remains the same)
        print(
            f"[Orchestrator] Error running container '{container_name}'. Return code: {e.returncode}")
        stderr_output = e.stderr.strip() if e.stderr else "N/A"
        stdout_output = e.stdout.strip() if e.stdout else "N/A"
        print(f"Stderr:\n{stderr_output}")
        print(f"Stdout:\n{stdout_output}")
        return False
    except FileNotFoundError:
        print(
            "[Orchestrator] Error: 'docker' command not found. Is Docker installed and in PATH?")
        return False
    except Exception as e:
        print(
            f"[Orchestrator] Unexpected error running container '{container_name}': {e}")
        return False


def run_pipeline(user_request, initial_input_content=None, initial_input_filepath=None):
    """Orchestrates the pipeline based on LLM plan, handles text or file input."""
    # Check if API key loaded correctly
    if not GOOGLE_API_KEY:
        return None, "LLM Engine API Key (GOOGLE_API_KEY) is not configured (check .env)."
    # Get plan from LLM
    plan = get_llm_plan(user_request)
    if not plan:
        return None, "Failed to get a valid plan from LLM."

    # Filter plan & validate steps
    valid_steps = [step for step in plan if step in SERVICE_INFO]
    if not valid_steps:
        return None, "LLM plan contains no known/actionable services."
    if len(valid_steps) != len(plan):
        ignored = set(plan) - set(valid_steps)
        print(
            f"[Orchestrator] Warning: Ignored unknown steps from LLM plan: {ignored}")

    print(f"[Orchestrator] Executing plan: {valid_steps}")

    # 2. Prepare temporary directory and initial input
    temp_dir = tempfile.mkdtemp(prefix="llm_orch_run_")
    print(f"[Orchestrator] Created temporary directory: {temp_dir}")

    current_input_file = os.path.join(
        temp_dir, "input.txt")  # Default input name
    current_output_file = os.path.join(temp_dir, "output.txt")
    is_first_step_pdf = valid_steps[0] == "pdf-reader-service"

    try:
        if is_first_step_pdf:
            if initial_input_filepath and os.path.exists(initial_input_filepath):
                pdf_input_in_container = os.path.join(temp_dir, "input.pdf")
                shutil.copyfile(initial_input_filepath, pdf_input_in_container)
                print(
                    f"[Orchestrator] Copied input PDF '{initial_input_filepath}' to '{pdf_input_in_container}' for pdf-reader-service.")
            else:
                raise ValueError(
                    "PDF Reader is the first step, but a valid input PDF file path was not provided.")
        elif initial_input_content:
            with open(current_input_file, 'w', encoding='utf-8') as f:
                f.write(initial_input_content)
            print(
                f"[Orchestrator] Wrote initial text content to '{current_input_file}'.")
        else:
            print("[Orchestrator] Warning: First step requires text input, but no initial content provided. Starting with empty input.")
            with open(current_input_file, 'w', encoding='utf-8') as f:
                f.write("")

        for i, service_name in enumerate(valid_steps):
            print(
                f"\n[Orchestrator] --- Step {i+1}/{len(valid_steps)}: {service_name} ---")

            if i > 0 or not is_first_step_pdf:
                if os.path.exists(current_output_file):
                    os.rename(current_output_file, current_input_file)
                    print(
                        f"[Orchestrator] Renamed previous output '{current_output_file}' to current input '{current_input_file}'.")
                elif i > 0:
                    raise FileNotFoundError(
                        f"Input file '{current_input_file}' missing for step {service_name}. Expected output from previous step.")

            step_env_vars = {}
            if service_name == "translator-service":
                lang_code = extract_language(user_request)
                step_env_vars['TARGET_LANG'] = lang_code
                print(
                    f"[Orchestrator] Setting TARGET_LANG={lang_code} for translator.")

            # Run the container using the updated function
            success = run_docker_task(service_name, temp_dir, step_env_vars)

            if not success:
                error_detail = f"Pipeline failed at step {service_name}."
                try:
                    if os.path.exists(current_output_file):
                        with open(current_output_file, 'r', encoding='utf-8') as f_err:
                            last_output = f_err.read(500)
                        error_detail += f" Last output/error from container:\n---\n{last_output}\n---"
                except Exception as read_err:
                    error_detail += f" (Could not read output file: {read_err})"
                print(f"[Orchestrator] {error_detail}. Aborting pipeline.")
                return None, error_detail

        if os.path.exists(current_output_file):
            with open(current_output_file, 'r', encoding='utf-8') as f:
                final_result = f.read()
            print("\n[Orchestrator] Pipeline finished successfully.")
            return final_result, None
        else:
            err_msg = "Final output file ('output.txt') is missing after the last step completion."
            if os.path.exists(current_input_file) and len(valid_steps) > 1:
                try:
                    with open(current_input_file, 'r', encoding='utf-8') as f_prev:
                        prev_output = f_prev.read(500)
                    err_msg += f"\nContent of input file for the failed last step:\n---\n{prev_output}\n---"
                except Exception:
                    pass
            print(f"[Orchestrator] Error: {err_msg}")
            return None, err_msg

    except Exception as pipeline_err:
        print(
            f"[Orchestrator] Pipeline execution failed with unexpected error: {pipeline_err}")
        return None, f"Pipeline failed: {pipeline_err}"

    finally:
        if temp_dir and os.path.exists(temp_dir):
            print(
                f"[Orchestrator] Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir, ignore_errors=True)

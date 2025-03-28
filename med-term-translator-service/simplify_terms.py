import os
import sys
import time
import google.generativeai as genai

print("Medical Term Simplifier Service starting...")

input_path = '/data/input.txt'
output_path = '/data/output.txt'

try:
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set inside container.")
    genai.configure(api_key=google_api_key)

    # Read input text
    with open(input_path, 'r', encoding='utf-8') as f_in:
        text_to_simplify = f_in.read()
        print(f"MedTerm Simplifier read {len(text_to_simplify)} characters.")

    if not text_to_simplify.strip():
        print("Input text is empty. Nothing to simplify.")
        simplified_text = ""
    else:
        # --- LLM Simplification Logic ---
        model = genai.GenerativeModel('gemini-1.5-flash')  # Or gemini-pro
        prompt = f"""Review the following text, which may contain complex medical terminology. Rewrite the text or add explanations in parentheses to make the medical terms understandable to a layperson (someone without a medical background). Focus on clarity and simplicity. Preserve the overall meaning and context. Output ONLY the simplified text, with no preamble or explanation.

        Text to Simplify:
        ---
        {text_to_simplify}
        ---

        Simplified Text:"""

        print("Calling LLM Engine to simplify medical terms...")
        response = model.generate_content(
            prompt, generation_config=genai.GenerationConfig(temperature=0.2))
        simplified_text = response.text
        # --- End LLM Logic ---

    # Simulate work
    time.sleep(1)

    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write(simplified_text)

    print("Medical Term Simplifier Service finished successfully.")

except Exception as e:
    print(f"Medical Term Simplifier Service Error: {e}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error during term simplification: {e}")
    except Exception as write_err:
        print(
            f"Additionally, failed to write error to output file: {write_err}")
    sys.exit(1)

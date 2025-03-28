import os
import sys
import time
import google.generativeai as genai

print("Anonymizer Service starting...")

input_path = '/data/input.txt'
output_path = '/data/output.txt'

try:
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set inside container.")
    genai.configure(api_key=google_api_key)

    # Read input text
    with open(input_path, 'r', encoding='utf-8') as f_in:
        text_to_anonymize = f_in.read()
        print(f"Anonymizer read {len(text_to_anonymize)} characters.")

    if not text_to_anonymize.strip():
         print("Input text is empty. Nothing to anonymize.")
         anonymized_text = ""
    else:
        # --- LLM Anonymization Logic ---
        model = genai.GenerativeModel('gemini-1.5-flash') # Or gemini-pro
        prompt = f"""VERY IMPORTANT: Identify and replace Personally Identifiable Information (PII) including names, specific dates (like birth dates, admission dates), addresses, phone numbers, email addresses, medical record numbers (MRN), social security numbers (SSN), or any other unique identifiers in the following text. Replace them with generic placeholders like [NAME], [DATE], [ADDRESS], [PHONE], [EMAIL], [MRN], [SSN], [IDENTIFIER]. Preserve the original structure and surrounding text. Output ONLY the fully anonymized text, with no preamble or explanation.

        Text to Anonymize:
        ---
        {text_to_anonymize}
        ---

        Anonymized Text:"""

        print("Calling LLM Engine to anonymize...")
        # No specific JSON format needed here, just text
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.1))
        anonymized_text = response.text
        # --- End LLM Logic ---

    # Simulate work
    time.sleep(1)

    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write(anonymized_text)

    print("Anonymizer Service finished successfully.")

except Exception as e:
    print(f"Anonymizer Service Error: {e}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error during anonymization: {e}")
    except Exception as write_err:
         print(f"Additionally, failed to write error to output file: {write_err}")
    sys.exit(1)
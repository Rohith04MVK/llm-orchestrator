import os
import sys
import time
from dotenv import load_dotenv
import google.generativeai as genai

print("Summarizer Service (using LLM) starting...")

input_path = '/data/input.txt'
output_path = '/data/output.txt'

try:
    load_dotenv()
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set inside container.")
    genai.configure(api_key=google_api_key)

    # Read input text
    with open(input_path, 'r', encoding='utf-8') as f_in:
        text_to_summarize = f_in.read()
        print(f"Summarizer read {len(text_to_summarize)} characters.")

    if not text_to_summarize.strip():
         print("Input text is empty. Nothing to summarize.")
         summary = ""
    else:
        # --- LLM Summarization Logic ---
        model = genai.GenerativeModel('gemini-2.0-flash') # Or gemini-pro
        prompt = f"""Generate a concise summary of the following text. Focus on the main points and key information. Output ONLY the summary text, with no preamble.

        Text to Summarize:
        ---
        {text_to_summarize}
        ---

        Summary:"""

        print("Calling LLM Engine to summarize...")
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=1))
        summary = response.text
        # --- End LLM Logic ---

    # Simulate work
    time.sleep(1)

    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write(summary)

    print("Summarizer Service finished successfully.")

except Exception as e:
    print(f"Summarizer Service Error: {e}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f_err:
            f_err.write(f"Error during summarization: {e}")
    except Exception as write_err:
         print(f"Additionally, failed to write error to output file: {write_err}")
    sys.exit(1)
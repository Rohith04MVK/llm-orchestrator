import os
import sys
import time
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai

print("Translator Service (using LLM) starting...")

input_path = '/data/input.txt'
output_path = '/data/output.txt'
# Get target language from environment variable (set by orchestrator)
target_lang_code = os.environ.get('TARGET_LANG', 'en') # Default to English
# Map code to full name for better prompt clarity (optional but good)
lang_name_map = {"de": "German", "fr": "French", "es": "Spanish", "ja": "Japanese", "en": "English"}
target_lang_name = lang_name_map.get(target_lang_code, target_lang_code) # Use code if name not found

try:
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set inside container.")
    genai.configure(api_key=google_api_key)

    # Read input text
    with open(input_path, 'r', encoding='utf-8') as f_in:
        text_to_translate = f_in.read()
        print(f"Translator read {len(text_to_translate)} chars. Target: {target_lang_name} ({target_lang_code})")

    if not text_to_translate.strip():
         print("Input text is empty. Nothing to translate.")
         translation = ""
    else:
        # --- LLM Translation Logic ---
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""Translate the following text accurately into {target_lang_name}. Preserve the meaning and tone. Output ONLY the translated text, with no preamble or explanation.

        Text to Translate:
        ---
        {text_to_translate}
        ---

        Translated Text ({target_lang_name}):"""

        print(f"Calling Google AI to translate to {target_lang_name}...")
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(temperature=0.2))
        translation = response.text
        # --- End LLM Logic ---

    # Simulate work
    time.sleep(1)

    with open(output_path, 'w', encoding='utf-8') as f_out:
        f_out.write(translation)

    print("Translator Service finished successfully.")

except Exception as e:
    print(f"Translator Service Error: {e}")
    try:
        with open(output_path, 'w', encoding='utf-8') as f_err:
             f_err.write(f"Error during translation: {e}")
    except Exception as write_err:
         print(f"Additionally, failed to write error to output file: {write_err}")
    sys.exit(1)
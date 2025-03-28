import sys
from orchestrator import run_pipeline

if __name__ == "__main__":
    # --- Get User Input ---
    print("="*40)
    print(" LLM Container Orchestrator ")
    print("="*40)

    task_description = input(
        "Enter your request (e.g., 'Summarize this and translate to German'): ")

    print("\nEnter the text content below. Press Ctrl+D (Linux/macOS) or Ctrl+Z then Enter (Windows) when done:")
    print("-"*40)
    input_text = sys.stdin.read()
    print("-"*40)

    if not task_description or not input_text:
        print("Error: Both task description and text content are required.")
        sys.exit(1)

    # --- Run the Pipeline ---
    print("\n[Main] Starting orchestration pipeline...")
    final_output, error_message = run_pipeline(task_description, input_text)

    # --- Display Result ---
    print("\n" + "="*40)
    if error_message:
        print(" Pipeline Execution Failed ")
        print("="*40)
        print(f"Error: {error_message}")
    elif final_output is not None:
        print(" Pipeline Execution Succeeded ")
        print("="*40)
        print("Final Output:")
        print(final_output)
    else:
        # Should ideally be covered by error_message, but as a fallback
        print(" Pipeline Execution Status Unknown ")
        print("="*40)
        print("An unexpected issue occurred. Check orchestrator logs.")
    print("="*40)

import sys
import re

try:
    with open("src/backend/deterministic_flow.py", "r") as f:
        text = f.read()

    # Find all print statements that look like print(f"\n... ") and append flush=True
    # Examples: print(f"\n🔐 [IDENTITY SERVICE]...")
    
    # We use a regex that looks for print(  followed by a string that starts with \n or f"\n, without flush=True
    
    # Replace print(f"\n...") with print(f"\n...", flush=True) but only if it's not already flushed
    text = re.sub(r'print\((f\"\\n[^\"]+\")\)', r'print(\1, flush=True)', text)
    text = re.sub(r'print\((f\'\\n[^\']+\')\)', r'print(\1, flush=True)', text)
    text = re.sub(r'print\((\"\\n[^\"]+\")\)', r'print(\1, flush=True)', text)
    
    with open("src/backend/deterministic_flow.py", "w") as f:
        f.write(text)
        
    print("Successfully added flush=True to simulated server prints.")
except Exception as e:
    print(f"Error: {e}")


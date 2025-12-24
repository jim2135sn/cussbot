"""
Cussbot Remote Loader
Fetches the latest bot code and responses from GitHub and runs it.
"""

import urllib.request
import sys
import os

BOT_CODE_URL = "https://raw.githubusercontent.com/jim2135sn/cussbot/main/cussbot.py?v=2"
RESPONSES_URL = "https://raw.githubusercontent.com/jim2135sn/cussbot/main/responses.json?v=2"

def update_responses():
    """Download latest responses.json from GitHub"""
    print("Updating responses.json from GitHub...")
    try:
        with urllib.request.urlopen(RESPONSES_URL, timeout=30) as response:
            data = response.read()
        with open("responses.json", "wb") as f:
            f.write(data)
        print(f"Updated responses.json ({len(data)} bytes)")
    except Exception as e:
        print(f"Warning: Could not update responses.json: {e}")

def fetch_and_run():
    print("=" * 50)
    print("Cussbot Remote Loader")
    print("=" * 50)
    print()
    
    update_responses()
    print()
    
    print("Fetching latest bot code from GitHub...")
    
    try:
        with urllib.request.urlopen(BOT_CODE_URL, timeout=30) as response:
            bot_code = response.read().decode('utf-8')
        
        print(f"Successfully fetched {len(bot_code)} bytes of code")
        print()
        print("Starting bot...")
        print("-" * 50)
        exec(bot_code, {'__name__': '__main__'})
        
    except urllib.error.URLError as e:
        print(f"Error: Could not fetch bot code from server!")
        print(f"Reason: {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")
    fetch_and_run()

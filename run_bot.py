"""
Cussbot Remote Loader
Fetches the latest bot code and responses from GitHub and runs it.
Self-updates if a new version is available.
"""

import urllib.request
import sys
import os

BOT_CODE_URL = "https://raw.githubusercontent.com/jim2135sn/cussbot/main/cussbot.py?v=2"
RESPONSES_URL = "https://raw.githubusercontent.com/jim2135sn/cussbot/main/responses.json?v=2"
SELF_URL = "https://raw.githubusercontent.com/jim2135sn/cussbot/main/run_bot.py?v=2"

def self_update():
    print("Checking for run_bot.py updates...")
    try:
        with urllib.request.urlopen(SELF_URL, timeout=30) as response:
            remote_code = response.read().decode('utf-8')
        
        script_path = os.path.abspath(__file__)
        with open(script_path, 'r', encoding='utf-8') as f:
            local_code = f.read()
        
        if remote_code.strip() != local_code.strip():
            print("New version found! Updating run_bot.py...")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(remote_code)
            print("Updated! Restarting...")
            os.execv(sys.executable, [sys.executable, script_path])
        else:
            print("run_bot.py is up to date.")
    except Exception as e:
        print(f"Could not check for updates: {e}")

def update_responses():
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
    
    self_update()
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

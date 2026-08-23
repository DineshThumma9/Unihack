import sys
import os
import requests
import subprocess
import time

def main():
    print("Starting uvicorn server in background...")
    proc = subprocess.Popen(["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"], cwd="backend/src", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    
    print("Testing /")
    try:
        r = requests.get("http://localhost:8000/")
        print("Status code:", r.status_code)
        print("Headers:", r.headers)
        print("Content length:", len(r.text))
    except Exception as e:
        print("Error:", e)
        
    proc.terminate()

if __name__ == "__main__":
    main()

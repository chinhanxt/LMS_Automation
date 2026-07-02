import sys
import os
import time

sys.path.append("/home/chinhan/Documents/lms")
from chrome_automation import ChromeAutomation

def main():
    print("Initializing ChromeAutomation on port 9333...")
    auto = ChromeAutomation("9333")
    
    url = "mock_quiz.html"
    print(f"Finding tab matching: {url}")
    tab = auto.find_matching_tab(url)
    if not tab:
        print("Error: Could not find matching tab. Make sure Chrome is open at the URL.")
        return
        
    print(f"Connected to tab: {tab.get('title')} ({tab.get('url')})")
    
    # We will solve 20 questions
    total = 20
    
    for i in range(1, total + 1):
        print(f"\n--- Processing Question {i} ---")
        
        # We loop to retry if we hit waiting_navigation
        max_attempts = 10
        scanned = None
        
        for attempt in range(max_attempts):
            print(f"Attempting to scan question {i} (attempt {attempt + 1})...")
            scanned = auto.scan_question(tab, i)
            if scanned and scanned.get("success"):
                if scanned.get("status") == "waiting_navigation":
                    print(f"Scan returned waiting_navigation (maybe clicked start/next). Sleeping...")
                    time.sleep(1.0)
                    continue
                else:
                    break
            else:
                print(f"Scan failed: {scanned.get('error') if scanned else 'None'}. Retrying...")
                time.sleep(1.0)
                
        if not scanned or not scanned.get("success") or scanned.get("status") == "waiting_navigation":
            print(f"Error: Failed to scan question {i} after {max_attempts} attempts.")
            return
            
        q_text = scanned.get("questionText")
        options = scanned.get("options", [])
        print(f"Question: {q_text}")
        print("Options:")
        for opt in options:
            print(f"  {opt['index']}: {opt['text']}")
            
        if not options:
            print("Error: No options found.")
            return
            
        # Select first option (A) or option 0
        opt_idx = 0
        print(f"Choosing option {opt_idx} for question {i}...")
        
        # Click the option
        click_res = auto.click_option(tab, i, opt_idx)
        print(f"Click option result: {click_res}")
        if not click_res or not click_res.get("success"):
            print("Error: Click option failed.")
            return
            
        # Since click_option will auto-advance, let's wait a bit for navigation
        time.sleep(1.2)
        
    print("\n[SUCCESS] Successfully solved and advanced through all 20 questions!")

if __name__ == "__main__":
    main()

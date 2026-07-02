import sys
import time
import json
import requests
import websocket

sys.path.append('/home/chinhan/Documents/lms')
from chrome_automation import ChromeAutomation

auto = ChromeAutomation("9222")
tabs = auto.get_tabs()
page_tabs = [t for t in tabs if t.get("type") == "page"]
if not page_tabs:
    print("Error: No page tabs open in Chrome.")
    sys.exit(1)

tab = page_tabs[0]
print(f"Connecting to tab: {tab.get('title')}")

# Navigate to localhost:3001
ws_url = tab.get("webSocketDebuggerUrl")
ws = websocket.create_connection(ws_url, timeout=10, suppress_origin=True)
try:
    print("Navigating to http://localhost:3001 ...")
    ws.send(json.dumps({
        "id": 100,
        "method": "Page.navigate",
        "params": {"url": "http://localhost:3001"}
    }))
    time.sleep(3.0)

    # Let's inspect the page content to make sure it loaded
    check_loaded_js = "document.title"
    res = auto.execute_js_on_tab(tab, check_loaded_js)
    print(f"Page title is: {res}")

    if "LMS Video Lock" in res:
        print("[✔] Mock LMS Video Lock Page successfully loaded!")
    else:
        print("[❌] Failed to load Mock LMS Page.")
        sys.exit(1)

    # Play the video
    print("Triggering video playback...")
    play_js = "var v = document.querySelector('video'); if (v) { v.muted = true; v.play(); }; 'Playing started';"
    res = auto.execute_js_on_tab(tab, play_js)
    print("JS Play command result:", res)

    # Wait 4 seconds for playback stats to accumulate
    print("Waiting 4 seconds to accumulate stats...")
    time.sleep(4.0)

    # Query the stats from the DOM
    query_stats_js = """
    (function() {
        var acc = document.getElementById('stat-accumulated').innerText;
        var wall = document.getElementById('stat-wall-clock').innerText;
        var status = document.getElementById('stat-status').innerText;
        return {
            accumulated: acc,
            wallClock: wall,
            status: status
        };
    })()
    """
    stats = auto.execute_js_on_tab(tab, query_stats_js)
    print("Stats after 4 seconds:", stats)

    # Check if the stats updated
    acc_val = float(stats['accumulated'].replace('s', ''))
    if acc_val > 0:
        print(f"[✔] Success: Stats are accumulating! Current watch time: {acc_val} seconds.")
    else:
        print("[❌] Error: Watch time is not accumulating. Check if the video is playing.")

finally:
    ws.close()

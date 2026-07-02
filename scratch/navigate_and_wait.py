import json
import time
import websocket
from chrome_automation import ChromeAutomation

auto = ChromeAutomation("9333")
tabs = auto.get_tabs()
page_tabs = [t for t in tabs if t.get("type") == "page"]
if not page_tabs:
    print("No page tabs found!")
    exit(1)

tab = page_tabs[0]
ws_url = tab.get("webSocketDebuggerUrl")
print("Connecting to:", ws_url)
ws = websocket.create_connection(ws_url, timeout=10)

# Enable Page
ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
print("Page.enable response:", ws.recv())

# Enable Network
ws.send(json.dumps({"id": 2, "method": "Network.enable"}))
print("Network.enable response:", ws.recv())

# Page.navigate
print("Navigating to http://127.0.0.1:3001/mock_quiz.html...")
ws.send(json.dumps({
    "id": 3,
    "method": "Page.navigate",
    "params": {"url": "http://127.0.0.1:3001/mock_quiz.html"}
}))

# Listen to events for 5 seconds
start_time = time.time()
ws.settimeout(1.0)
while time.time() - start_time < 5.0:
    try:
        msg = ws.recv()
        data = json.loads(msg)
        method = data.get("method")
        if method:
            print(f"[Event] {method}: {list(data.get('params', {}).keys())}")
        else:
            print(f"[Response] id={data.get('id')}: {data.get('result')}")
    except websocket.WebSocketTimeoutException:
        pass
    except Exception as e:
        print("Error:", e)
        break

ws.close()

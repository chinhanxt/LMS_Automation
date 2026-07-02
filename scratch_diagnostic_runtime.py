import json
import websocket
from chrome_automation import ChromeAutomation

auto = ChromeAutomation("9333")
tab = auto.get_tabs()[0]
ws_url = tab.get("webSocketDebuggerUrl")
print("Connecting...")
ws = websocket.create_connection(ws_url, timeout=3)
print("Connected!")
payload = {
    "id": 9999,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "1+1",
        "returnByValue": True
    }
}
print("Sending Runtime.evaluate...")
ws.send(json.dumps(payload))
try:
    print("Received:", ws.recv())
except Exception as e:
    print("Error:", e)
ws.close()

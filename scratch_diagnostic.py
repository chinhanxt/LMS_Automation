import json
import websocket
from chrome_automation import ChromeAutomation

auto = ChromeAutomation("9333")
tab = auto.get_tabs()[0]
print("Tab:", tab)

ws_url = tab.get("webSocketDebuggerUrl")
print("Connecting to ws_url:", ws_url)
ws = websocket.create_connection(ws_url, timeout=3)
print("Connected!")
print("Sending Page.enable...")
ws.send(json.dumps({"id": 10001, "method": "Page.enable"}))
ws.settimeout(3.0)
try:
    while True:
        res = json.loads(ws.recv())
        print("Received:", res)
        if res.get("id") == 10001:
            break
except Exception as e:
    print("Error receiving Page.enable response:", e)

print("Closing...")
ws.close()

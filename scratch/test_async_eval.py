import json
import requests
import websocket

port = "9222"
json_url = f"http://localhost:{port}/json"

try:
    resp = requests.get(json_url, timeout=2)
    if resp.status_code == 200:
        tabs = resp.json()
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if page_tabs:
            target_tab = page_tabs[0]
            ws_url = target_tab.get("webSocketDebuggerUrl")
            ws = websocket.create_connection(ws_url, timeout=4)
            try:
                ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
                
                # Test async evaluation
                js_code = """
                (async function() {
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            resolve({ success: true, message: "Hello from the future!" });
                        }, 1000);
                    });
                })()
                """
                
                ws.send(json.dumps({
                    "id": 99,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_code,
                        "returnByValue": True,
                        "awaitPromise": True
                    }
                }))
                
                ws.settimeout(5.0)
                while True:
                    res = json.loads(ws.recv())
                    if res.get("id") == 99:
                        print("Result:", res)
                        break
            finally:
                ws.close()
except Exception as e:
    print("Error:", e)

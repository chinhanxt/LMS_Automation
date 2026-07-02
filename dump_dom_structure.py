import json
import requests
import websocket

port = "9222"
json_url = f"http://localhost:{port}/json"

try:
    resp = requests.get(json_url, timeout=2)
    if resp.status_code == 200:
        tabs = resp.json()
        page_tabs = [t for t in tabs if t.get("type") == "page" and "lms" in t.get("url", "").lower()]
        if page_tabs:
            target_tab = page_tabs[0]
            ws_url = target_tab.get("webSocketDebuggerUrl")
            ws = websocket.create_connection(ws_url, timeout=4)
            try:
                ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
                
                # Fetch contexts
                contexts = []
                ws.settimeout(0.5)
                try:
                    while True:
                        msg = json.loads(ws.recv())
                        if msg.get("method") == "Runtime.executionContextCreated":
                            ctx = msg["params"]["context"]
                            contexts.append((ctx["id"], ctx.get("origin", "")))
                except websocket.WebSocketTimeoutException:
                    pass
                
                lms_ctx = [c[0] for c in contexts if "lms.hutech.edu.vn" in c[1]]
                if lms_ctx:
                    ctx_id = lms_ctx[0]
                    print(f"Targeting context {ctx_id}")
                    
                    test_js = """
                    (function() {
                        let cg = document.querySelector('.choicegroup');
                        if (!cg) return "No .choicegroup found";
                        
                        let parent = cg.parentElement;
                        let grandparent = parent ? parent.parentElement : null;
                        let ggp = grandparent ? grandparent.parentElement : null;
                        
                        return {
                            cg_html: cg.outerHTML.slice(0, 500),
                            parent_html: parent ? parent.outerHTML.slice(0, 500) : "None",
                            grandparent_html: grandparent ? grandparent.outerHTML.slice(0, 800) : "None",
                            ggp_html: ggp ? ggp.outerHTML.slice(0, 1000) : "None"
                        };
                    })()
                    """
                    
                    ws.send(json.dumps({
                        "id": 2,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": test_js,
                            "returnByValue": True,
                            "contextId": ctx_id
                        }
                    }))
                    
                    ws.settimeout(3.0)
                    while True:
                        res = json.loads(ws.recv())
                        if res.get("id") == 2:
                            val = res.get("result", {}).get("result", {}).get("value")
                            print(json.dumps(val, indent=2, ensure_ascii=False))
                            break
            finally:
                ws.close()
except Exception as e:
    print("Error:", e)

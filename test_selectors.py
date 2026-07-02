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
        if not page_tabs:
            page_tabs = [t for t in tabs if t.get("type") == "page"]
            
        if page_tabs:
            target_tab = page_tabs[0]
            print(f"Connecting to: {target_tab.get('title')}")
            
            ws_url = target_tab.get("webSocketDebuggerUrl")
            ws = websocket.create_connection(ws_url, timeout=4)
            try:
                ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
                
                # Fetch all execution contexts
                contexts = []
                ws.settimeout(0.5)
                try:
                    while True:
                        msg = json.loads(ws.recv())
                        if msg.get("method") == "Runtime.executionContextCreated":
                            ctx = msg["params"]["context"]
                            contexts.append((ctx["id"], ctx.get("name", ""), ctx.get("origin", "")))
                except websocket.WebSocketTimeoutException:
                    pass
                
                print(f"Found contexts: {contexts}")
                
                # Test selectors in each context
                for ctx_id, name, origin in contexts:
                    print(f"\n--- Testing in Context {ctx_id} ({name} | {origin}) ---")
                    
                    test_js = """
                    (function() {
                        let results = {};
                        let selectors = ['.que', '.question', '.problem', '.quiz-question', '.question-card', '.form-group', '.question_holder', '.problem-wrapper', 'fieldset', '.vert'];
                        selectors.forEach(s => {
                            let elms = document.querySelectorAll(s);
                            results[s] = elms.length;
                        });
                        
                        // Check inputs count
                        let inputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"]');
                        results['inputs_count'] = inputs.length;
                        
                        // Check for any forms
                        let forms = document.querySelectorAll('form');
                        results['forms_count'] = forms.length;
                        
                        return results;
                    })()
                    """
                    
                    try:
                        ws.send(json.dumps({
                            "id": 1000 + ctx_id,
                            "method": "Runtime.evaluate",
                            "params": {
                                "expression": test_js,
                                "returnByValue": True,
                                "contextId": ctx_id
                            }
                        }))
                        
                        # wait for reply
                        ws.settimeout(2.0)
                        while True:
                            res = json.loads(ws.recv())
                            if res.get("id") == 1000 + ctx_id:
                                val = res.get("result", {}).get("result", {}).get("value")
                                print("Result:", val)
                                break
                    except Exception as e:
                        print(f"Error in context {ctx_id}:", e)
            finally:
                ws.close()
except Exception as e:
    print("Error:", e)

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
                
                ctx_id = contexts[0][0] if contexts else 1
                print(f"Using context {ctx_id}")
                
                test_js = """
                (function() {
                    function getOptions(el) {
                        let inputs = Array.from(el.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]'));
                        if (inputs.length > 0) return inputs;
                        
                        let customTags = Array.from(el.querySelectorAll('mat-radio-button, mat-checkbox, ion-radio, ion-checkbox, el-radio, el-checkbox, ui-radio, ui-checkbox'));
                        if (customTags.length > 0) return customTags;

                        let custom = Array.from(el.querySelectorAll('.quiz-choice-item, .choice-item, .answer-item, .option-item, .choice, .option, .answer'));
                        if (custom.length > 0) {
                            custom = custom.filter(item => {
                                let hasOuter = custom.some(other => other !== item && other.contains(item));
                                return !hasOuter;
                            });
                            if (custom.length >= 2) return custom;
                        }
                        return [];
                    }

                    function deduplicateContainers(containers) {
                        return containers.filter(el => {
                            let opts = getOptions(el);
                            if (opts.length === 0) return false;
                            
                            let hasNestedSubQuestion = containers.some(other => {
                                if (other === el) return false;
                                if (!el.contains(other)) return false;
                                let otherOpts = getOptions(other);
                                return otherOpts.length > 0 && otherOpts.length < opts.length;
                            });
                            if (hasNestedSubQuestion) return false;
                            
                            let hasLargerWrapper = containers.some(other => {
                                if (other === el) return false;
                                if (!other.contains(el)) return false;
                                let otherOpts = getOptions(other);
                                return otherOpts.length === opts.length;
                            });
                            if (hasLargerWrapper) return false;
                            
                            return true;
                        });
                    }

                    function findQuestionContainers() {
                        let candidates = [];
                        let selectors = ['.que', '.question', '.quiz-question', '.question-card'];
                        selectors.forEach(s => {
                            try {
                                document.querySelectorAll(s).forEach(el => {
                                    if (!candidates.includes(el)) candidates.push(el);
                                });
                            } catch(e) {}
                        });
                        
                        let specificFiltered = candidates.filter(el => {
                            let opts = getOptions(el);
                            return opts.length >= 2 && opts.length <= 20;
                        });
                        specificFiltered = deduplicateContainers(specificFiltered);
                        
                        let genericElms = document.querySelectorAll('div, section, fieldset, form, tr, li, td');
                        let genericFiltered = Array.from(genericElms).filter(el => {
                            let opts = getOptions(el);
                            return opts.length >= 2 && opts.length <= 20;
                        });
                        genericFiltered = deduplicateContainers(genericFiltered);
                        
                        if (genericFiltered.length > specificFiltered.length) {
                            return genericFiltered;
                        }
                        return specificFiltered.length > 0 ? specificFiltered : genericFiltered;
                    }

                    let questionContainers = findQuestionContainers();
                    
                    // Let's return details of found containers
                    return questionContainers.map((el, idx) => {
                        let opts = getOptions(el);
                        // Try to find question text
                        let text = el.textContent.trim().substring(0, 100);
                        return {
                            index: idx + 1,
                            tagName: el.tagName,
                            className: el.className,
                            optionsCount: opts.length,
                            textSample: text
                        };
                    });
                })()
                """
                
                ws.send(json.dumps({
                    "id": 42,
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
                    if res.get("id") == 42:
                        val = res.get("result", {}).get("result", {}).get("value")
                        print(f"Found {len(val) if val else 0} question containers:")
                        for item in val:
                            print(f"Q{item['index']}: Tag={item['tagName']}, Class={item['className']}, Options={item['optionsCount']}, Text='{item['textSample']}'")
                        break
            finally:
                ws.close()
except Exception as e:
    print("Error:", e)

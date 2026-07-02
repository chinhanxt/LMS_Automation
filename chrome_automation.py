# -*- coding: utf-8 -*-
import json
import requests
import websocket
from urllib.parse import urlparse
from config_manager import load_selectors_config

class ChromeAutomation:
    def __init__(self, debug_port="9222"):
        self.debug_port = debug_port
        self._injected_tabs = set()


    def get_tabs(self):
        json_url = f"http://127.0.0.1:{self.debug_port}/json"
        try:
            resp = requests.get(json_url, timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def get_active_tab(self):
        tabs = self.get_tabs()
        if not tabs:
            return None
        
        page_tabs = [t for t in tabs if t.get("type") == "page"]
        if not page_tabs:
            return None
            
        for tab in page_tabs:
            try:
                # Check if the page is visible / active
                is_visible = self.execute_js_on_tab(tab, "document.visibilityState === 'visible'")
                if is_visible is True:
                    return tab
            except Exception:
                pass
                
        # If no active tab is found (e.g. browser minimized), return the first tab as default fallback
        return page_tabs[0]

    def find_matching_tab(self, target_url):
        tabs = self.get_tabs()
        if not tabs:
            return None

        # If target_url is empty, just return the active tab!
        if not target_url or not target_url.strip():
            active_tab = self.get_active_tab()
            if active_tab:
                return active_tab

        # Try exact matching or inclusion matching
        matching_tabs = []
        for tab in tabs:
            if tab.get("type") == "page":
                tab_url = tab.get("url", "")
                if tab_url and (target_url in tab_url or tab_url in target_url):
                    matching_tabs.append(tab)

        if not matching_tabs:
            parsed_target = urlparse(target_url)
            target_domain = parsed_target.netloc or parsed_target.path
            for tab in tabs:
                if tab.get("type") == "page":
                    tab_url = tab.get("url", "")
                    if target_domain and target_domain in tab_url:
                        matching_tabs.append(tab)

        # Fallback to active/focused tab if no match found
        if not matching_tabs:
            active_tab = self.get_active_tab()
            if active_tab:
                return active_tab

        return matching_tabs[0] if matching_tabs else None

    def execute_js_on_tab(self, tab, js_code, context_id=None, await_promise=False):
        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            raise ConnectionError("Không tìm thấy webSocketDebuggerUrl cho tab.")

        timeout = 15 if await_promise else 4
        ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
        try:
            # Prepare payload
            payload = {
                "id": 9999,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_code,
                    "returnByValue": True,
                    "awaitPromise": await_promise
                }
            }
            if context_id is not None:
                payload["params"]["contextId"] = context_id

            ws.send(json.dumps(payload))
            
            # Wait for response
            ws.settimeout(timeout - 1.0 if timeout > 1 else 1.0)
            while True:
                res_raw = ws.recv()
                res = json.loads(res_raw)
                if res.get("id") == 9999:
                    result = res.get("result", {})
                    if "exceptionDetails" in result:
                        desc = result["exceptionDetails"].get("exception", {}).get("description", "Unknown error")
                        raise RuntimeError(f"Lỗi thực thi JS: {desc}")
                    return result.get("result", {}).get("value")
        finally:
            ws.close()

    def get_all_contexts(self, tab):
        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            return []
        
        ws = websocket.create_connection(ws_url, timeout=3, suppress_origin=True)
        contexts = []
        try:
            ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            ws.settimeout(2.0)
            while True:
                msg_raw = ws.recv()
                msg = json.loads(msg_raw)
                if msg.get("method") == "Runtime.executionContextCreated":
                    ctx = msg["params"]["context"]
                    contexts.append((ctx["id"], ctx.get("origin", "")))
                elif msg.get("id") == 1:
                    break
        finally:
            ws.close()
        return contexts if contexts else [(None, "Default Context")]

    def find_active_context(self, tab):
        """Finds the execution context ID that contains the most quiz elements/inputs."""
        contexts = self.get_all_contexts(tab)
        if not contexts:
            return None
        
        valid_contexts = [c for c in contexts if c[0] is not None]
        if not valid_contexts:
            return contexts[0][0]
            
        best_ctx = valid_contexts[0][0]
        max_count = -1
        
        for ctx_id, origin in valid_contexts:
            try:
                check_js = """
                (function() {
                    let selectors = ['.wrapper-problem-response', 'fieldset', '.que', '.question', '.quiz-question', '.question-card', '.game-object-view', '.game-object-quiz', '.quiz-choice-item'];
                    let maxCount = 0;
                    for (let s of selectors) {
                        let c = document.querySelectorAll(s).length;
                        if (c > maxCount) {
                            maxCount = c;
                        }
                    }
                    if (maxCount > 0) return maxCount;
                    return document.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]').length;
                })()
                """
                count = self.execute_js_on_tab(tab, check_js, context_id=ctx_id)
                if count is not None and count > max_count:
                    max_count = count
                    best_ctx = ctx_id
            except Exception:
                pass
        return best_ctx

    def inject_anti_cheat_bypass(self, tab):
        """Injects bypass script that runs on every page navigation / new document."""
        tab_id = tab.get("id")
        if tab_id in self._injected_tabs:
            return True

        js_code = """
        (function() {
            try {
                let dummyViolation = function(reason) {
                    console.log("Anti-cheat bypassed (Injected on new document):", reason);
                };
                
                if (typeof window.handleViolation === 'undefined' || window.handleViolation !== dummyViolation) {
                    Object.defineProperty(window, 'handleViolation', {
                        get: function() { return dummyViolation; },
                        set: function(val) { console.log("Tried to overwrite handleViolation, ignored."); },
                        configurable: true
                    });
                }
                
                Object.defineProperty(window, 'violationCount', {
                    get: function() { return 0; },
                    set: function(val) { console.log("Tried to set violationCount, ignored."); },
                    configurable: true
                });

                Object.defineProperty(window, 'warningOverlayOpen', {
                    get: function() { return false; },
                    set: function(val) { console.log("Tried to set warningOverlayOpen, ignored."); },
                    configurable: true
                });
            } catch(e) {
                console.error("New document bypass injection failed:", e);
            }
        })();
        """
        
        # Inject to active page right now
        try:
            self.execute_js_on_tab(tab, js_code)
        except Exception:
            pass
            
        # Register to run on new documents / navigations
        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            return True
            
        try:
            import json
            ws = websocket.create_connection(ws_url, timeout=3, suppress_origin=True)
            # Enable Page domain
            ws.send(json.dumps({"id": 10001, "method": "Page.enable"}))
            while True:
                res = json.loads(ws.recv())
                if res.get("id") == 10001:
                    break
            # Register script
            ws.send(json.dumps({
                "id": 10002,
                "method": "Page.addScriptToEvaluateOnNewDocument",
                "params": {"source": js_code}
            }))
            while True:
                res = json.loads(ws.recv())
                if res.get("id") == 10002:
                    break
            ws.close()
            self._injected_tabs.add(tab_id)
            return True
        except Exception as e:
            print("Failed to register Page.addScriptToEvaluateOnNewDocument:", e)
            return True

    def scan_question(self, tab, question_number, quiz_mode="auto"):
        """Scrapes question text and option values for a specific index (1-based)."""
        self.inject_anti_cheat_bypass(tab)
        js_code = """
        (function(targetIndex, quizMode) {
            // Bypass quiz lockdown violation handler
            try {
                window.handleViolation = function(reason) {
                    console.log("Anti-cheat bypassed:", reason);
                };
                window.violationCount = 0;
                window.warningOverlayOpen = false;
                
                // Hide any active warning overlay immediately
                let overlay = document.getElementById("warning-overlay");
                if (overlay) {
                    overlay.classList.remove("show");
                }
                // Try clicking resume button to cleanly restore focus/state in page closure
                let resumeBtn = document.querySelector('.warn-btn.resume');
                if (resumeBtn && overlay && overlay.classList.contains("show")) {
                    resumeBtn.click();
                }
                // Reset counter elements
                let display = document.getElementById("violation-display");
                if (display) display.innerText = "0/3";
                let dots = document.querySelectorAll(".strike-dot");
                if (dots) dots.forEach(dot => dot.classList.remove("active"));
            } catch(e) {}


            function getOptions(el) {
                // 1. Standard inputs
                let inputs = Array.from(el.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]'));
                if (inputs.length > 0) return inputs;
                
                // 2. Custom elements/framework inputs
                let customTags = Array.from(el.querySelectorAll('mat-radio-button, mat-checkbox, ion-radio, ion-checkbox, el-radio, el-checkbox, ui-radio, ui-checkbox'));
                if (customTags.length > 0) return customTags;

                // 3. Custom classes
                let custom = Array.from(el.querySelectorAll('.quiz-choice-item, .choice-item, .answer-item, .option-item, .choice, .option, .answer, [class$="choice-item"], [class$="answer-item"], [class$="option-item"]'));
                if (custom.length > 0) {
                    custom = custom.filter(item => {
                        let hasOuter = custom.some(other => other !== item && other.contains(item));
                        return !hasOuter;
                    });
                    if (custom.length >= 2) return custom;
                }
                
                // 4. Element prefixes matching A. B. C. D. (Optimized!)
                let candidates = Array.from(el.querySelectorAll('div, p, li, span, label, td'));
                let prefixOptions = [];
                for (let child of candidates) {
                    let text = (child.textContent || "").trim();
                    if (text && text.match(/^[A-G]\\s*[\\.\\:\\)\\-\\u3002]/i)) {
                        let hasChildOption = false;
                        let subCandidates = child.querySelectorAll('div, p, li, span, label, td');
                        for (let sub of subCandidates) {
                            let subText = (sub.textContent || "").trim();
                            if (subText && subText.match(/^[A-G]\\s*[\\.\\:\\)\\-\\u3002]/i)) {
                                hasChildOption = true;
                                break;
                            }
                        }
                        if (!hasChildOption) {
                            prefixOptions.push(child);
                        }
                    }
                }
                if (prefixOptions.length >= 2) return prefixOptions;

                // 5. Options container children fallback
                let optionsContainer = el.querySelector('.game-object-quiz-choices, .options, .choices, .answers, .options-container, .choices-container, .answers-container');
                if (optionsContainer) {
                    let children = Array.from(optionsContainer.children);
                    if (children.length >= 2) return children;
                }

                // 6. Buttons/Links/List-items/Labels as choices (Fallback)
                let fallbackSelectors = [
                    'label',
                    'li',
                    'tr',
                    'button',
                    'a',
                    '[role="button"]',
                    '.option',
                    '.choice',
                    '.answer'
                ];
                for (let sel of fallbackSelectors) {
                    let items = Array.from(el.querySelectorAll(sel));
                    items = items.filter(item => {
                        let hasOuter = items.some(other => other !== item && other.contains(item));
                        return !hasOuter;
                    });
                    items = items.filter(item => {
                        let text = (item.textContent || "").trim().toLowerCase();
                        if (!text) return false;
                        if (text.includes('next') || text.includes('tiếp') || text.includes('prev') || text.includes('quay') || text.includes('back') || text.includes('submit') || text.includes('nộp')) {
                            return false;
                        }
                        return true;
                    });
                    if (items.length >= 2 && items.length <= 20) {
                        return items;
                    }
                }
                
                // 7. Dropdown Select element option tags
                let selects = el.querySelectorAll('select');
                if (selects.length > 0) {
                    let opts = Array.from(selects[0].querySelectorAll('option')).filter(o => o.value && o.textContent.trim());
                    if (opts.length >= 2) return opts;
                }

                return [];
            }

            function getQuestionNumber(el) {
                // 1. Look inside for question number label
                let qnoEl = el.querySelector('.qno, .questionnumber, .info .questionnumber, .question-number, .question-number-lbl, .question-idx, .q-idx');
                if (qnoEl) {
                    let match = qnoEl.textContent.match(/\\d+/);
                    if (match) return parseInt(match[0], 10);
                }
                
                // 2. Search all children for numbers with question prefix
                let children = el.querySelectorAll('div, span, p, h1, h2, h3, h4, h5, h6, legend, b, strong');
                for (let child of children) {
                    let text = (child.textContent || "").trim();
                    if (!text) continue;
                    
                    let match = text.match(/^(?:Câu|Question|Câu hỏi|Q|No|No\\.)?\\s*(\\d+)[\\.\\:\\)\\s\\-]/i);
                    if (match) {
                        // Avoid option letters being matched if class matches choice/option
                        if (text.match(/^[A-G]\\s*[\\.\\:\\)\\s\\-]/i)) continue;
                        return parseInt(match[1], 10);
                    }
                    
                    let exactMatch = text.match(/^(\\d+)$/);
                    if (exactMatch) {
                        let className = child.className || "";
                        let id = child.id || "";
                        if (className.match(/(num|no|index|seq|label|title|header|qno)/i) || id.match(/(num|no|index|seq|label|title|header|qno)/i)) {
                            return parseInt(exactMatch[1], 10);
                        }
                    }
                }

                // 3. Look at the text content of the question text
                let qTextEl = el.querySelector('.qtext, .question-text, .question-title, .question-content, .question_text, .question_content, .description, .prompt, h3, h4, legend, .problem-group-label, .game-object-question-text, .game-object-question, [id$="_question-name"], [class*="question-name"], [class*="question-title"], [class*="question-content"]');
                if (qTextEl) {
                    let match = qTextEl.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                    if (match) return parseInt(match[1], 10);
                }

                // 4. Try parsing input name/id attributes in this container
                let inputs = Array.from(el.querySelectorAll('input, select, textarea, [role="radio"], [role="checkbox"]'));
                for (let input of inputs) {
                    let name = input.getAttribute('name') || "";
                    let id = input.getAttribute('id') || "";
                    let match = name.match(/(?:question|q|ans|answer|choice|problem)[\-_]?(\\d+)/i) || 
                                id.match(/(?:question|q|ans|answer|choice|problem)[\-_]?(\\d+)/i);
                    if (match) {
                        return parseInt(match[1], 10);
                    }
                }

                // 5. Try container attributes
                let idAttr = el.getAttribute('id') || "";
                let classAttr = el.getAttribute('class') || "";
                let containerMatch = idAttr.match(/(?:question|q|problem)[\-_]?(\\d+)/i) || 
                                     classAttr.match(/(?:question|q|problem)[\-_]?(\\d+)/i);
                if (containerMatch) {
                    return parseInt(containerMatch[1], 10);
                }

                // 6. Look at any heading inside
                let headers = el.querySelectorAll('h1, h2, h3, h4, h5, h6, legend');
                for (let h of headers) {
                    let match = h.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                    if (match) return parseInt(match[1], 10);
                }
                
                // 7. Try parsing the whole element's textContent prefix
                let match = el.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                if (match) return parseInt(match[1], 10);
                
                return null;
            }

            // Check if we are on cover/start page first
            let startBtnSelectors = [
                '.start-btn',
                '.btn-start',
                '.start-exam',
                'button[onclick*="start"]',
                'button[onclick*="Exam"]',
                'button[onclick*="doQuiz"]',
                'input[type="button"][value*="Bắt đầu"]',
                'input[type="submit"][value*="Bắt đầu"]'
            ];
            let startBtn = null;
            for (let sel of startBtnSelectors) {
                startBtn = document.querySelector(sel);
                if (startBtn) break;
            }
            if (!startBtn) {
                let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                for (let el of elements) {
                    let text = (el.textContent || "").trim().toLowerCase();
                    if (text === 'bắt đầu' || text === 'bắt đầu làm bài' || text === 'start exam' || text === 'vào thi' || text === 'tiếp tục lần nỗ lực này' || text.includes('start attempt') || text.includes('vào phòng thi')) {
                        startBtn = el;
                        break;
                    }
                }
            }
            if (startBtn) {
                let realInputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]');
                if (realInputs.length === 0) {
                    startBtn.click();
                    return { success: true, status: "waiting_navigation", currentQuestion: 0, targetQuestion: targetIndex, info: "Đã tự động click nút Bắt đầu thi" };
                }
            }

            let allPotential = [];
            let selectors = [
                '.que', 
                '.question', 
                '.quiz-question', 
                '.question-card', 
                '.wrapper-problem-response', 
                'fieldset', 
                '.choicegroup', 
                '.form-group', 
                '.problem', 
                '.question_holder',
                '.game-object-quiz',
                '.game-object-view',
                'div[id*="question"]',
                'div[class*="question"]',
                'div[class*="quiz"]',
                'div[class*="problem"]',
                '.test-question',
                '.exam-question'
            ];
            selectors.forEach(s => {
                try {
                    let elms = document.querySelectorAll(s);
                    elms.forEach(el => {
                        if (!allPotential.includes(el)) {
                            allPotential.push(el);
                        }
                    });
                } catch(e) {}
            });

            let questionContainers = allPotential.filter(el => {
                if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                    return false;
                }
                let opts = getOptions(el);
                return opts.length >= 2 && opts.length <= 20;
            });

            if (questionContainers.length === 0) {
                let fallbacks = document.querySelectorAll('div, section, fieldset, form, tr, li');
                questionContainers = Array.from(fallbacks).filter(el => {
                    if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                        return false;
                    }
                    let opts = getOptions(el);
                    if (opts.length < 2 || opts.length > 20) return false;
                    
                    let text = el.textContent || "";
                    let hasQuestionKeywords = text.match(/(câu|question|câu hỏi|\\bQ\\d+\\b|\\bQ\\.\\d+\\b|\\b\\d+[\\.\\:\\)\\s\\-])/i);
                    return hasQuestionKeywords;
                });
            }

            if (questionContainers.length === 0) {
                let fallbacks = document.querySelectorAll('div, section, fieldset, form, tr, td');
                questionContainers = Array.from(fallbacks).filter(el => {
                    if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                        return false;
                    }
                    let opts = getOptions(el);
                    return opts.length >= 2 && opts.length <= 20;
                });
            }

            // Filter and deduplicate nested question containers
            questionContainers = questionContainers.filter(el => {
                let opts = getOptions(el);
                if (opts.length === 0) return false;
                
                let hasNestedSubQuestion = questionContainers.some(other => {
                    if (other === el) return false;
                    if (!el.contains(other)) return false;
                    let otherOpts = getOptions(other);
                    return otherOpts.length > 0 && otherOpts.length < opts.length;
                });
                if (hasNestedSubQuestion) return false;
                
                let hasLargerWrapper = questionContainers.some(other => {
                    if (other === el) return false;
                    if (!other.contains(el)) return false;
                    let otherOpts = getOptions(other);
                    return otherOpts.length === opts.length;
                });
                if (hasLargerWrapper) return false;
                
                return true;
            });

            if (questionContainers.length === 0) {
                // Check if we are on cover/start page
                let startBtnSelectors = [
                    '.start-btn',
                    '.btn-start',
                    '.start-exam',
                    'button[onclick*="start"]',
                    'button[onclick*="Exam"]',
                    'button[onclick*="doQuiz"]',
                    'input[type="button"][value*="Bắt đầu"]',
                    'input[type="submit"][value*="Bắt đầu"]'
                ];
                let startBtn = null;
                for (let sel of startBtnSelectors) {
                    startBtn = document.querySelector(sel);
                    if (startBtn) break;
                }
                if (!startBtn) {
                    let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                    for (let el of elements) {
                        let text = (el.textContent || "").trim().toLowerCase();
                        if (text === 'bắt đầu' || text === 'bắt đầu làm bài' || text === 'start exam' || text === 'vào thi' || text === 'tiếp tục lần nỗ lực này' || text.includes('start attempt') || text.includes('vào phòng thi')) {
                            startBtn = el;
                            break;
                        }
                    }
                }
                if (startBtn) {
                    startBtn.click();
                    return { success: true, status: "waiting_navigation", currentQuestion: 0, targetQuestion: targetIndex, info: "Đã tự động click nút Bắt đầu thi" };
                }
                return { success: false, error: "Không tìm thấy câu hỏi nào trên trang!" };
            }

            // Sort by document position
            questionContainers.sort((a, b) => {
                return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
            });

            // Map question containers to detected question numbers using our new mapping algorithm
            let activeSidebar = document.querySelector('.qnbutton.active, .nav-item.active, .qnbutton.thispage, .nav-item.thispage, .question-nav.active, .quiz-nav.active, .active-question');
            if (!activeSidebar) {
                let navs = Array.from(document.querySelectorAll('.qnbutton, .nav-item, .question-nav-item, .quiz-nav-item, [class*="nav-item"], [class*="qnbutton"]'));
                for (let nav of navs) {
                    if (nav.classList.contains('active') || nav.classList.contains('current') || nav.classList.contains('selected') || nav.getAttribute('aria-current') || nav.getAttribute('aria-selected') === 'true') {
                        activeSidebar = nav;
                        break;
                    }
                }
            }
            let activeSidebarNum = null;
            if (activeSidebar) {
                let text = activeSidebar.textContent.trim();
                let match = text.match(/\\d+/);
                if (match) {
                    activeSidebarNum = parseInt(match[0], 10);
                }
            }

            function getPageNumber() {
                let textEls = document.querySelectorAll('.pagination, .page-link, .active, div, span, p');
                for (let el of textEls) {
                    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
                    let text = (el.textContent || "").trim();
                    if (!text) continue;
                    
                    let match = text.match(/^(?:Trang|Page)\\s*(\\d+)/i);
                    if (match) return parseInt(match[1], 10);
                }
                
                let activePageEl = document.querySelector('.pagination .active, .page-item.active, .pager .active');
                if (activePageEl) {
                    let match = activePageEl.textContent.match(/\\d+/);
                    if (match) return parseInt(match[0], 10);
                }
                
                return 1;
            }

            let S = null;
            let N = questionContainers.length;
            if (quizMode === "single") {
                N = 1;
            }
            
            // 1. Try to find a container with an explicit question number
            for (let idx = 0; idx < questionContainers.length; idx++) {
                let num = getQuestionNumber(questionContainers[idx]);
                if (num !== null) {
                    S = num - idx;
                    break;
                }
            }
            
            // 2. If not found, use activeSidebarNum with the mapping formula
            if (S === null && activeSidebarNum !== null) {
                S = Math.floor((activeSidebarNum - 1) / N) * N + 1;
            }
            
            // 3. If still not found, use pageNum
            if (S === null) {
                let pageNum = getPageNumber();
                S = Math.floor((pageNum - 1) / N) + 1;
            }
            
            // 4. Fallback to targetIndex or 1 if still null
            if (S === null || isNaN(S) || S < 1) {
                S = 1;
            }
            
            // Now map all containers sequentially starting from S
            let mappedContainers = [];
            if (quizMode === "single" && questionContainers.length > 0) {
                let num = getQuestionNumber(questionContainers[0]) || activeSidebarNum || targetIndex;
                mappedContainers.push({ el: questionContainers[0], number: num });
            } else {
                questionContainers.forEach((el, idx) => {
                    mappedContainers.push({ el: el, number: S + idx });
                });
            }

            // Find if targetIndex is in mappedContainers
            let targetContainer = null;
            let targetItem = mappedContainers.find(item => item.number === targetIndex);
            if (targetItem) {
                targetContainer = targetItem.el;
            } else {
                // If not found, and we have multiple containers but none matched, or single container on wrong page:
                // We need to navigate to targetIndex!
                let currentActiveNum = (mappedContainers[0] && mappedContainers[0].number) || activeSidebarNum || 1;
                
                // Try to click sidebar/grid item matching targetIndex
                let clicked = false;
                let navSelectors = [
                    `.nav-item[data-q="${targetIndex}"]`,
                    `.nav-item[href*="question-${targetIndex}"]`,
                    `.qnbutton[data-q="${targetIndex}"]`,
                    `#qnbutton-${targetIndex}`,
                    `#nav-item-${targetIndex}`
                ];
                for (let sel of navSelectors) {
                    let btn = document.querySelector(sel);
                    if (btn) {
                        btn.click();
                        clicked = true;
                        break;
                    }
                }
                
                if (!clicked) {
                    // Try text matching for qnbuttons, nav-items, etc.
                    let btns = Array.from(document.querySelectorAll('.qnbutton, .nav-item, .question-nav-item, .quiz-nav-item, [class*="nav-item"], [class*="qnbutton"], button, a'));
                    for (let btn of btns) {
                        let text = btn.textContent.trim();
                        let match = text.match(/^\\s*(?:Câu|Question|Q)?\\s*0*(\\d+)\\s*$/i);
                        if (match && parseInt(match[1], 10) === targetIndex) {
                            btn.click();
                            clicked = true;
                            break;
                        }
                    }
                }

                if (!clicked) {
                    // Fallback to Next / Previous button clicking
                    if (currentActiveNum < targetIndex) {
                        // Click Next
                        let nextBtnSelectors = [
                            'button.next-button',
                            'a.next-button',
                            'button.button-next',
                            'button.sequence-navigation-next',
                            'a.button-next',
                            'a.sequence-navigation-next',
                            '.sequence-nav-button.button-next',
                            '.next a',
                            'button.next-btn',
                            'a.next-btn',
                            '#next-btn',
                            '.btn-next',
                            'button.flash-card-play-game-button-next-card',
                            '[class*="-button-next"]',
                            '[class*="btn-next"]',
                            '.next-card',
                            'input[type="submit"][value*="Next"]',
                            'input[type="submit"][value*="Tiếp"]',
                            'input[type="button"][value*="Next"]',
                            'input[type="button"][value*="Tiếp"]',
                            'button[class*="next"]',
                            'button[class*="Next"]'
                        ];
                        let nextBtn = null;
                        for (let sel of nextBtnSelectors) {
                            nextBtn = document.querySelector(sel);
                            if (nextBtn) break;
                        }
                        if (!nextBtn) {
                            let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                            for (let el of elements) {
                                let text = (el.textContent || "").trim().toLowerCase();
                                if (text === 'tiếp tục' || text === 'tiếp theo' || text === 'next' || text === 'continue' || text.startsWith('tiếp tục') || text.includes('next page')) {
                                    nextBtn = el;
                                    break;
                                }
                            }
                        }
                        if (nextBtn) {
                            nextBtn.click();
                            clicked = true;
                        }
                    } else if (currentActiveNum > targetIndex) {
                        // Click Previous
                        let prevBtnSelectors = [
                            'button.previous-button',
                            'a.previous-button',
                            'button.button-previous',
                            'button.sequence-navigation-previous',
                            'a.button-previous',
                            'a.sequence-navigation-previous',
                            '.sequence-nav-button.button-previous',
                            '.prev a',
                            'button.prev-btn',
                            'a.prev-btn',
                            '#prev-btn',
                            '.btn-prev',
                            'button.flash-card-play-game-button-prev-card',
                            '[class*="-button-prev"]',
                            '[class*="btn-prev"]',
                            '.prev-card',
                            'input[type="submit"][value*="Prev"]',
                            'input[type="submit"][value*="Quay"]',
                            'input[type="button"][value*="Prev"]',
                            'input[type="button"][value*="Quay"]',
                            'button[class*="prev"]',
                            'button[class*="Prev"]',
                            'button[class*="back"]',
                            'button[class*="Back"]'
                        ];
                        let prevBtn = null;
                        for (let sel of prevBtnSelectors) {
                            prevBtn = document.querySelector(sel);
                            if (prevBtn) break;
                        }
                        if (!prevBtn) {
                            let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                            for (let el of elements) {
                                let text = (el.textContent || "").trim().toLowerCase();
                                if (text === 'quay lại' || text === 'trở lại' || text === 'prev' || text === 'previous' || text.startsWith('quay lại') || text.includes('previous page')) {
                                    prevBtn = el;
                                    break;
                                }
                            }
                        }
                        if (prevBtn) {
                            prevBtn.click();
                            clicked = true;
                        }
                    }
                }

                if (clicked) {
                    return { success: true, status: "waiting_navigation", currentQuestion: currentActiveNum, targetQuestion: targetIndex };
                } else {
                    // If we can't navigate, but questionContainers has at least one element, fallback to it
                    targetContainer = questionContainers[0];
                }
            }

            // Scroll to center target question and force focus
            targetContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            targetContainer.setAttribute('tabindex', '-1');
            targetContainer.focus();
            
            try {
                if (window.parent && window.parent !== window) {
                    let frames = window.parent.document.querySelectorAll('iframe');
                    for (let frame of frames) {
                        if (frame.contentWindow === window) {
                            frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            break;
                        }
                    }
                }
            } catch(e) {}
            
            questionContainers.forEach(el => {
                if (el.dataset && el.dataset.originalBorder !== undefined) {
                    el.style.border = el.dataset.originalBorder;
                    delete el.dataset.originalBorder;
                }
            });
            
            let originalBorder = targetContainer.style.border || "";
            targetContainer.dataset.originalBorder = originalBorder;
            targetContainer.style.border = "3px solid #00e5ff";
            setTimeout(() => {
                if (targetContainer.dataset && targetContainer.dataset.originalBorder !== undefined) {
                    targetContainer.style.border = targetContainer.dataset.originalBorder;
                    delete targetContainer.dataset.originalBorder;
                }
            }, 3000);

            // Extract choices/options
            let inputs = getOptions(targetContainer);

            // Extract question text
            let questionText = "";
            let qTextEl = targetContainer.querySelector('.qtext, .question-text, .question-title, .question-content, .question_text, .question_content, .description, .prompt, h3, h4, legend, .problem-group-label, .game-object-question-text, .game-object-question, [id$="_question-name"], [class*="question-name"], [class*="question-title"], [class*="question-content"]');
            if (qTextEl) {
                questionText = qTextEl.textContent.trim();
            }
            if (!questionText) {
                let heading = targetContainer.querySelector('h1, h2, h3, h4, h5, h6');
                if (heading) {
                    questionText = heading.textContent.trim();
                }
            }
            if (!questionText && inputs[0]) {
                let firstOpt = inputs[0];
                let walker = document.createTreeWalker(targetContainer, NodeFilter.SHOW_ELEMENT);
                let node;
                let textParts = [];
                while (node = walker.nextNode()) {
                    if (node === firstOpt || node.contains(firstOpt)) {
                        break;
                    }
                    if (node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE' && node.tagName !== 'TEMPLATE') {
                        let directText = "";
                        for (let child of node.childNodes) {
                            if (child.nodeType === 3) {
                                directText += child.textContent;
                            }
                        }
                        directText = directText.trim();
                        if (directText) {
                            textParts.push(directText);
                        }
                    }
                }
                questionText = textParts.join('\\n').trim();
            }
            if (!questionText) {
                let prev = targetContainer.previousElementSibling;
                if (targetContainer.tagName === 'FIELDSET' || targetContainer.classList.contains('choicegroup')) {
                    let wrapper = targetContainer.closest('.wrapper-problem-response');
                    if (wrapper && wrapper.previousElementSibling) {
                        prev = wrapper.previousElementSibling;
                    }
                }
                if (prev && getOptions(prev).length > 0) {
                    prev = null;
                }
                if (prev && prev.textContent && prev.textContent.trim()) {
                    questionText = prev.textContent.trim();
                } else {
                    let fullText = targetContainer.textContent || "";
                    let lines = fullText.split('\\n').map(l => l.trim()).filter(l => l);
                    let qLines = [];
                    for (let line of lines) {
                        if (line.match(/^[A-G]\\s*[\\.\\:\\-\\)\\u3002]/i)) break;
                        qLines.push(line);
                    }
                    questionText = qLines.join('\\n');
                }
            }

            // Subtraction fallback if questionText is still empty
            if (!questionText.trim()) {
                let containerText = targetContainer.textContent || "";
                inputs.forEach(opt => {
                    let optText = opt.textContent || "";
                    if (optText) {
                        containerText = containerText.replace(optText, "");
                    }
                });
                questionText = containerText.replace(/^[A-G]\\s*[\\.\\:\\-\\)\\u3002]/gi, "").trim();
            }

            let hasImages = targetContainer.querySelectorAll('img').length > 0;
            
            let options = [];
            inputs.forEach((input, idx) => {
                let optText = "";
                if (input.tagName === 'INPUT') {
                    let label = null;
                    if (input.id) {
                        label = document.querySelector(`label[for="${input.id}"]`);
                    }
                    if (!label) {
                        label = input.closest('label');
                    }
                    if (label) {
                        optText = label.textContent.trim();
                    } else {
                        let next = input.nextSibling;
                        if (next && next.nodeType === 3) {
                            optText = next.textContent.trim();
                        }
                    }
                    if (!optText) {
                        let sibling = input.nextElementSibling;
                        if (sibling && sibling.textContent.trim()) {
                            optText = sibling.textContent.trim();
                        }
                    }
                } else {
                    optText = input.textContent.trim();
                }

                // Image choices fallback
                if (!optText.trim()) {
                    let img = input.querySelector('img');
                    if (!img && input.tagName === 'INPUT' && input.id) {
                        let lbl = document.querySelector(`label[for="${input.id}"]`);
                        if (lbl) img = lbl.querySelector('img');
                    }
                    if (img && img.src) {
                        optText = "[Hình ảnh: " + (img.alt || img.src.split('/').pop()) + "]";
                    }
                }

                options.push({
                    index: idx,
                    text: optText
                });
            });

            // Find totalQuestions
            let totalQuestions = questionContainers.length;
            let sidebarButtons = document.querySelectorAll('.qnbutton, .nav-item');
            if (sidebarButtons.length > totalQuestions) {
                totalQuestions = sidebarButtons.length;
            }
            if (totalQuestions === 1) {
                let textEls = document.querySelectorAll('.progress, .pagination, .info, .status, .question-nav, div, span, p, td');
                for (let el of textEls) {
                    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
                    let text = (el.textContent || "").trim();
                    let match = text.match(/(?:^|\\s)(\\d+)\\/(\\d+)(?:\\s|$)/);
                    if (match) {
                        let parsedTotal = parseInt(match[2], 10);
                        if (parsedTotal > totalQuestions && parsedTotal < 200) {
                            totalQuestions = parsedTotal;
                            break;
                        }
                    }
                }
            }

            return {
                success: true,
                status: "ready",
                totalQuestions: totalQuestions,
                questionText: questionText,
                options: options,
                hasImages: hasImages
            };
        })(%d, "%s");
        """ % (int(question_number), quiz_mode)

        import time
        max_retries = 15
        for retry in range(max_retries):
            try:
                ctx_id = self.find_active_context(tab)
                result = self.execute_js_on_tab(tab, js_code, context_id=ctx_id)
                if result and result.get("success") and result.get("status") == "waiting_navigation":
                    time.sleep(0.6)
                    continue
                return result
            except Exception as e:
                if retry == max_retries - 1:
                    return {"success": False, "error": f"Lỗi thực thi quét context: {str(e)}"}
                time.sleep(0.5)

    def click_option(self, tab, question_number, option_index, quiz_mode="auto"):
        """Clicks option of a specific question (1-based for question, 0-based for option)."""
        self.inject_anti_cheat_bypass(tab)
        js_code = """
        (function(targetQuestionIdx, targetOptionIdx, quizMode) {
            // Bypass quiz lockdown violation handler
            try {
                window.handleViolation = function(reason) {
                    console.log("Anti-cheat bypassed:", reason);
                };
                window.violationCount = 0;
                window.warningOverlayOpen = false;
                
                // Hide any active warning overlay immediately
                let overlay = document.getElementById("warning-overlay");
                if (overlay) {
                    overlay.classList.remove("show");
                }
                // Try clicking resume button to cleanly restore focus/state in page closure
                let resumeBtn = document.querySelector('.warn-btn.resume');
                if (resumeBtn && overlay && overlay.classList.contains("show")) {
                    resumeBtn.click();
                }
                // Reset counter elements
                let display = document.getElementById("violation-display");
                if (display) display.innerText = "0/3";
                let dots = document.querySelectorAll(".strike-dot");
                if (dots) dots.forEach(dot => dot.classList.remove("active"));
            } catch(e) {}


            function getOptions(el) {
                // 1. Standard inputs
                let inputs = Array.from(el.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]'));
                if (inputs.length > 0) return inputs;
                
                // 2. Custom elements/framework inputs
                let customTags = Array.from(el.querySelectorAll('mat-radio-button, mat-checkbox, ion-radio, ion-checkbox, el-radio, el-checkbox, ui-radio, ui-checkbox'));
                if (customTags.length > 0) return customTags;

                // 3. Custom classes
                let custom = Array.from(el.querySelectorAll('.quiz-choice-item, .choice-item, .answer-item, .option-item, .choice, .option, .answer, [class$="choice-item"], [class$="answer-item"], [class$="option-item"]'));
                if (custom.length > 0) {
                    custom = custom.filter(item => {
                        let hasOuter = custom.some(other => other !== item && other.contains(item));
                        return !hasOuter;
                    });
                    if (custom.length >= 2) return custom;
                }
                
                // 4. Element prefixes matching A. B. C. D. (Optimized!)
                let candidates = Array.from(el.querySelectorAll('div, p, li, span, label, td'));
                let prefixOptions = [];
                for (let child of candidates) {
                    let text = (child.textContent || "").trim();
                    if (text && text.match(/^[A-G]\\s*[\\.\\:\\)\\-\\u3002]/i)) {
                        let hasChildOption = false;
                        let subCandidates = child.querySelectorAll('div, p, li, span, label, td');
                        for (let sub of subCandidates) {
                            let subText = (sub.textContent || "").trim();
                            if (subText && subText.match(/^[A-G]\\s*[\\.\\:\\)\\-\\u3002]/i)) {
                                hasChildOption = true;
                                break;
                            }
                        }
                        if (!hasChildOption) {
                            prefixOptions.push(child);
                        }
                    }
                }
                if (prefixOptions.length >= 2) return prefixOptions;

                // 5. Options container children fallback
                let optionsContainer = el.querySelector('.game-object-quiz-choices, .options, .choices, .answers, .options-container, .choices-container, .answers-container');
                if (optionsContainer) {
                    let children = Array.from(optionsContainer.children);
                    if (children.length >= 2) return children;
                }

                // 6. Buttons/Links/List-items/Labels as choices (Fallback)
                let fallbackSelectors = [
                    'label',
                    'li',
                    'tr',
                    'button',
                    'a',
                    '[role="button"]',
                    '.option',
                    '.choice',
                    '.answer'
                ];
                for (let sel of fallbackSelectors) {
                    let items = Array.from(el.querySelectorAll(sel));
                    items = items.filter(item => {
                        let hasOuter = items.some(other => other !== item && other.contains(item));
                        return !hasOuter;
                    });
                    items = items.filter(item => {
                        let text = (item.textContent || "").trim().toLowerCase();
                        if (!text) return false;
                        if (text.includes('next') || text.includes('tiếp') || text.includes('prev') || text.includes('quay') || text.includes('back') || text.includes('submit') || text.includes('nộp')) {
                            return false;
                        }
                        return true;
                    });
                    if (items.length >= 2 && items.length <= 20) {
                        return items;
                    }
                }
                
                // 7. Dropdown Select element option tags
                let selects = el.querySelectorAll('select');
                if (selects.length > 0) {
                    let opts = Array.from(selects[0].querySelectorAll('option')).filter(o => o.value && o.textContent.trim());
                    if (opts.length >= 2) return opts;
                }

                return [];
            }

            function getQuestionNumber(el) {
                // 1. Look inside for question number label
                let qnoEl = el.querySelector('.qno, .questionnumber, .info .questionnumber, .question-number, .question-number-lbl, .question-idx, .q-idx');
                if (qnoEl) {
                    let match = qnoEl.textContent.match(/\\d+/);
                    if (match) return parseInt(match[0], 10);
                }
                
                // 2. Search all children for numbers with question prefix
                let children = el.querySelectorAll('div, span, p, h1, h2, h3, h4, h5, h6, legend, b, strong');
                for (let child of children) {
                    let text = (child.textContent || "").trim();
                    if (!text) continue;
                    
                    let match = text.match(/^(?:Câu|Question|Câu hỏi|Q|No|No\\.)?\\s*(\\d+)[\\.\\:\\)\\s\\-]/i);
                    if (match) {
                        // Avoid option letters being matched if class matches choice/option
                        if (text.match(/^[A-G]\\s*[\\.\\:\\)\\s\\-]/i)) continue;
                        return parseInt(match[1], 10);
                    }
                    
                    let exactMatch = text.match(/^(\\d+)$/);
                    if (exactMatch) {
                        let className = child.className || "";
                        let id = child.id || "";
                        if (className.match(/(num|no|index|seq|label|title|header|qno)/i) || id.match(/(num|no|index|seq|label|title|header|qno)/i)) {
                            return parseInt(exactMatch[1], 10);
                        }
                    }
                }

                // 3. Look at the text content of the question text
                let qTextEl = el.querySelector('.qtext, .question-text, .question-title, .question-content, .question_text, .question_content, .description, .prompt, h3, h4, legend, .problem-group-label, .game-object-question-text, .game-object-question, [id$="_question-name"], [class*="question-name"], [class*="question-title"], [class*="question-content"]');
                if (qTextEl) {
                    let match = qTextEl.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                    if (match) return parseInt(match[1], 10);
                }

                // 4. Try parsing input name/id attributes in this container
                let inputs = Array.from(el.querySelectorAll('input, select, textarea, [role="radio"], [role="checkbox"]'));
                for (let input of inputs) {
                    let name = input.getAttribute('name') || "";
                    let id = input.getAttribute('id') || "";
                    let match = name.match(/(?:question|q|ans|answer|choice|problem)[\-_]?(\\d+)/i) || 
                                id.match(/(?:question|q|ans|answer|choice|problem)[\-_]?(\\d+)/i);
                    if (match) {
                        return parseInt(match[1], 10);
                    }
                }

                // 5. Try container attributes
                let idAttr = el.getAttribute('id') || "";
                let classAttr = el.getAttribute('class') || "";
                let containerMatch = idAttr.match(/(?:question|q|problem)[\-_]?(\\d+)/i) || 
                                     classAttr.match(/(?:question|q|problem)[\-_]?(\\d+)/i);
                if (containerMatch) {
                    return parseInt(containerMatch[1], 10);
                }

                // 6. Look at any heading inside
                let headers = el.querySelectorAll('h1, h2, h3, h4, h5, h6, legend');
                for (let h of headers) {
                    let match = h.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                    if (match) return parseInt(match[1], 10);
                }
                
                // 7. Try parsing the whole element's textContent prefix
                let match = el.textContent.trim().match(/^(?:Câu|Question|Câu hỏi)?\\s*(\\d+)[\\.\\:\\)\\s]/i);
                if (match) return parseInt(match[1], 10);
                
                return null;
            }

            // Check if we are on cover/start page first
            let startBtnSelectors = [
                '.start-btn',
                '.btn-start',
                '.start-exam',
                'button[onclick*="start"]',
                'button[onclick*="Exam"]',
                'button[onclick*="doQuiz"]',
                'input[type="button"][value*="Bắt đầu"]',
                'input[type="submit"][value*="Bắt đầu"]'
            ];
            let startBtn = null;
            for (let sel of startBtnSelectors) {
                startBtn = document.querySelector(sel);
                if (startBtn) break;
            }
            if (!startBtn) {
                let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                for (let el of elements) {
                    let text = (el.textContent || "").trim().toLowerCase();
                    if (text === 'bắt đầu' || text === 'bắt đầu làm bài' || text === 'start exam' || text === 'vào thi' || text === 'tiếp tục lần nỗ lực này' || text.includes('start attempt') || text.includes('vào phòng thi')) {
                        startBtn = el;
                        break;
                    }
                }
            }
            if (startBtn) {
                let realInputs = document.querySelectorAll('input[type="radio"], input[type="checkbox"], [role="radio"], [role="checkbox"]');
                if (realInputs.length === 0) {
                    startBtn.click();
                    return { success: true, status: "waiting_navigation", currentQuestion: 0, targetQuestion: targetQuestionIdx };
                }
            }

            let allPotential = [];
            let selectors = [
                '.que', 
                '.question', 
                '.quiz-question', 
                '.question-card', 
                '.wrapper-problem-response', 
                'fieldset', 
                '.choicegroup', 
                '.form-group', 
                '.problem', 
                '.question_holder',
                '.game-object-quiz',
                '.game-object-view',
                'div[id*="question"]',
                'div[class*="question"]',
                'div[class*="quiz"]',
                'div[class*="problem"]',
                '.test-question',
                '.exam-question'
            ];
            selectors.forEach(s => {
                try {
                    let elms = document.querySelectorAll(s);
                    elms.forEach(el => {
                        if (!allPotential.includes(el)) {
                            allPotential.push(el);
                        }
                    });
                } catch(e) {}
            });

            let questionContainers = allPotential.filter(el => {
                if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                    return false;
                }
                let opts = getOptions(el);
                return opts.length >= 2 && opts.length <= 20;
            });

            if (questionContainers.length === 0) {
                let fallbacks = document.querySelectorAll('div, section, fieldset, form, tr, li');
                questionContainers = Array.from(fallbacks).filter(el => {
                    if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                        return false;
                    }
                    let opts = getOptions(el);
                    if (opts.length < 2 || opts.length > 20) return false;
                    
                    let text = el.textContent || "";
                    let hasQuestionKeywords = text.match(/(câu|question|câu hỏi|\\bQ\\d+\\b|\\bQ\\.\\d+\\b|\\b\\d+[\\.\\:\\)\\s\\-])/i);
                    return hasQuestionKeywords;
                });
            }

            if (questionContainers.length === 0) {
                let fallbacks = document.querySelectorAll('div, section, fieldset, form, tr, td');
                questionContainers = Array.from(fallbacks).filter(el => {
                    if (el.closest('.navigation-panel, .sidebar, .question-nav, .quiz-nav, nav, .pagination, [class*="nav-panel"], [class*="sidebar"], [class*="nav-grid"], [id*="nav-grid"], [class*="question-grid"], [id*="navigation"], [class*="sidebar"], [class*="qn-container"], [class*="qnbuttons"], [class*="quiz-nav"], [class*="nav-block"]')) {
                        return false;
                    }
                    let opts = getOptions(el);
                    return opts.length >= 2 && opts.length <= 20;
                });
            }

            // Filter and deduplicate nested question containers
            questionContainers = questionContainers.filter(el => {
                let opts = getOptions(el);
                if (opts.length === 0) return false;
                
                let hasNestedSubQuestion = questionContainers.some(other => {
                    if (other === el) return false;
                    if (!el.contains(other)) return false;
                    let otherOpts = getOptions(other);
                    return otherOpts.length > 0 && otherOpts.length < opts.length;
                });
                if (hasNestedSubQuestion) return false;
                
                let hasLargerWrapper = questionContainers.some(other => {
                    if (other === el) return false;
                    if (!other.contains(el)) return false;
                    let otherOpts = getOptions(other);
                    return otherOpts.length === opts.length;
                });
                if (hasLargerWrapper) return false;
                
                return true;
            });

            if (questionContainers.length === 0) {
                // Check if we are on cover/start page
                let startBtnSelectors = [
                    '.start-btn',
                    '.btn-start',
                    '.start-exam',
                    'button[onclick*="start"]',
                    'button[onclick*="Exam"]',
                    'button[onclick*="doQuiz"]',
                    'input[type="button"][value*="Bắt đầu"]',
                    'input[type="submit"][value*="Bắt đầu"]'
                ];
                let startBtn = null;
                for (let sel of startBtnSelectors) {
                    startBtn = document.querySelector(sel);
                    if (startBtn) break;
                }
                if (!startBtn) {
                    let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                    for (let el of elements) {
                        let text = (el.textContent || "").trim().toLowerCase();
                        if (text === 'bắt đầu' || text === 'bắt đầu làm bài' || text === 'start exam' || text === 'vào thi' || text === 'tiếp tục lần nỗ lực này' || text.includes('start attempt') || text.includes('vào phòng thi')) {
                            startBtn = el;
                            break;
                        }
                    }
                }
                if (startBtn) {
                    startBtn.click();
                    return { success: true, status: "waiting_navigation", currentQuestion: 0, targetQuestion: targetQuestionIdx };
                }
                return { success: false, error: "Không tìm thấy câu hỏi nào." };
            }

            questionContainers.sort((a, b) => {
                return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
            });

            let activeSidebar = document.querySelector('.qnbutton.active, .nav-item.active, .qnbutton.thispage, .nav-item.thispage, .question-nav.active, .quiz-nav.active, .active-question');
            if (!activeSidebar) {
                let navs = Array.from(document.querySelectorAll('.qnbutton, .nav-item, .question-nav-item, .quiz-nav-item, [class*="nav-item"], [class*="qnbutton"]'));
                for (let nav of navs) {
                    if (nav.classList.contains('active') || nav.classList.contains('current') || nav.classList.contains('selected') || nav.getAttribute('aria-current') || nav.getAttribute('aria-selected') === 'true') {
                        activeSidebar = nav;
                        break;
                    }
                }
            }
            let activeSidebarNum = null;
            if (activeSidebar) {
                let text = activeSidebar.textContent.trim();
                let match = text.match(/\\d+/);
                if (match) {
                    activeSidebarNum = parseInt(match[0], 10);
                }
            }

            function getPageNumber() {
                let textEls = document.querySelectorAll('.pagination, .page-link, .active, div, span, p');
                for (let el of textEls) {
                    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName)) continue;
                    let text = (el.textContent || "").trim();
                    if (!text) continue;
                    
                    let match = text.match(/^(?:Trang|Page)\\s*(\\d+)/i);
                    if (match) return parseInt(match[1], 10);
                }
                
                let activePageEl = document.querySelector('.pagination .active, .page-item.active, .pager .active');
                if (activePageEl) {
                    let match = activePageEl.textContent.match(/\\d+/);
                    if (match) return parseInt(match[0], 10);
                }
                
                return 1;
            }

            let S = null;
            let N = questionContainers.length;
            if (quizMode === "single") {
                N = 1;
            }
            
            // 1. Try to find a container with an explicit question number
            for (let idx = 0; idx < questionContainers.length; idx++) {
                let num = getQuestionNumber(questionContainers[idx]);
                if (num !== null) {
                    S = num - idx;
                    break;
                }
            }
            
            // 2. If not found, use activeSidebarNum with the mapping formula
            if (S === null && activeSidebarNum !== null) {
                S = Math.floor((activeSidebarNum - 1) / N) * N + 1;
            }
            
            // 3. If still not found, use pageNum
            if (S === null) {
                let pageNum = getPageNumber();
                S = Math.floor((pageNum - 1) / N) + 1;
            }
            
            // 4. Fallback to targetQuestionIdx or 1 if still null
            if (S === null || isNaN(S) || S < 1) {
                S = 1;
            }
            
            // Now map all containers sequentially starting from S
            let mappedContainers = [];
            if (quizMode === "single" && questionContainers.length > 0) {
                let num = getQuestionNumber(questionContainers[0]) || activeSidebarNum || targetQuestionIdx;
                mappedContainers.push({ el: questionContainers[0], number: num });
            } else {
                questionContainers.forEach((el, idx) => {
                    mappedContainers.push({ el: el, number: S + idx });
                });
            }

            let targetContainer = null;
            let targetItem = mappedContainers.find(item => item.number === targetQuestionIdx);
            if (targetItem) {
                targetContainer = targetItem.el;
            } else {
                // Navigate first
                let currentActiveNum = (mappedContainers[0] && mappedContainers[0].number) || activeSidebarNum || 1;
                let clicked = false;
                let navSelectors = [
                    `.nav-item[data-q="${targetQuestionIdx}"]`,
                    `.nav-item[href*="question-${targetQuestionIdx}"]`,
                    `.qnbutton[data-q="${targetQuestionIdx}"]`,
                    `#qnbutton-${targetQuestionIdx}`,
                    `#nav-item-${targetQuestionIdx}`
                ];
                for (let sel of navSelectors) {
                    let btn = document.querySelector(sel);
                    if (btn) {
                        btn.click();
                        clicked = true;
                        break;
                    }
                }
                
                if (!clicked) {
                    // Try text matching for qnbuttons, nav-items, etc.
                    let btns = Array.from(document.querySelectorAll('.qnbutton, .nav-item, .question-nav-item, .quiz-nav-item, [class*="nav-item"], [class*="qnbutton"], button, a'));
                    for (let btn of btns) {
                        let text = btn.textContent.trim();
                        let match = text.match(/^\\s*(?:Câu|Question|Q)?\\s*0*(\\d+)\\s*$/i);
                        if (match && parseInt(match[1], 10) === targetQuestionIdx) {
                            btn.click();
                            clicked = true;
                            break;
                        }
                    }
                }

                if (!clicked) {
                    if (currentActiveNum < targetQuestionIdx) {
                        let nextBtnSelectors = [
                            'button.next-button',
                            'a.next-button',
                            'button.button-next',
                            'button.sequence-navigation-next',
                            'a.button-next',
                            'a.sequence-navigation-next',
                            '.sequence-nav-button.button-next',
                            '.next a',
                            'button.next-btn',
                            'a.next-btn',
                            '#next-btn',
                            '.btn-next',
                            'button.flash-card-play-game-button-next-card',
                            '[class*="-button-next"]',
                            '[class*="btn-next"]',
                            '.next-card',
                            'input[type="submit"][value*="Next"]',
                            'input[type="submit"][value*="Tiếp"]',
                            'input[type="button"][value*="Next"]',
                            'input[type="button"][value*="Tiếp"]',
                            'button[class*="next"]',
                            'button[class*="Next"]'
                        ];
                        let nextBtn = null;
                        for (let sel of nextBtnSelectors) {
                            nextBtn = document.querySelector(sel);
                            if (nextBtn) break;
                        }
                        if (!nextBtn) {
                            let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                            for (let el of elements) {
                                let text = (el.textContent || "").trim().toLowerCase();
                                if (text === 'tiếp tục' || text === 'tiếp theo' || text === 'next' || text === 'continue' || text.startsWith('tiếp tục') || text.includes('next page')) {
                                    nextBtn = el;
                                    break;
                                }
                            }
                        }
                        if (nextBtn) {
                            nextBtn.click();
                            clicked = true;
                        }
                    } else if (currentActiveNum > targetQuestionIdx) {
                        let prevBtnSelectors = [
                            'button.previous-button',
                            'a.previous-button',
                            'button.button-previous',
                            'button.sequence-navigation-previous',
                            'a.button-previous',
                            'a.sequence-navigation-previous',
                            '.sequence-nav-button.button-previous',
                            '.prev a',
                            'button.prev-btn',
                            'a.prev-btn',
                            '#prev-btn',
                            '.btn-prev',
                            'button.flash-card-play-game-button-prev-card',
                            '[class*="-button-prev"]',
                            '[class*="btn-prev"]',
                            '.prev-card',
                            'input[type="submit"][value*="Prev"]',
                            'input[type="submit"][value*="Quay"]',
                            'input[type="button"][value*="Prev"]',
                            'input[type="button"][value*="Quay"]',
                            'button[class*="prev"]',
                            'button[class*="Prev"]',
                            'button[class*="back"]',
                            'button[class*="Back"]'
                        ];
                        let prevBtn = null;
                        for (let sel of prevBtnSelectors) {
                            prevBtn = document.querySelector(sel);
                            if (prevBtn) break;
                        }
                        if (!prevBtn) {
                            let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                            for (let el of elements) {
                                let text = (el.textContent || "").trim().toLowerCase();
                                if (text === 'quay lại' || text === 'trở lại' || text === 'prev' || text === 'previous' || text.startsWith('quay lại') || text.includes('previous page')) {
                                    prevBtn = el;
                                    break;
                                }
                            }
                        }
                        if (prevBtn) {
                            prevBtn.click();
                            clicked = true;
                        }
                    }
                }
                
                if (clicked) {
                    return { success: true, status: "waiting_navigation", currentQuestion: currentActiveNum, targetQuestion: targetQuestionIdx };
                } else {
                    targetContainer = questionContainers[0];
                }
            }

            let inputs = getOptions(targetContainer);
            if (targetOptionIdx >= 0 && targetOptionIdx < inputs.length) {
                let inputToClick = inputs[targetOptionIdx];
                
                targetContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
                targetContainer.setAttribute('tabindex', '-1');
                targetContainer.focus();
                
                questionContainers.forEach(el => {
                    if (el.dataset && el.dataset.originalBorder !== undefined) {
                        el.style.border = el.dataset.originalBorder;
                        delete el.dataset.originalBorder;
                    }
                });
                
                let originalBorder = targetContainer.style.border || "";
                targetContainer.dataset.originalBorder = originalBorder;
                targetContainer.style.border = "3px solid #00e5ff";
                setTimeout(() => {
                    if (targetContainer.dataset && targetContainer.dataset.originalBorder !== undefined) {
                        targetContainer.style.border = targetContainer.dataset.originalBorder;
                        delete targetContainer.dataset.originalBorder;
                    }
                }, 3000);
                
                try {
                    if (window.parent && window.parent !== window) {
                        let frames = window.parent.document.querySelectorAll('iframe');
                        for (let frame of frames) {
                            if (frame.contentWindow === window) {
                                frame.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                break;
                            }
                        }
                    }
                } catch(e) {}
                
                // Finger emoji animation
                try {
                    let rect = inputToClick.getBoundingClientRect();
                    let doc = targetContainer.ownerDocument || document;
                    let finger = doc.createElement('div');
                    finger.innerText = "👈";
                    finger.style.position = 'absolute';
                    finger.style.left = (rect.left + (window.pageXOffset || doc.documentElement.scrollLeft) + rect.width + 5) + 'px';
                    finger.style.top = (rect.top + (window.pageYOffset || doc.documentElement.scrollTop) - 5) + 'px';
                    finger.style.pointerEvents = 'none';
                    finger.style.fontSize = '26px';
                    finger.style.zIndex = '999999';
                    finger.style.transition = 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                    finger.style.transform = 'translateX(15px)';
                    finger.style.opacity = '0';
                    doc.body.appendChild(finger);
                    
                    setTimeout(() => {
                        finger.style.transform = 'translateX(0px)';
                        finger.style.opacity = '1';
                    }, 50);
                    
                    setTimeout(() => {
                        finger.style.transform = 'scale(0.8) translateX(-3px)';
                    }, 350);

                    setTimeout(() => {
                        finger.style.transform = 'scale(1.2) translateY(-15px)';
                        finger.style.opacity = '0';
                    }, 750);

                    setTimeout(() => {
                        finger.remove();
                    }, 1200);
                } catch(e) {}
                
                if (inputToClick.tagName === 'INPUT') {
                    if (!inputToClick.checked) {
                        inputToClick.click();
                        inputToClick.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } else if (inputToClick.tagName === 'OPTION') {
                    let select = inputToClick.closest('select');
                    if (select) {
                        select.value = inputToClick.value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } else {
                    inputToClick.click();
                    inputToClick.dispatchEvent(new Event('click', { bubbles: true }));
                }

                return { success: true, status: "ready", isSingleQuestion: (quizMode === "single" || (quizMode === "auto" && questionContainers.length === 1)) };
            }
            return { success: false, error: "Không tìm thấy lựa chọn tương ứng để click." };
        })(%d, %d, "%s");
        """ % (int(question_number), int(option_index), quiz_mode)

        import time
        max_retries = 15
        for retry in range(max_retries):
            try:
                ctx_id = self.find_active_context(tab)
                result = self.execute_js_on_tab(tab, js_code, context_id=ctx_id)
                if result and result.get("success") and result.get("status") == "waiting_navigation":
                    time.sleep(0.6)
                    continue
                
                # Let the next scan_question call handle navigation to prevent double-click race conditions.
                return result
            except Exception as e:
                if retry == max_retries - 1:
                    return {"success": False, "error": f"Lỗi click context: {str(e)}"}
                time.sleep(0.5)

    def click_next_button(self, tab, context_id=None):
        """Finds and clicks the Next / Continue / Submit button on the page."""
        js_code = """
        (function() {
            let nextBtnSelectors = [
                'button.flash-card-play-game-button-next-card',
                '[class*="-button-next"]',
                '[class*="btn-next"]',
                '.next-card',
                'input[type="submit"][value*="Next"]',
                'input[type="submit"][value*="Tiếp"]',
                'input[type="button"][value*="Next"]',
                'input[type="button"][value*="Tiếp"]',
                'button[class*="next"]',
                'button[class*="Next"]'
            ];
            let nextBtn = null;
            for (let sel of nextBtnSelectors) {
                nextBtn = document.querySelector(sel);
                if (nextBtn) break;
            }
            if (!nextBtn) {
                // Fallback to text matching
                let elements = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a, div.btn, span'));
                for (let el of elements) {
                    let text = (el.innerText || "").trim().toLowerCase();
                    if (text === 'tiếp tục' || text === 'tiếp theo' || text === 'next' || text === 'continue' || text.startsWith('tiếp tục') || text.includes('next page')) {
                        nextBtn = el;
                        break;
                    }
                }
            }
            if (nextBtn) {
                nextBtn.click();
                nextBtn.dispatchEvent(new Event('click', { bubbles: true }));
                return { success: true, text: nextBtn.innerText || nextBtn.value };
            }
            return { success: false, error: "Next button not found" };
        })()
        """
        try:
            if context_id is None:
                context_id = self.find_active_context(tab)
            return self.execute_js_on_tab(tab, js_code, context_id=context_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

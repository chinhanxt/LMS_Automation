# -*- coding: utf-8 -*-
import os
import json

CONFIG_FILE = "config_speed.json"

DEFAULT_CONFIG = {
    "last_url": "https://apps.lms.hutech.edu.vn",
    "speed": "4.0",
    "debug_port": "9222",
    "mute_video": True,
    "remaining_seconds": 10,
    "auto_skip_video": True,
    "ai_auto_fill": False,
    "ai_skip_img": True,
    "ai_target_question": 1,
    "quiz_mode": "auto",
    "api_keys": []
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

SELECTORS_FILE = "config_selectors.json"

DEFAULT_SELECTORS = {
    "question_selectors": [
        ".que", ".question", ".quiz-question", ".question-card", 
        ".wrapper-problem-response", "fieldset", ".choicegroup", 
        ".form-group", ".problem", ".question_holder",
        ".game-object-quiz", ".game-object-view",
        "div[id*=\"question\"]", "div[class*=\"question\"]",
        "div[class*=\"quiz\"]", "div[class*=\"problem\"]",
        ".test-question", ".exam-question"
    ],
    "option_selectors": [
        "input[type=\"radio\"]", "input[type=\"checkbox\"]",
        "[role=\"radio\"]", "[role=\"checkbox\"]"
    ],
    "custom_option_tags": [
        "mat-radio-button", "mat-checkbox", "ion-radio", "ion-checkbox",
        "el-radio", "el-checkbox", "ui-radio", "ui-checkbox"
    ],
    "custom_option_classes": [
        ".quiz-choice-item", ".choice-item", ".answer-item",
        ".option-item", ".choice", ".option", ".answer"
    ],
    "next_btn_selectors": [
        "button.next-button", "a.next-button", "button.button-next",
        "button.sequence-navigation-next", "a.button-next",
        "a.sequence-navigation-next", ".sequence-nav-button.button-next",
        ".next a", "button.next-btn", "a.next-btn", "#next-btn",
        ".btn-next", "button.flash-card-play-game-button-next-card",
        "[class*=\"-button-next\"]", "[class*=\"btn-next\"]",
        ".next-card", "input[type=\"submit\"][value*=\"Next\"]",
        "input[type=\"submit\"][value*=\"Tiếp\"]",
        "input[type=\"button\"][value*=\"Next\"]",
        "input[type=\"button\"][value*=\"Tiếp\"]",
        "button[class*=\"next\"]", "button[class*=\"Next\"]"
    ],
    "prev_btn_selectors": [
        "button.previous-button", "a.previous-button", "button.button-previous",
        "button.sequence-navigation-previous", "a.button-previous",
        "a.sequence-navigation-previous", ".sequence-nav-button.button-previous",
        ".prev a", "button.prev-btn", "a.prev-btn", "#prev-btn",
        ".btn-prev", "button.flash-card-play-game-button-prev-card",
        "[class*=\"-button-prev\"]", "[class*=\"btn-prev\"]",
        ".prev-card", "input[type=\"submit\"][value*=\"Prev\"]",
        "input[type=\"submit\"][value*=\"Quay\"]",
        "input[type=\"button\"][value*=\"Prev\"]",
        "input[type=\"button\"][value*=\"Quay\"]",
        "button[class*=\"prev\"]", "button[class*=\"Prev\"]",
        "button[class*=\"back\"]", "button[class*=\"Back\"]"
    ],
    "start_btn_selectors": [
        ".start-btn", ".btn-start", ".start-exam",
        "button[onclick*=\"start\"]", "button[onclick*=\"Exam\"]",
        "button[onclick*=\"doQuiz\"]",
        "input[type=\"button\"][value*=\"Bắt đầu\"]",
        "input[type=\"submit\"][value*=\"Bắt đầu\"]"
    ]
}

def load_selectors_config():
    if os.path.exists(SELECTORS_FILE):
        try:
            with open(SELECTORS_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure all default keys exist
                for k, v in DEFAULT_SELECTORS.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return DEFAULT_SELECTORS.copy()

def save_selectors_config(config):
    try:
        with open(SELECTORS_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

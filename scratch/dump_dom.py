import json
from chrome_automation import ChromeAutomation

auto = ChromeAutomation("9333")
tabs = auto.get_tabs()
print("All tabs:")
for tab in tabs:
    print(tab)

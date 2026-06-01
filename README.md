# Xpath-Extracter-tool

# 🕵️ Interactive XPath / Selector Extractor — Selenium Edition

A point-and-click browser tool that lets you hover over any element on any webpage and instantly capture its **relative XPath**, CSS selector, and ID — ready to paste directly into Selenium test scripts.

---

## 📋 Prerequisites

- Python 3.8+
- Google Chrome installed
- ChromeDriver matching your Chrome version (or use `webdriver-manager` to handle it automatically)

---

## ⚙️ Installation

### Option A — Manual ChromeDriver

```bash
pip install selenium
```

Download ChromeDriver from https://chromedriver.chromium.org/downloads and place it in your PATH.

### Option B — Auto-managed ChromeDriver (recommended)

```bash
pip install selenium webdriver-manager
```

Then swap the driver init in the script:

```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)
```

---

## 🚀 Usage

```bash
python xpath_extractor_selenium.py
```

A Chrome browser window will open automatically at the configured `START_URL`. You can navigate to any page from there.

### Step-by-step workflow

| Step | Action |
|------|--------|
| 1 | Browser opens — navigate to the page you want to inspect |
| 2 | **Hover** over any element — a tooltip appears at the bottom-left showing its XPath, CSS, tag, ID, class, and text |
| 3 | **Click** the element — it gets **locked** (tooltip turns orange) |
| 4 | Switch back to the terminal |
| 5 | *(Optional)* Type a label like `login_button` or `email_input` |
| 6 | Press **ENTER** — the element is captured and the browser unlocks |
| 7 | Repeat for as many elements as you need |
| 8 | Type `save` to export everything to a JSON file |
| 9 | Type `quit` to exit (auto-saves on exit) |

### Terminal commands

| Command | Description |
|---------|-------------|
| `ENTER` | Capture the currently locked element |
| `mylabel` + `ENTER` | Capture with a custom label |
| `save` | Export all captured selectors to a timestamped JSON file |
| `show` | Print a summary of all captured selectors in the terminal |
| `quit` | Exit the tool (auto-saves if anything was captured) |

---

## 🔍 XPath Priority Logic

The tool generates **relative XPaths** using the following priority order — it picks the first rule that produces a unique, stable selector:

| Priority | Strategy | Example |
|----------|----------|---------|
| 1 | `id` attribute | `//*[@id="submitBtn"]` |
| 2 | `name` attribute | `//input[@name="email"]` |
| 3 | `placeholder` attribute | `//input[@placeholder="Search..."]` |
| 4 | `type` + `class` combo | `//button[@type="submit" and contains(@class,"btn-primary")]` |
| 5 | `data-*` attributes | `//div[@data-testid="hero-banner"]` |
| 6 | `aria-label` | `//button[@aria-label="Close dialog"]` |
| 7 | `role` attribute | `//nav[@role="navigation"]` |
| 8 | Exact text match | `//button[normalize-space(text())="Sign In"]` |
| 9 | Partial text match | `//p[contains(normalize-space(.),"Welcome back")]` |
| 10 | Class-based | `//div[contains(@class,"card-header")]` |
| 11 | Positional fallback | `(//span)[4]` |

> **Tip:** IDs and `name` attributes give the most stable selectors. Positional fallbacks are fragile — prefer to label elements that have a unique ID or class.

---

## 📤 Output

### JSON export (`selectors_YYYYMMDD_HHMMSS.json`)

```json
[
  {
    "tag": "input",
    "id": "email",
    "cls": "form-control input-lg",
    "type": "email",
    "name": "email",
    "text": "",
    "xpath": "//*[@id=\"email\"]",
    "css": "#email",
    "timestamp": "2026-06-01T10:23:45.123Z",
    "label": "email_input"
  },
  {
    "tag": "button",
    "id": "",
    "cls": "btn btn-primary",
    "type": "submit",
    "name": "",
    "text": "Sign In",
    "xpath": "//button[@type=\"submit\" and contains(@class,\"btn-primary\")]",
    "css": "form > button.btn.btn-primary",
    "timestamp": "2026-06-01T10:24:01.456Z",
    "label": "login_button"
  }
]
```

### Terminal summary + Selenium snippets

After `save` or `show`, the terminal prints copy-paste ready Selenium code:

```python
# email_input
email_input = driver.find_element(By.ID, 'email')

# login_button
login_button = driver.find_element(By.XPATH, '//button[@type="submit" and contains(@class,"btn-primary")]')
# CSS alt: driver.find_element(By.CSS_SELECTOR, 'form > button.btn.btn-primary')
```

---

## 🛠️ Configuration

Edit the top of the script to change the starting URL:

```python
START_URL = "https://your-app.com/login"
```

---

## 📁 File Structure

```
project/
├── xpath_extractor_selenium.py   # Main script
├── README.md                     # This file
└── selectors_20260601_102345.json  # Generated on save/quit
```

---

## ⚠️ Known Limitations

- **Dynamic content**: Elements rendered after AJAX calls may need a brief wait before hovering. Navigate to the final state before clicking.
- **iframes**: The injected JS runs in the top-level document only. Elements inside `<iframe>` tags won't be captured — you'd need to switch frames manually via Selenium first.
- **Shadow DOM**: Custom web components using Shadow DOM may not be reachable with standard XPath. Use JS-based locators in Selenium for those.
- **Positional XPaths** like `(//div)[12]` are fragile — if the page structure changes, they break. Always prefer ID or attribute-based selectors.

---

## 💡 Tips for QA / Test Automation

- **Label clearly**: Use names like `checkout_button`, `username_field`, `error_toast` — your JSON becomes a selector registry.
- **Cross-check in DevTools**: Paste the XPath into Chrome DevTools console with `$x('//your/xpath')` to verify it matches exactly one element.
- **Use CSS for speed**: Selenium's CSS selector engine is slightly faster than XPath for most browsers. Both are exported.
- **Keep JSON as source of truth**: Store the JSON file in your repo alongside your test suite for easy selector maintenance.

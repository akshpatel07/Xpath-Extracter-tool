"""
╔══════════════════════════════════════════════════════════════╗
║      INTERACTIVE XPATH / SELECTOR EXTRACTOR (Selenium)       ║
║                                                              ║
║  HOW TO USE:                                                 ║
║  1. pip install selenium                                     ║
║  2. Run: python xpath_extractor_selenium.py                  ║
║  3. Browser opens — navigate to any page manually            ║
║  4. Hover over any element → selectors shown in tooltip      ║
║  5. Click any element → selectors LOCKED & printed           ║
║  6. Press ENTER in terminal to capture & unlock              ║
║  7. Optionally type a label before pressing ENTER            ║
║  8. Type 'save' to export captured selectors to JSON         ║
║  9. Type 'quit' to exit                                      ║
╚══════════════════════════════════════════════════════════════╝

XPaths generated are RELATIVE (e.g. //input[@id='email'])
Priority order:
  1. //*[@id="..."]
  2. //tag[@name="..."]
  3. //tag[contains(@class,"...")]
  4. //tag[@type="..."]
  5. //tag[normalize-space(text())="..."]
  6. Positional fallback: (//tag)[n]
"""

import json
import threading
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import JavascriptException, WebDriverException

START_URL = "https://www.lumoslearning.com/llwp/stepup-starter-for-schools.html?schoolid=439546&code=B005"

# ── JS injected into page ─────────────────────────────────────────────────────
INJECTED_JS = r"""
(function() {
    if (window.__xpathExtractorActive) return;
    window.__xpathExtractorActive = true;
    window.__capturedElements = [];
    window.__locked = false;

    // ── Relative XPath builder (priority-based) ─────────────────────────────
    function getRelativeXPath(el) {
        // 1. ID — most reliable
        if (el.id) return `//*[@id="${el.id}"]`;

        const tag = el.tagName.toLowerCase();

        // 2. name attribute
        const name = el.getAttribute('name');
        if (name) return `//${tag}[@name="${name}"]`;

        // 3. placeholder (inputs)
        const ph = el.getAttribute('placeholder');
        if (ph) return `//${tag}[@placeholder="${ph}"]`;

        // 4. type + distinctive class combo (e.g. buttons)
        const type = el.getAttribute('type');
        const cls  = [...el.classList].filter(c => c.length > 2 && !/^js-/.test(c));
        if (type && cls.length) return `//${tag}[@type="${type}" and contains(@class,"${cls[0]}")]`;
        if (type) return `//${tag}[@type="${type}"]`;

        // 5. data-* attribute
        for (const attr of el.attributes) {
            if (attr.name.startsWith('data-') && attr.value) {
                return `//${tag}[@${attr.name}="${attr.value}"]`;
            }
        }

        // 6. aria-label
        const aria = el.getAttribute('aria-label');
        if (aria) return `//${tag}[@aria-label="${aria}"]`;

        // 7. role
        const role = el.getAttribute('role');
        if (role) return `//${tag}[@role="${role}"]`;

        // 8. Visible text (trim, first 40 chars)
        const txt = (el.innerText || el.textContent || '').trim().replace(/\s+/g,' ').substring(0, 40);
        if (txt && txt.length < 40) return `//${tag}[normalize-space(text())="${txt}"]`;
        if (txt) return `//${tag}[contains(normalize-space(.),"${txt.substring(0,30)}")]`;

        // 9. class-based (first meaningful class)
        if (cls.length) return `//${tag}[contains(@class,"${cls[0]}")]`;

        // 10. Positional fallback — count same-tag siblings in entire DOM
        const all = document.querySelectorAll(tag);
        const idx = [...all].indexOf(el) + 1;
        return `(//${tag})[${idx}]`;
    }

    // ── CSS selector builder ────────────────────────────────────────────────
    function getCSSSelector(el) {
        if (el.id) return `#${el.id}`;
        const parts = [];
        while (el && el.nodeType === 1 && el.tagName !== 'BODY') {
            let sel = el.tagName.toLowerCase();
            if (el.className) {
                const cls = [...el.classList].slice(0, 3).join('.');
                if (cls) sel += '.' + cls;
            }
            const sibs = [...(el.parentElement?.children || [])].filter(s => s.tagName === el.tagName);
            if (sibs.length > 1) sel += `:nth-of-type(${sibs.indexOf(el) + 1})`;
            parts.unshift(sel);
            el = el.parentElement;
        }
        return parts.join(' > ');
    }

    // ── Tooltip ─────────────────────────────────────────────────────────────
    const tip = document.createElement('div');
    tip.id = '__xpathTip';
    tip.style.cssText = `
        position:fixed; bottom:10px; left:10px; z-index:999999;
        background:#1a1a2e; color:#00ff88; font:12px monospace;
        padding:10px 14px; border-radius:8px; max-width:740px;
        border:1px solid #00ff88; pointer-events:none;
        box-shadow:0 4px 20px rgba(0,255,136,0.3);
        white-space:pre-wrap; word-break:break-all;
    `;
    document.body.appendChild(tip);

    // ── Highlight overlay ───────────────────────────────────────────────────
    const hl = document.createElement('div');
    hl.id = '__xpathHighlight';
    hl.style.cssText = `
        position:fixed; z-index:999998; pointer-events:none;
        background:rgba(0,255,136,0.15); border:2px solid #00ff88;
        transition:all 0.1s;
    `;
    document.body.appendChild(hl);

    function highlightEl(el) {
        const r = el.getBoundingClientRect();
        hl.style.left   = r.left   + 'px';
        hl.style.top    = r.top    + 'px';
        hl.style.width  = r.width  + 'px';
        hl.style.height = r.height + 'px';
        hl.style.display = 'block';
    }

    // ── Mouseover ──────────────────────────────────────────────────────────
    document.addEventListener('mouseover', function(e) {
        if (window.__locked) return;
        const el = e.target;
        if (el.id === '__xpathTip' || el.id === '__xpathHighlight') return;

        const xpath = getRelativeXPath(el);
        const css   = getCSSSelector(el);
        const tag   = el.tagName.toLowerCase();
        const id    = el.id   ? `id="${el.id}"` : '';
        const cls   = el.className ? `class="${[...el.classList].join(' ')}"` : '';
        const txt   = (el.innerText || '').trim().substring(0, 60);
        const type  = el.getAttribute('type') || '';
        const name  = el.getAttribute('name') || '';
        const role  = el.getAttribute('role') || '';

        tip.textContent = [
            `Tag:    <${tag}> ${type?'type="'+type+'"':''} ${name?'name="'+name+'"':''} ${role?'role="'+role+'"':''}`,
            `ID:     ${id || '(none)'}`,
            `Class:  ${cls || '(none)'}`,
            `Text:   ${txt || '(none)'}`,
            ``,
            `XPath:  ${xpath}`,
            `CSS:    ${css}`,
            ``,
            `► CLICK to LOCK this element`,
        ].join('\n');

        highlightEl(el);
    }, true);

    // ── Click: lock & record ───────────────────────────────────────────────
    document.addEventListener('click', function(e) {
        const el = e.target;
        if (el.id === '__xpathTip' || el.id === '__xpathHighlight') return;
        if (window.__locked) return;

        e.preventDefault();
        e.stopPropagation();
        window.__locked = true;

        const xpath = getRelativeXPath(el);
        const css   = getCSSSelector(el);
        const tag   = el.tagName.toLowerCase();
        const txt   = (el.innerText || '').trim().substring(0, 80);
        const id    = el.id || '';
        const clsStr = [...el.classList].join(' ');
        const type  = el.getAttribute('type') || '';
        const name  = el.getAttribute('name') || '';

        const captured = {
            tag, id, cls: clsStr, type, name,
            text: txt, xpath, css,
            timestamp: new Date().toISOString()
        };
        window.__capturedElements.push(captured);

        tip.style.background  = '#0d3b2e';
        tip.style.borderColor = '#ffaa00';
        tip.style.color       = '#ffaa00';
        tip.textContent = [
            `✅ LOCKED — Element #${window.__capturedElements.length}`,
            `Tag:   <${tag}> ${type?'type="'+type+'"':''} ${name?'name="'+name+'"':''}`,
            `ID:    ${id || '(none)'}`,
            `Class: ${clsStr || '(none)'}`,
            `Text:  ${txt || '(none)'}`,
            ``,
            `XPath: ${xpath}`,
            `CSS:   ${css}`,
            ``,
            `► Press ENTER in terminal to capture & unlock`,
        ].join('\n');

        // Signal Python via window title
        document.title = '__CAPTURED__:' + JSON.stringify(captured);
    }, true);

    // ── Unlock ─────────────────────────────────────────────────────────────
    window.__unlockExtractor = function() {
        window.__locked = false;
        tip.style.background  = '#1a1a2e';
        tip.style.borderColor = '#00ff88';
        tip.style.color       = '#00ff88';
        tip.textContent = '► Hover over elements to inspect. Click to lock.';
        hl.style.display = 'none';
        document.title = 'XPath Extractor — Ready';
    };

    tip.textContent = '► Hover over elements to inspect. Click to lock.';
    console.log('[XPath Extractor] Injected and ready.');
})();
"""


# ─────────────────────────────────────────────────────────────────────────────

def setup_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--disable-extensions")
    # Keep browser open after script exits (comment out if unwanted)
    opts.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=opts)
    return driver


def inject_js(driver: webdriver.Chrome):
    try:
        driver.execute_script(INJECTED_JS)
    except (JavascriptException, WebDriverException):
        pass


def read_captured(driver: webdriver.Chrome) -> dict | None:
    """Read element data encoded in the page title."""
    try:
        title = driver.title
        if title.startswith("__CAPTURED__:"):
            raw = title[len("__CAPTURED__:"):]
            return json.loads(raw)
    except Exception:
        pass
    return None


def unlock(driver: webdriver.Chrome):
    try:
        driver.execute_script("window.__unlockExtractor()")
    except Exception:
        pass


def print_summary(captured: list):
    print()
    print("═" * 68)
    print("  CAPTURED SELECTORS SUMMARY")
    print("═" * 68)
    for item in captured:
        label = item.get("label", "?")
        print(f"\n  [{label}]")
        print(f"    XPath  : {item['xpath']}")
        print(f"    CSS    : {item['css']}")
        if item.get("id"):
            print(f"    By ID  : #{item['id']}")
        print(f"    Text   : {item.get('text','')[:60]}")

    print()
    print("  ── Selenium-ready snippets ──")
    print()
    for item in captured:
        label = item.get("label", "element").replace(" ", "_")
        xpath = item["xpath"]
        css   = item["css"]
        eid   = item.get("id", "")
        print(f"  # {label}")
        if eid:
            print(f"  {label} = driver.find_element(By.ID, '{eid}')")
        else:
            print(f"  {label} = driver.find_element(By.XPATH, '{xpath}')")
            print(f"  # CSS alt: driver.find_element(By.CSS_SELECTOR, '{css}')")
        print()
    print("═" * 68)


def run():
    captured_all: list[dict] = []

    driver = setup_driver()

    # Re-inject JS on every page load using a polling thread
    stop_event = threading.Event()

    def reinjector():
        last_url = ""
        while not stop_event.is_set():
            try:
                url = driver.current_url
                if url != last_url:
                    inject_js(driver)
                    last_url = url
            except WebDriverException:
                break
            time.sleep(0.8)

    t = threading.Thread(target=reinjector, daemon=True)
    t.start()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     INTERACTIVE XPATH / SELECTOR EXTRACTOR  (Selenium)      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    driver.get(START_URL)
    inject_js(driver)

    print("[✓] Browser ready.")
    print()
    print("INSTRUCTIONS:")
    print("  • Navigate to the page you want to inspect")
    print("  • Hover over any element — tooltip shows selectors")
    print("  • Click an element to LOCK it")
    print("  • Come back here, type an optional label, press ENTER")
    print("  • Type 'save'  → export all captured selectors to JSON")
    print("  • Type 'show'  → print summary in terminal")
    print("  • Type 'quit'  → exit (auto-saves if anything captured)")
    print()

    while True:
        try:
            cmd = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd.lower() == "quit":
            break

        if cmd.lower() == "save":
            if not captured_all:
                print("  [!] Nothing captured yet.")
                continue
            fname = f"selectors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fname, "w") as f:
                json.dump(captured_all, f, indent=2)
            print(f"  [✓] Saved {len(captured_all)} selectors → {fname}")
            print_summary(captured_all)
            continue

        if cmd.lower() == "show":
            print_summary(captured_all)
            continue

        if cmd.lower() == "help":
            print("  Commands: ENTER=capture, save, show, quit")
            continue

        # ENTER (with optional label) — read capture from page title
        data = read_captured(driver)
        if data is None:
            print("  [!] No element locked yet. Click an element in the browser first.")
            continue

        label = cmd if cmd else f"element_{len(captured_all) + 1}"
        data["label"] = label
        captured_all.append(data)

        print()
        print(f"  ✅ Captured [{label}]")
        print(f"     Tag:   <{data['tag']}> type='{data.get('type','')}' name='{data.get('name','')}'")
        print(f"     ID:    {data.get('id') or '(none)'}")
        print(f"     Class: {data.get('cls') or '(none)'}")
        print(f"     Text:  {data.get('text') or '(none)'}")
        print(f"     XPath: {data['xpath']}")
        print(f"     CSS:   {data['css']}")
        print()
        print("  ► Hover & click the NEXT element, then press ENTER:")

        unlock(driver)

    # ── Auto-save on exit ──────────────────────────────────────────────────
    stop_event.set()
    if captured_all:
        fname = f"selectors_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w") as f:
            json.dump(captured_all, f, indent=2)
        print(f"\n[✓] Auto-saved {len(captured_all)} selectors → {fname}")
        print_summary(captured_all)

    try:
        driver.quit()
    except Exception:
        pass

    print("\n[✓] Done.")


if __name__ == "__main__":
    run()

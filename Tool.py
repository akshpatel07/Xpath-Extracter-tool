"""
╔══════════════════════════════════════════════════════════════╗
║          INTERACTIVE XPATH / SELECTOR EXTRACTOR              ║
║                                                              ║
║  HOW TO USE:                                                 ║
║  1. Run: python xpath_extractor.py                           ║
║  2. Browser opens — navigate to any page manually            ║
║  3. Hover over any element → its selectors shown in console  ║
║  4. Click any element → selectors LOCKED & printed clearly   ║
║  5. Press ENTER in terminal to unlock and pick another       ║
║  6. Type 'save' to save all captured selectors to JSON file  ║
║  7. Type 'quit' to exit                                      ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

START_URL = "https://www.lumoslearning.com/llwp/stepup-starter-for-schools.html?schoolid=439546&code=B005"

# ── JS injected into page to show hover tooltip + capture clicks ──────────────
INJECTED_JS = """
(function() {
    if (window.__xpathExtractorActive) return;
    window.__xpathExtractorActive = true;
    window.__capturedElements = [];
    window.__locked = false;

    // ── Build XPath for an element ──────────────────────────────────────────
    function getXPath(el) {
        if (el.id) return `//*[@id="${el.id}"]`;
        const parts = [];
        while (el && el.nodeType === 1) {
            let idx = 1;
            let sib = el.previousElementSibling;
            while (sib) { if (sib.tagName === el.tagName) idx++; sib = sib.previousElementSibling; }
            const tag = el.tagName.toLowerCase();
            parts.unshift(idx > 1 ? `${tag}[${idx}]` : tag);
            el = el.parentElement;
        }
        return '/' + parts.join('/');
    }

    // ── Build CSS selector ──────────────────────────────────────────────────
    function getCSSSelector(el) {
        if (el.id) return `#${el.id}`;
        const parts = [];
        while (el && el.nodeType === 1 && el.tagName !== 'BODY') {
            let sel = el.tagName.toLowerCase();
            if (el.className) {
                const cls = [...el.classList].slice(0, 3).join('.');
                if (cls) sel += '.' + cls;
            }
            const sib = [...(el.parentElement?.children || [])].filter(s => s.tagName === el.tagName);
            if (sib.length > 1) sel += `:nth-of-type(${sib.indexOf(el)+1})`;
            parts.unshift(sel);
            el = el.parentElement;
        }
        return parts.join(' > ');
    }

    // ── Tooltip element ────────────────────────────────────────────────────
    const tip = document.createElement('div');
    tip.id = '__xpathTip';
    tip.style.cssText = `
        position:fixed; bottom:10px; left:10px; z-index:999999;
        background:#1a1a2e; color:#00ff88; font:12px monospace;
        padding:10px 14px; border-radius:8px; max-width:700px;
        border:1px solid #00ff88; pointer-events:none;
        box-shadow:0 4px 20px rgba(0,255,136,0.3);
        white-space:pre-wrap; word-break:break-all;
    `;
    document.body.appendChild(tip);

    // ── Highlight overlay ─────────────────────────────────────────────────
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

    // ── Mouseover: show tooltip ────────────────────────────────────────────
    document.addEventListener('mouseover', function(e) {
        if (window.__locked) return;
        const el = e.target;
        if (el.id === '__xpathTip' || el.id === '__xpathHighlight') return;

        const xpath  = getXPath(el);
        const css    = getCSSSelector(el);
        const tag    = el.tagName.toLowerCase();
        const id     = el.id ? `id="${el.id}"` : '';
        const cls    = el.className ? `class="${[...el.classList].join(' ')}"` : '';
        const txt    = (el.innerText || '').trim().substring(0, 60);
        const type   = el.getAttribute('type') || '';
        const name   = el.getAttribute('name') || '';
        const role   = el.getAttribute('role') || '';

        tip.textContent = [
            `Tag:     <${tag}> ${type ? 'type="'+type+'"' : ''} ${name ? 'name="'+name+'"' : ''} ${role ? 'role="'+role+'"' : ''}`,
            `ID:      ${id || '(none)'}`,
            `Class:   ${cls || '(none)'}`,
            `Text:    ${txt || '(none)'}`,
            ``,
            `XPath:   ${xpath}`,
            `CSS:     ${css}`,
            ``,
            `► CLICK to LOCK this element`,
        ].join('\\n');

        highlightEl(el);
    }, true);

    // ── Click: lock and record ─────────────────────────────────────────────
    document.addEventListener('click', function(e) {
        const el = e.target;
        if (el.id === '__xpathTip' || el.id === '__xpathHighlight') return;
        if (window.__locked) return;

        e.preventDefault();
        e.stopPropagation();
        window.__locked = true;

        const xpath = getXPath(el);
        const css   = getCSSSelector(el);
        const tag   = el.tagName.toLowerCase();
        const txt   = (el.innerText || '').trim().substring(0, 80);
        const id    = el.id || '';
        const cls   = [...el.classList].join(' ');
        const type  = el.getAttribute('type') || '';
        const name  = el.getAttribute('name') || '';

        const captured = { tag, id, cls, type, name, text: txt, xpath, css,
                           timestamp: new Date().toISOString() };
        window.__capturedElements.push(captured);

        tip.style.background = '#0d3b2e';
        tip.style.borderColor = '#ffaa00';
        tip.style.color = '#ffaa00';
        tip.textContent = [
            `✅ LOCKED — Element #${window.__capturedElements.length}`,
            `Tag:   <${tag}> ${type ? 'type="'+type+'"' : ''} ${name ? 'name="'+name+'"' : ''}`,
            `ID:    ${id || '(none)'}`,
            `Class: ${cls || '(none)'}`,
            `Text:  ${txt || '(none)'}`,
            ``,
            `XPath: ${xpath}`,
            `CSS:   ${css}`,
            ``,
            `► Press ENTER in terminal to unlock and pick another element`,
        ].join('\\n');

        // Signal Python via window title
        document.title = '__CAPTURED__:' + JSON.stringify(captured);

    }, true);

    // ── Unlock function called from Python ─────────────────────────────────
    window.__unlockExtractor = function() {
        window.__locked = false;
        tip.style.background = '#1a1a2e';
        tip.style.borderColor = '#00ff88';
        tip.style.color = '#00ff88';
        tip.textContent = '► Hover over elements to inspect. Click to lock.';
        hl.style.display = 'none';
        document.title = 'XPath Extractor — Ready';
    };

    tip.textContent = '► Hover over elements to inspect. Click to lock.';
    console.log('[XPath Extractor] Injected and ready.');
})();
"""

async def run():
    captured_all = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page    = await context.new_page()

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║          INTERACTIVE XPATH / SELECTOR EXTRACTOR             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()
        print("[*] Opening page …")
        await page.goto(START_URL, timeout=30_000)

        # Inject on every navigation
        async def inject(_):
            try:
                await page.evaluate(INJECTED_JS)
            except Exception:
                pass

        page.on("domcontentloaded", inject)
        await inject(None)

        print("[✓] Browser ready.")
        print()
        print("INSTRUCTIONS:")
        print("  • Navigate the browser to the page you want to inspect")
        print("  • Hover over any element to see its selectors")
        print("  • Click an element to LOCK it")
        print("  • Come back here and press ENTER to capture & unlock")
        print("  • Type a label for the element (e.g. 'next_button')")
        print("  • Type 'save' to export all captured selectors to JSON")
        print("  • Type 'quit' to exit")
        print()

        while True:
            cmd = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input(">> ").strip()
            )

            if cmd.lower() == 'quit':
                break

            if cmd.lower() == 'save':
                if not captured_all:
                    print("  [!] Nothing captured yet.")
                    continue
                fname = f"selectors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(fname, 'w') as f:
                    json.dump(captured_all, f, indent=2)
                print(f"  [✓] Saved {len(captured_all)} selectors to {fname}")
                _print_summary(captured_all)
                continue

            if cmd.lower() == 'show':
                _print_summary(captured_all)
                continue

            if cmd.lower() == 'help':
                print("  Commands: ENTER=capture, save, show, quit")
                continue

            # ENTER pressed — read captured element from page title
            try:
                title = await page.title()
                if title.startswith("__CAPTURED__:"):
                    raw = title[len("__CAPTURED__:"):]
                    data = json.loads(raw)

                    label = cmd if cmd else f"element_{len(captured_all)+1}"
                    data['label'] = label

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
                    print("  ► Hover & click the NEXT element, then press ENTER (or type label first):")

                    # Unlock the extractor
                    await page.evaluate("window.__unlockExtractor()")
                else:
                    print("  [!] No element locked yet. Click an element in the browser first.")
            except Exception as e:
                print(f"  [!] Error reading capture: {e}")

        # Auto-save on exit
        if captured_all:
            fname = f"selectors_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fname, 'w') as f:
                json.dump(captured_all, f, indent=2)
            print(f"\n[✓] Auto-saved {len(captured_all)} selectors to {fname}")
            _print_summary(captured_all)

        await browser.close()
        print("\n[✓] Done.")


def _print_summary(captured):
    print()
    print("═" * 65)
    print("  CAPTURED SELECTORS SUMMARY")
    print("═" * 65)
    for item in captured:
        label = item.get('label', '?')
        print(f"\n  [{label}]")
        print(f"    XPath : {item['xpath']}")
        print(f"    CSS   : {item['css']}")
        if item.get('id'):
            print(f"    By ID : #{item['id']}")
        print(f"    Text  : {item.get('text','')[:60]}")
    print()
    print("  ── Playwright-ready snippets ──")
    for item in captured:
        label = item.get('label', 'element').replace(' ', '_')
        xpath = item['xpath']
        css   = item['css']
        eid   = item.get('id','')
        txt   = item.get('text','')[:30]
        print(f"\n  # {label}")
        if eid:
            print(f"  self.{label} = page.locator('#{eid}')")
        else:
            print(f"  self.{label} = page.locator(\"{css}\")")
        print(f"  # XPath alternative: page.locator(\"{xpath}\")")
    print("═" * 65)


if __name__ == "__main__":
    asyncio.run(run())
"""Exports the executed notebook to a self-contained, responsive HTML report.

Usage: python3 build_html.py   (after NYC_Taxi_Analysis.ipynb has been executed)
"""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
NB = HERE / "NYC_Taxi_Analysis.ipynb"
OUT = HERE / "NYC_Taxi_Analysis.html"

subprocess.run(
    ["jupyter", "nbconvert", "--to", "html", str(NB), "--output", OUT.name],
    check=True, capture_output=True,
)
html = OUT.read_text(encoding="utf-8")

# 1. Self-contained: drop the CDN scripts (require.js / MathJax). The report has no
#    widgets or maths, and they break offline or on restricted networks.
html = re.sub(r'<script[^>]*src="https://cdnjs[^"]*"[^>]*>\s*</script>\s*', "", html, flags=re.I)
html = re.sub(r'<script[^>]*src="[^"]*mathjax[^"]*"[^>]*>\s*</script>\s*', "", html, flags=re.I)
html = re.sub(r'<script[^>]*type="module"[^>]*>(?:(?!</script>).)*?mermaid(?:(?!</script>).)*?</script>\s*', "", html, flags=re.S | re.I)
html = re.sub(r'<script[^>]*type="text/x-mathjax-config"[^>]*>.*?</script>\s*', "", html, flags=re.S | re.I)

# 2. Page metadata for phones, tablets and print
head_extra = """
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<meta name="description" content="Analysis of NYC taxi trips (March 2019): demand, fares and tipping."/>
<style id="responsive-overrides">
  :root { --page-max: 980px; --gutter: clamp(14px, 4vw, 40px); }
  html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
  html, body { margin: 0; max-width: 100%; overflow-x: hidden; background: #fff; }

  /* Fluid reading column, safe-area aware for notched phones */
  body.jp-Notebook, .jp-Notebook {
    box-sizing: border-box;
    max-width: var(--page-max) !important;
    margin: 0 auto !important;
    padding: 12px max(var(--gutter), env(safe-area-inset-right)) 48px max(var(--gutter), env(safe-area-inset-left)) !important;
  }
  .jp-Cell, .jp-Cell-inputWrapper, .jp-Cell-outputWrapper, .jp-InputArea, .jp-OutputArea,
  .jp-OutputArea-child, .jp-RenderedText, .jp-RenderedHTMLCommon { min-width: 0; max-width: 100%; box-sizing: border-box; }

  /* Charts scale to the screen instead of overflowing */
  img, svg, canvas { max-width: 100% !important; height: auto !important; }
  .jp-RenderedImage { text-align: center; }

  /* Headings and prose */
  .jp-RenderedHTMLCommon { overflow-wrap: break-word; word-break: normal; }
  .jp-RenderedHTMLCommon h1 { font-size: clamp(1.55rem, 5.5vw, 2.2rem); line-height: 1.2; }
  .jp-RenderedHTMLCommon h2 { font-size: clamp(1.3rem, 4.5vw, 1.7rem); line-height: 1.25; margin-top: 1.6em; }
  .jp-RenderedHTMLCommon h3 { font-size: clamp(1.1rem, 3.8vw, 1.3rem); }
  .jp-RenderedHTMLCommon p, .jp-RenderedHTMLCommon li { line-height: 1.6; }

  /* Wide tables (markdown and DataFrames) scroll inside their own box, not the page */
  .jp-RenderedHTMLCommon table, .jp-RenderedHTML table, .dataframe {
    display: block; max-width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;
    border-collapse: collapse; margin-left: 0; margin-right: 0;
  }
  .jp-RenderedHTMLCommon table { font-size: 0.92em; }
  .jp-RenderedHTMLCommon th, .jp-RenderedHTMLCommon td { white-space: normal; min-width: 4.5em; }
  .jp-OutputArea-output.jp-RenderedHTML { overflow-x: auto; -webkit-overflow-scrolling: touch; }

  /* Code and text output: scroll sideways within the block */
  .highlight pre, .jp-RenderedText pre, pre {
    overflow-x: auto; max-width: 100%; white-space: pre; -webkit-overflow-scrolling: touch;
    font-size: clamp(11px, 2.9vw, 13px); line-height: 1.45; tab-size: 4;
  }

  /* Remove the fixed 64px In/Out prompt gutters on small screens */
  @media (max-width: 720px) {
    .jp-InputPrompt, .jp-OutputPrompt { display: none !important; }
    .jp-Cell-inputWrapper, .jp-Cell-outputWrapper { display: block !important; }
    .jp-RenderedHTMLCommon table { font-size: 0.82em; }
    .jp-RenderedHTMLCommon th, .jp-RenderedHTMLCommon td { padding: 4px 6px; }
  }

  /* Code visibility toggle */
  #code-toggle {
    position: fixed; right: max(12px, env(safe-area-inset-right)); bottom: max(12px, env(safe-area-inset-bottom));
    z-index: 50; padding: 10px 14px; border: 0; border-radius: 999px; cursor: pointer;
    background: #0b0b0b; color: #fff; font: 600 13px/1 system-ui, -apple-system, "Segoe UI", sans-serif;
    box-shadow: 0 2px 10px rgba(0,0,0,.25); min-height: 44px; min-width: 44px;
  }
  #code-toggle:focus-visible { outline: 3px solid #2a78d6; outline-offset: 2px; }
  body.hide-code .jp-CodeCell .jp-Cell-inputWrapper { display: none !important; }

  /* Tap-to-zoom charts */
  .jp-RenderedImage img { cursor: zoom-in; }
  #lightbox { position: fixed; inset: 0; z-index: 100; display: none; background: rgba(11,11,11,.92); flex-direction: column; }
  #lightbox.open { display: flex; }
  #lightbox .lb-bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 10px 14px;
    color: #fff; font: 500 13px/1.3 system-ui, -apple-system, "Segoe UI", sans-serif; }
  #lightbox button { min-height: 44px; min-width: 44px; padding: 0 16px; border: 0; border-radius: 999px; background: #fff; color: #0b0b0b;
    font: 600 14px system-ui, sans-serif; cursor: pointer; }
  #lightbox .lb-scroll { flex: 1; overflow: auto; -webkit-overflow-scrolling: touch; padding: 0 0 24px; text-align: center; }
  #lightbox img { background: #fff; width: auto !important; max-width: none !important; height: auto !important; cursor: default;
    min-width: 900px; max-height: none; }
  @media (min-width: 1100px) { #lightbox img { min-width: 0; max-width: 96vw !important; max-height: calc(100vh - 80px); } }

  /* Print / save-as-PDF: no toggle, no scrollbars, charts do not split across pages */
  @media print {
    #code-toggle, #lightbox { display: none !important; }
    body.jp-Notebook { max-width: none !important; padding: 0 !important; }
    img { break-inside: avoid; page-break-inside: avoid; }
    .jp-RenderedHTMLCommon table, pre { overflow: visible !important; white-space: pre-wrap; }
    h1, h2, h3 { break-after: avoid; }
  }
</style>
"""
html = re.sub(r'<meta[^>]*name="viewport"[^>]*/?>', "", html)
html = html.replace("</head>", head_extra + "</head>", 1)

# 3. Code toggle (report view by default on phones, code visible on large screens)
toggle = """
<button id="code-toggle" type="button" aria-pressed="false">Hide code</button>
<div id="lightbox" role="dialog" aria-modal="true" aria-label="Chart viewer">
  <div class="lb-bar"><span>Scroll or pinch to explore the chart</span><button id="lb-close" type="button">Close</button></div>
  <div class="lb-scroll"><img id="lb-img" alt=""/></div>
</div>
<script>
(function () {
  var btn = document.getElementById("code-toggle"), body = document.body;
  function set(hide) {
    body.classList.toggle("hide-code", hide);
    btn.textContent = hide ? "Show code" : "Hide code";
    btn.setAttribute("aria-pressed", String(hide));
  }
  set(window.matchMedia("(max-width: 720px)").matches);
  btn.addEventListener("click", function () { set(!body.classList.contains("hide-code")); });

  var lb = document.getElementById("lightbox"), lbImg = document.getElementById("lb-img"), last = null;
  function open(img) {
    last = img; lbImg.src = img.src; lbImg.alt = img.alt || "Chart";
    lb.classList.add("open"); body.style.overflow = "hidden"; document.getElementById("lb-close").focus();
  }
  function close() {
    lb.classList.remove("open"); body.style.overflow = ""; if (last) last.focus();
  }
  document.querySelectorAll(".jp-RenderedImage img").forEach(function (img) {
    img.setAttribute("tabindex", "0"); img.setAttribute("role", "button");
    img.setAttribute("aria-label", "Open chart full screen");
    img.addEventListener("click", function () { open(img); });
    img.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(img); } });
  });
  document.getElementById("lb-close").addEventListener("click", close);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && lb.classList.contains("open")) close(); });
})();
</script>
"""
html = html.replace("</body>", toggle + "</body>", 1)

OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")

import json, html, os

SP = r"C:\Users\ishat\AppData\Local\Temp\claude\421772d99a25f2fb\732e120e-2b91-4dfc-bda2-2925a51afa1e\scratchpad"
R = json.load(open(os.path.join(SP, "report", "report.json")))

CAT = {
    "columns": ("Columns", "col"),
    "beams": ("Beams", "beam"),
    "joists": ("Joists", "joist"),
    "trusses": ("Trusses", "joist"),
    "areas": ("Deck / bays", "deck"),
    "walls": ("Walls", "other"),
    "other": ("Headers / base plates / other", "other"),
}
e = html.escape


def n(v, d=0):
    return f"{v:,.{d}f}"


def summary_rows():
    out = []
    for s in R:
        b, a = s["counts_before"], s["counts"]
        def cell(k):
            x, y = b.get(k, 0), a.get(k, 0)
            if not x and not y:
                return '<td class="num dim">–</td>'
            d = y - x
            delta = f' <span class="delta {"up" if d > 0 else "down"}">{"+" if d > 0 else ""}{d}</span>' if d else ""
            return f'<td class="num">{y}{delta}</td>'
        jt = {k: b.get("joists", 0) + b.get("trusses", 0) for k in ["x"]}["x"], a.get("joists", 0) + a.get("trusses", 0)
        jcell = (f'<td class="num">{jt[1]}' + (f' <span class="delta up">+{jt[1]-jt[0]}</span>' if jt[1] > jt[0] else "") + "</td>") if jt[1] or jt[0] else '<td class="num dim">–</td>'
        grid = f'{s["grid"][0]} × {s["grid"][1]}' if s.get("grid") else "–"
        miss = len(s["missed"])
        out.append(
            f'<tr><th scope="row"><a href="#{e(s["sheet"].replace(".", "-"))}">{e(s["sheet"])}</a><span class="sub">{e(s["project"])}</span></th>'
            f'<td class="num">{grid}</td>{cell("columns")}{cell("beams")}{jcell}{cell("areas")}'
            f'<td class="num">{"<span class=\'chip ok\'>0</span>" if not miss else f"<span class=\'chip warn\'>{miss}</span>"}</td></tr>'
        )
    return "\n".join(out)


def qty_table(s):
    rows = []
    last = None
    for r in s["rows"]:
        label, cls = CAT.get(r["category"], (r["category"], "other"))
        if r["category"] != last:
            rows.append(f'<tr class="grp"><th colspan="5" scope="colgroup"><span class="sw {cls}"></span>{e(label)}</th></tr>')
            last = r["category"]
        qty = n(r["count"])
        lf = n(r["lf"]) if r["lf"] else "–"
        sf = n(r["sf"]) if r["sf"] else "–"
        z = f'<span class="chip zoom">{r["zoom"]}</span>' if r["zoom"] else '<span class="dim">–</span>'
        des = r["designation"]
        if des == "BEAM":
            des = "BEAM — no size on plan (rename)"
        rows.append(f'<tr><td>{e(des)}{(" <span class=sub>" + e(r["role"]) + "</span>") if r["role"] and r["role"] not in des else ""}</td><td class="num">{qty}</td><td class="num">{lf}</td><td class="num">{sf}</td><td class="num">{z}</td></tr>')
    return "\n".join(rows)


def part_list(s):
    items = []
    for l in s["log"]:
        c = " · ".join(f'{v} {CAT.get(k, (k,))[0].lower()}' for k, v in l["counts"].items()) or "nothing to take off"
        warn = f'<span class="chip warn">{l["missed"]} to check</span>' if l["missed"] else '<span class="chip ok">checked</span>'
        items.append(f'<li><span class="pn">Part {l["part"]}</span><span class="pc">{e(c)}</span>{warn}</li>')
    return "\n".join(items)


sections = []
for s in R:
    sid = s["sheet"].replace(".", "-")
    miss = ""
    if s["missed"]:
        miss = '<p class="note warn-note"><b>Still to check by eye:</b> ' + ", ".join(e(m["designation"]) for m in s["missed"]) + "</p>"
    rules = '<span class="chip rules">House rules</span>' if s["rules"] else '<span class="chip plain">No house rules</span>'
    removed = f' · {s["removed"]} false column{"s" if s["removed"] != 1 else ""} removed' if s.get("removed") else ""
    sections.append(f'''
<section class="sheet" id="{e(sid)}">
  <header class="sheet-head">
    <div>
      <p class="eyebrow">{e(s["project"])} · PDF page {s["page"]}</p>
      <h2><span class="num-mark">{e(s["sheet"])}</span> {e(s["title"])}</h2>
      <p class="meta">{rules} <span>Scale {e(s["scale"] or "not found")}</span> <span>Split into {s["grid"][0]} × {s["grid"][1]} parts</span>{e(removed)}</p>
    </div>
  </header>
  <div class="sheet-body">
    <figure class="plan">
      <div class="plan-scroll" tabindex="0" aria-label="Sheet {e(s["sheet"])} with take-off markups; scroll to pan">
        <img src="data:image/jpeg;base64,{s["img"]}" width="{s["w"]}" height="{s["h"]}" alt="Sheet {e(s["sheet"])} with the parts grid and every take-off markup">
      </div>
      <figcaption>Dashed blue: the parts the sheet was split into. Thick lines and big circles: found by the zoomed check. Dashed beams: no size on the plan.</figcaption>
    </figure>
    <div class="side">
      <h3>Quantities</h3>
      <div class="tbl-wrap">
      <table class="qty">
        <thead><tr><th scope="col">Size / mark</th><th scope="col" class="num">Qty</th><th scope="col" class="num">LF</th><th scope="col" class="num">SF</th><th scope="col" class="num">Zoom</th></tr></thead>
        <tbody>{qty_table(s)}</tbody>
      </table>
      </div>
      <h3>Part by part</h3>
      <ul class="parts">{part_list(s)}</ul>
      {miss}
    </div>
  </div>
</section>''')

page = f'''<title>Zoomed Takeoff Check</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a takeoff report - summary sheet first, then one plate per drawing (plan left, quantities right). */
:root {{
  --paper: #f4f6f8;
  --sheet: #ffffff;
  --ink: #18202b;
  --ink-2: #4a5566;
  --ink-3: #7a8494;
  --rule: #d8dee6;
  --grid: #2b5bd7;
  --col: #0b9e52;
  --beam: #c41a8c;
  --joist: #1f6bd9;
  --deck: #e8960c;
  --other: #707884;
  --warn-bg: #fff3dc;
  --warn: #9a5a00;
  --ok-bg: #e3f5ea;
  --ok: #17703f;
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", Roboto, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --paper: #0f1318; --sheet: #171c23; --ink: #e8ecf1; --ink-2: #b3bcc8; --ink-3: #8590a0; --rule: #2b333e;
    --grid: #7d9fff; --col: #3fd18a; --beam: #ff5cc0; --joist: #5ea2ff; --deck: #ffb53d; --other: #9aa3ae;
    --warn-bg: #3a2a0c; --warn: #ffc56b; --ok-bg: #12301f; --ok: #6fe0a0; color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --paper: #0f1318; --sheet: #171c23; --ink: #e8ecf1; --ink-2: #b3bcc8; --ink-3: #8590a0; --rule: #2b333e;
  --grid: #7d9fff; --col: #3fd18a; --beam: #ff5cc0; --joist: #5ea2ff; --deck: #ffb53d; --other: #9aa3ae;
  --warn-bg: #3a2a0c; --warn: #ffc56b; --ok-bg: #12301f; --ok: #6fe0a0; color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--paper); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 1280px; margin: 0 auto; padding-block: 40px 64px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 40px; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; margin: 0; }}
h1 {{ font-size: clamp(30px, 4.4vw, 46px); font-weight: 800; letter-spacing: -0.01em; line-height: 1.08; }}
h2 {{ font-size: clamp(20px, 2.4vw, 26px); font-weight: 700; }}
h3 {{ font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-2); }}
p {{ margin: 0; }}
.eyebrow {{ font: 500 12px/1.3 var(--mono); text-transform: uppercase; letter-spacing: 0.1em; color: var(--grid); }}
.intro {{ display: grid; gap: 14px; max-width: 70ch; }}
.intro p {{ color: var(--ink-2); }}
.steps {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 8px; }}
.step {{ border-top: 2px dashed var(--grid); padding-top: 10px; display: grid; gap: 4px; }}
.step b {{ font-family: var(--display); font-size: 16px; }}
.step span {{ color: var(--ink-2); font-size: 14px; }}
.tbl-wrap {{ overflow-x: auto; min-width: 0; }}
table {{ border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
thead th {{ font: 600 11px/1.3 var(--mono); text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-3); border-bottom: 1.5px solid var(--ink-3); }}
.num {{ text-align: right; font-family: var(--mono); white-space: nowrap; }}
.dim {{ color: var(--ink-3); }}
.sub {{ display: block; font-size: 12px; color: var(--ink-3); font-weight: 400; }}
.summary {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px; padding: 6px 4px; }}
.summary th[scope=row] a {{ color: var(--ink); font-family: var(--display); font-weight: 700; text-decoration: none; border-bottom: 1px dashed var(--grid); }}
.summary th[scope=row] a:hover, .summary th[scope=row] a:focus-visible {{ color: var(--grid); }}
.delta {{ font-size: 12px; margin-left: 4px; }}
.delta.up {{ color: var(--ok); }}
.delta.down {{ color: var(--warn); }}
.chip {{ display: inline-block; font: 500 11.5px/1 var(--mono); padding: 4px 7px; border-radius: 999px; white-space: nowrap; }}
.chip.ok {{ background: var(--ok-bg); color: var(--ok); }}
.chip.warn {{ background: var(--warn-bg); color: var(--warn); }}
.chip.zoom {{ background: color-mix(in srgb, var(--grid) 16%, transparent); color: var(--grid); }}
.chip.rules {{ background: color-mix(in srgb, var(--col) 16%, transparent); color: var(--col); }}
.chip.plain {{ background: color-mix(in srgb, var(--ink-3) 16%, transparent); color: var(--ink-2); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 13px; color: var(--ink-2); }}
.legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
.sw {{ width: 18px; height: 4px; border-radius: 2px; display: inline-block; margin-right: 6px; vertical-align: middle; }}
.sw.col {{ background: var(--col); height: 10px; width: 10px; border-radius: 50%; }}
.sw.beam {{ background: var(--beam); }}
.sw.joist {{ background: var(--joist); }}
.sw.deck {{ background: var(--deck); opacity: 0.6; height: 10px; }}
.sw.other {{ background: var(--other); }}
.sw.part {{ background: none; border-top: 2px dashed var(--grid); height: 0; border-radius: 0; }}
.sheet {{ background: var(--sheet); border: 1px solid var(--rule); border-radius: 8px; overflow: hidden; scroll-margin-top: 16px; }}
.sheet-head {{ padding: 18px 20px 14px; border-bottom: 1px solid var(--rule); display: grid; gap: 6px; }}
.num-mark {{ font-family: var(--mono); font-weight: 500; color: var(--grid); margin-right: 6px; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: center; color: var(--ink-3); font-size: 13px; margin-top: 6px; }}
.sheet-body {{ display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr); }}
.plan {{ margin: 0; padding: 14px; border-right: 1px solid var(--rule); display: grid; gap: 8px; align-content: start; min-width: 0; }}
.plan-scroll {{ overflow: auto; border: 1px solid var(--rule); border-radius: 4px; background: #fff; max-height: 78vh; }}
.plan-scroll:focus-visible {{ outline: 2px solid var(--grid); outline-offset: 2px; }}
.plan img {{ display: block; width: 100%; height: auto; max-width: none; }}
.plan.big img {{ width: 220%; }}
.plan figcaption {{ font-size: 12.5px; color: var(--ink-3); }}
.zoom-btn {{ justify-self: start; font: 500 13px var(--body); color: var(--grid); background: none; border: 1px solid var(--grid); border-radius: 4px; padding: 5px 10px; cursor: pointer; }}
.zoom-btn:hover {{ background: color-mix(in srgb, var(--grid) 10%, transparent); }}
.zoom-btn:focus-visible {{ outline: 2px solid var(--grid); outline-offset: 2px; }}
.side {{ padding: 16px 18px 20px; display: grid; gap: 14px; align-content: start; min-width: 0; }}
.qty td:first-child {{ font-family: var(--mono); font-size: 13px; }}
.qty tr.grp th {{ font: 700 12.5px/1.3 var(--display); color: var(--ink); padding-top: 14px; border-bottom-color: var(--ink-3); }}
.parts {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }}
.parts li {{ display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: baseline; font-size: 13.5px; border-bottom: 1px dashed var(--rule); padding-bottom: 6px; }}
.pn {{ font: 500 12.5px var(--mono); color: var(--grid); white-space: nowrap; }}
.pc {{ color: var(--ink-2); min-width: 0; }}
.note {{ font-size: 13.5px; color: var(--ink-2); }}
.warn-note {{ background: var(--warn-bg); color: var(--warn); padding: 8px 10px; border-radius: 4px; }}
.limits {{ display: grid; gap: 10px; max-width: 75ch; }}
.limits ul {{ margin: 0; padding-left: 18px; color: var(--ink-2); display: grid; gap: 6px; }}
@media (max-width: 900px) {{
  .sheet-body {{ grid-template-columns: minmax(0, 1fr); }}
  .plan {{ border-right: 0; border-bottom: 1px solid var(--rule); }}
}}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style>
<div class="wrap">
  <header class="intro">
    <p class="eyebrow">Auto Takeoff · zoomed check · engine run on your PDFs</p>
    <h1>Zoomed Takeoff Check</h1>
    <p>Every sheet is split into parts and each part is checked zoomed in, one by one, the way you would check it in Revu. Below is the final take-off on six sheets from three of your drawing sets, with the parts each sheet was split into and every markup drawn on it.</p>
    <div class="steps">
      <div class="step"><b>Split</b><span>The drawing area is cut into 4, 6, 9 or more parts, more for a busy sheet. Parts overlap by about 2 ft.</span></div>
      <div class="step"><b>Zoom in</b><span>Every small shape and every line in the part is read at full detail, curves included.</span></div>
      <div class="step"><b>Check one by one</b><span>Columns, beams, joists and deck callouts are checked. Wrong ones (arrows, grid bubbles) are removed.</span></div>
      <div class="step"><b>Join</b><span>The parts are put back together. Anything still not taken off is listed per part.</span></div>
    </div>
  </header>

  <section aria-labelledby="sum-h" style="display:grid;gap:12px">
    <h3 id="sum-h">All sheets — after the zoomed check (change from before)</h3>
    <div class="summary tbl-wrap">
      <table>
        <thead><tr><th scope="col">Sheet</th><th scope="col" class="num">Parts</th><th scope="col" class="num">Columns</th><th scope="col" class="num">Beams</th><th scope="col" class="num">Joists / trusses</th><th scope="col" class="num">Deck / bays</th><th scope="col" class="num">To check</th></tr></thead>
        <tbody>{summary_rows()}</tbody>
      </table>
    </div>
    <div class="legend" aria-label="Markup colours">
      <span><i class="sw col"></i>Column</span><span><i class="sw beam"></i>Beam</span><span><i class="sw joist"></i>Joist / truss</span><span><i class="sw deck"></i>Deck / joist bay</span><span><i class="sw other"></i>Header / other</span><span><i class="sw part"></i>Zoom part</span>
    </div>
  </section>

  {"".join(sections)}

  <section class="limits" aria-labelledby="lim-h">
    <h3 id="lim-h">What the zoomed check still can't do</h3>
    <ul>
      <li>Deck on a decking plan with no beams taken off (AC Retreat S4.03a) gets no bay yet. Teach me your deck rules and I'll add them, like the walls.</li>
      <li>Beams with no size printed are added as "BEAM — no size on plan". Rename them with ✏️ in the Detected list.</li>
      <li>The joist check only steps in when the first pass framed nothing for a callout. On these sheets the first pass framed every joist callout, so it added nothing (tested on its own on StudioRes, 89–99% of its lines sat exactly on the first pass's joists).</li>
      <li>Columns drawn only as part of a wall, with no symbol of their own, are not added. They are listed to check instead (Home2 S-1.00: one HSS10X10X5/8).</li>
      <li>Home2 S-1.00 "before" counted 84 columns, but 10 of them were grid bubbles. Now 78 real columns: every column size label on the sheet has its column, except the one above. 2 columns are still unnamed.</li>
      <li>Walls: waiting for your rules.</li>
    </ul>
  </section>
</div>
<script>
document.querySelectorAll('.plan').forEach(function (fig) {{
  var b = document.createElement('button');
  b.type = 'button'; b.className = 'zoom-btn'; b.textContent = 'Zoom in on the sheet';
  b.addEventListener('click', function () {{
    var big = fig.classList.toggle('big');
    b.textContent = big ? 'Show the whole sheet' : 'Zoom in on the sheet';
  }});
  fig.insertBefore(b, fig.firstChild);
}});
</script>
'''
open(os.path.join(SP, "zoomed-takeoff-check.html"), "w", encoding="utf-8").write(page)
print(len(page) // 1024, "KB")

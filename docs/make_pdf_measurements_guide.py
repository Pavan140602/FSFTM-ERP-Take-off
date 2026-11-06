"""Build the PDF Measurements master-flow guide (Florida Steel branding)."""
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, Flowable, CondPageBreak,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = sys.argv[1]
LOGO = sys.argv[2]

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Arial", F + "arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", F + "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", F + "ariali.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", F + "arialbi.ttf"))
pdfmetrics.registerFont(TTFont("Consolas", F + "consola.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("Arial", 0, 0, "Arial"); addMapping("Arial", 1, 0, "Arial-Bold")
addMapping("Arial", 0, 1, "Arial-Italic"); addMapping("Arial", 1, 1, "Arial-BoldItalic")

MAROON = colors.HexColor("#830000")
GREY = colors.HexColor("#616364")
INK = colors.HexColor("#222222")
LIGHT = colors.HexColor("#F4F1F1")
RULE = colors.HexColor("#D9D4D4")
BLUE = colors.HexColor("#1F5FBF")

ss = {}
ss["body"] = ParagraphStyle("body", fontName="Arial", fontSize=9.6, leading=13.4, textColor=INK, spaceAfter=5)
ss["small"] = ParagraphStyle("small", parent=ss["body"], fontSize=8.4, leading=11)
ss["cell"] = ParagraphStyle("cell", parent=ss["body"], fontSize=8.6, leading=11.2, spaceAfter=0)
ss["cellb"] = ParagraphStyle("cellb", parent=ss["cell"], fontName="Arial-Bold")
ss["head"] = ParagraphStyle("head", parent=ss["cell"], fontName="Arial-Bold", textColor=colors.white)
ss["h1"] = ParagraphStyle("h1", fontName="Arial-Bold", fontSize=19, leading=23, textColor=MAROON, spaceBefore=4, spaceAfter=8, keepWithNext=1)
ss["h2"] = ParagraphStyle("h2", fontName="Arial-Bold", fontSize=13, leading=17, textColor=MAROON, spaceBefore=10, spaceAfter=5, keepWithNext=1)
ss["h3"] = ParagraphStyle("h3", fontName="Arial-Bold", fontSize=10.6, leading=14, textColor=GREY, spaceBefore=7, spaceAfter=3, keepWithNext=1)
ss["bullet"] = ParagraphStyle("bullet", parent=ss["body"], leftIndent=14, bulletIndent=4, spaceAfter=2.5)
ss["bullet2"] = ParagraphStyle("bullet2", parent=ss["bullet"], leftIndent=28, bulletIndent=18)
ss["code"] = ParagraphStyle("code", fontName="Consolas", fontSize=8.6, leading=11.5, textColor=INK,
                            backColor=LIGHT, borderPadding=(4, 6, 4, 6), leftIndent=6, rightIndent=6,
                            spaceBefore=3, spaceAfter=7)
ss["note"] = ParagraphStyle("note", parent=ss["body"], backColor=colors.HexColor("#FBF3E6"),
                            borderColor=colors.HexColor("#E3B66B"), borderWidth=0.6,
                            borderPadding=(6, 8, 6, 8), leftIndent=8, rightIndent=8,
                            spaceBefore=6, spaceAfter=10)


def P(t, s="body"):
    return Paragraph(t, ss[s])


def B(items, s="bullet"):
    return [Paragraph(i, ss[s], bulletText="•") for i in items]


def K(t):
    return f'<font name="Consolas" color="#830000">{t}</font>'


def H1(t):
    p = Paragraph(t, ss["h1"]); p._toc = (0, t); return p


def H2(t):
    p = Paragraph(t, ss["h2"]); p._toc = (1, t); return p


def table(rows, widths, header=True, zebra=True):
    data = []
    for r_i, row in enumerate(rows):
        out = []
        for c in row:
            if isinstance(c, str):
                style = "head" if (header and r_i == 0) else "cell"
                out.append(Paragraph(c, ss[style]))
            else:
                out.append(c)
        data.append(out)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
    ]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), MAROON))
    if zebra:
        for i in range(1 if header else 0, len(data)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(cmds))
    return t


# ── Flowables ──────────────────────────────────────────────────────────────
class MasterFlow(Flowable):
    """Numbered master-flow diagram: two columns, snake order."""
    STEPS = [
        ("Upload & open", "Takeoff > PDF Measurements > Current & recent drawings. Upload; it opens by itself."),
        ("Check the sheets", "Thumbnails: sheet label, page no., scale pill (green = set, orange = not set)."),
        ("Set the scale", "Status-bar scale / Scale tab / thumbnail pill > Apply Scale to Pages, or Calibrate."),
        ("Run Auto Takeoff", "Left rail > Auto. Tick member types, keep House framing rules on, Run."),
        ("Review the results", "Detected markups, filters, Not taken off (n), Select same profile, fix profiles."),
        ("Measure by hand", "Right tool strip or keys. Tool Chest structural tools. Snap + straight lines."),
        ("Organise", "Subject / Label / Caption / colour, Markups list (all sheets), Status, Legend."),
        ("Save", "Ctrl+S (also auto-saves). Everything is stored on the ERP server."),
        ("Output", "Download PDF (vector + dimensions), CSV summary, extract / combine pages."),
        ("Close", "The × on the drawing tab (top right) saves and closes."),
    ]

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.box_h = 0.86 * inch
        self.gap = 0.22 * inch
        self.height = 5 * self.box_h + 4 * self.gap + 0.1 * inch

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        colw = (self.width - 0.7 * inch) / 2
        xs = [0, colw + 0.7 * inch]
        pos = []
        for i in range(10):
            col = 0 if i < 5 else 1
            row = i if i < 5 else i - 5
            x = xs[col]
            y = self.height - (row + 1) * self.box_h - row * self.gap
            pos.append((x, y))
        # arrows
        c.setStrokeColor(GREY); c.setFillColor(GREY); c.setLineWidth(1.2)
        for i in range(9):
            x0, y0 = pos[i]; x1, y1 = pos[i + 1]
            if i == 4:  # column jump
                sx, sy = x0 + colw, y0 + self.box_h / 2
                ex, ey = x1, y1 + self.box_h / 2
                mx = (sx + ex) / 2
                p = c.beginPath(); p.moveTo(sx, sy); p.lineTo(mx, sy); p.lineTo(mx, ey); p.lineTo(ex - 5, ey)
                c.drawPath(p, stroke=1, fill=0)
                self._head(ex, ey, "right")
            else:
                ax = x0 + colw / 2
                if i < 4:
                    c.line(ax, y0, ax, y1 + self.box_h + 5); self._head(ax, y1 + self.box_h, "down")
                else:
                    c.line(ax, y0, ax, y1 + self.box_h + 5); self._head(ax, y1 + self.box_h, "down")
        for i, (title, desc) in enumerate(self.STEPS):
            x, y = pos[i]
            c.setFillColor(colors.white); c.setStrokeColor(RULE); c.setLineWidth(0.8)
            c.roundRect(x, y, colw, self.box_h, 6, stroke=1, fill=1)
            c.setFillColor(MAROON if i < 5 else GREY)
            c.roundRect(x, y, 0.42 * inch, self.box_h, 6, stroke=0, fill=1)
            c.rect(x + 0.3 * inch, y, 0.12 * inch, self.box_h, stroke=0, fill=1)
            c.setFillColor(colors.white); c.setFont("Arial-Bold", 15)
            c.drawCentredString(x + 0.21 * inch, y + self.box_h / 2 - 5, str(i + 1))
            c.setFillColor(MAROON); c.setFont("Arial-Bold", 10.5)
            c.drawString(x + 0.52 * inch, y + self.box_h - 16, title)
            p = Paragraph(desc, ParagraphStyle("d", fontName="Arial", fontSize=8.3, leading=10.4, textColor=INK))
            w, h = p.wrap(colw - 0.62 * inch, self.box_h)
            p.drawOn(c, x + 0.52 * inch, y + self.box_h - 22 - h)

    def _head(self, x, y, d):
        c = self.canv; s = 5
        p = c.beginPath()
        if d == "down":
            p.moveTo(x, y); p.lineTo(x - s, y + s * 1.6); p.lineTo(x + s, y + s * 1.6)
        else:
            p.moveTo(x, y); p.lineTo(x - s * 1.6, y + s); p.lineTo(x - s * 1.6, y - s)
        p.close(); c.drawPath(p, stroke=0, fill=1)


class ScreenMap(Flowable):
    """Wireframe of the PDF Measurements workspace with numbered callouts."""

    def __init__(self, width):
        super().__init__()
        self.width = width
        self.height = 3.9 * inch

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W, H = self.width, self.height

        def region(x, y, w, h, fill, label, num, tc=INK):
            c.setFillColor(fill); c.setStrokeColor(GREY); c.setLineWidth(0.6)
            c.rect(x, y, w, h, stroke=1, fill=1)
            c.setFillColor(tc); c.setFont("Arial", 7.6)
            c.drawString(x + 18, y + h / 2 - 3, label)
            c.setFillColor(MAROON); c.circle(x + 9, y + h / 2, 6.2, stroke=0, fill=1)
            c.setFillColor(colors.white); c.setFont("Arial-Bold", 7.4)
            c.drawCentredString(x + 9, y + h / 2 - 2.6, str(num))

        top = H
        region(0, top - 16, W, 16, colors.HexColor("#ECECEC"), "Menu bar: File  Edit  View  Document  Measure  Markup  Tools  Window  Help        [drawing tab ×]", 1)
        region(0, top - 34, W, 18, colors.HexColor("#F6F6F6"), "Toolbar: Pages · Legend · Show/Hide · Names · Values · Combine · New · Save · Download PDF · Fullscreen ...", 2)
        region(0.62 * inch, top - 54, W - 1.25 * inch, 18, colors.HexColor("#FFF7E0"), "Properties bar (floats while a tool is active or markups are selected)", 3)
        # left rail
        rail_w = 0.5 * inch
        c.setFillColor(colors.HexColor("#F0F0F0")); c.setStrokeColor(GREY)
        c.rect(0, 38, rail_w, top - 34 - 38, stroke=1, fill=1)
        names = ["Thumbs", "Index", "Measure", "Tools", "Scale", "AI", "Auto", "Search"]
        c.setFont("Arial", 6.4); c.setFillColor(GREY)
        for i, n in enumerate(names):
            c.drawCentredString(rail_w / 2, top - 52 - i * 19, n)
        c.setFillColor(MAROON); c.circle(rail_w / 2, 52, 6.2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Arial-Bold", 7.4); c.drawCentredString(rail_w / 2, 49.4, "4")
        # left panel
        lp_w = 1.25 * inch
        c.setFillColor(colors.HexColor("#FAFAFA")); c.rect(rail_w, 38 + 0.95 * inch, lp_w, top - 34 - 38 - 0.95 * inch - 20, stroke=1, fill=1)
        c.setFillColor(INK); c.setFont("Arial", 7.4)
        c.drawString(rail_w + 18, top - 75, "Left panel")
        c.setFont("Arial", 6.6); c.setFillColor(GREY)
        for i, t in enumerate(["thumbnails, Auto Takeoff,", "scale, Tool Chest ...", "(drag edge to resize)"]):
            c.drawString(rail_w + 8, top - 90 - i * 10, t)
        c.setFillColor(MAROON); c.circle(rail_w + 9, top - 72, 6.2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Arial-Bold", 7.4); c.drawCentredString(rail_w + 9, top - 74.6, "5")
        # drawing
        dx = rail_w + lp_w; dw = W - dx - 0.42 * inch
        c.setFillColor(colors.white); c.rect(dx, 38 + 0.95 * inch, dw, top - 54 - 38 - 0.95 * inch, stroke=1, fill=1)
        c.setStrokeColor(colors.HexColor("#B8C7E6")); c.setLineWidth(0.5)
        for gx in range(6):
            xx = dx + 20 + gx * (dw - 40) / 5
            c.line(xx, 38 + 0.95 * inch + 12, xx, top - 66)
        c.setStrokeColor(MAROON); c.setLineWidth(2.2)
        c.line(dx + 40, top - 120, dx + dw - 60, top - 120)
        c.setStrokeColor(BLUE); c.setLineWidth(5); c.setStrokeAlpha(0.35)
        c.line(dx + 50, top - 160, dx + dw - 90, top - 160); c.setStrokeAlpha(1)
        c.setFillColor(INK); c.setFont("Arial-Bold", 8.2)
        c.drawCentredString(dx + dw / 2, top - 98, "Drawing (sheet) — markups drawn here")
        c.setFillColor(MAROON); c.circle(dx + 12, top - 98 + 3, 6.2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Arial-Bold", 7.4); c.drawCentredString(dx + 12, top - 98 + 0.4, "6")
        # right strip
        c.setFillColor(colors.HexColor("#F0F0F0")); c.setStrokeColor(GREY); c.setLineWidth(0.6)
        c.rect(W - 0.42 * inch, 38 + 0.95 * inch, 0.42 * inch, top - 54 - 38 - 0.95 * inch, stroke=1, fill=1)
        c.saveState(); c.translate(W - 0.21 * inch, 38 + 0.95 * inch + 30); c.rotate(90)
        c.setFillColor(GREY); c.setFont("Arial", 7.2); c.drawString(0, -2.5, "Tool strip (measure + markup tools)")
        c.restoreState()
        c.setFillColor(MAROON); c.circle(W - 0.21 * inch, top - 66, 6.2, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Arial-Bold", 7.4); c.drawCentredString(W - 0.21 * inch, top - 68.6, "7")
        # markups list
        region(rail_w, 38, W - rail_w, 0.95 * inch, colors.HexColor("#F7F3F3"), "Markups list (Alt+L): Subject · Label · Length / Area · Unit · Material · Status ...  This sheet | All sheets", 8)
        c.setStrokeColor(RULE)
        for i in range(1, 4):
            c.line(rail_w + 18, 38 + 0.95 * inch - 0.5 * inch + 0 - i * 9 + 22, W - 10, 38 + 0.95 * inch - 0.5 * inch - i * 9 + 22)
        region(0, 18, W, 18, colors.HexColor("#ECECEC"), "Status bar: Select · Pan · Text Select · page no. · SNAP · REUSE · scale button · units · SYNC · zoom · sheet size · X/Y", 9)


# ── Page decoration ────────────────────────────────────────────────────────
def on_page(c, doc):
    c.saveState()
    w, h = letter
    c.setFillColor(MAROON); c.rect(0, h - 0.18 * inch, w * 0.62, 0.18 * inch, stroke=0, fill=1)
    c.setFillColor(GREY); c.rect(w * 0.62, h - 0.18 * inch, w * 0.38, 0.18 * inch, stroke=0, fill=1)
    c.drawImage(LOGO, 0.75 * inch, h - 0.72 * inch, width=1.5 * inch, height=0.375 * inch, mask="auto")
    c.setFont("Arial", 8); c.setFillColor(GREY)
    c.drawRightString(w - 0.75 * inch, h - 0.52 * inch, "PDF Measurements — Master Flow & User Guide")
    c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(0.75 * inch, h - 0.82 * inch, w - 0.75 * inch, h - 0.82 * inch)
    c.line(0.75 * inch, 0.62 * inch, w - 0.75 * inch, 0.62 * inch)
    c.setFont("Arial", 7.6)
    c.drawString(0.75 * inch, 0.45 * inch, "Florida Steel Frame & Truss Manufacturing LLC · Internal ERP guide")
    c.drawRightString(w - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    c.restoreState()


def on_cover(c, doc):
    c.saveState()
    w, h = letter
    c.setFillColor(MAROON); c.rect(0, h - 0.5 * inch, w * 0.62, 0.5 * inch, stroke=0, fill=1)
    c.setFillColor(GREY); c.rect(w * 0.62, h - 0.5 * inch, w * 0.38, 0.5 * inch, stroke=0, fill=1)
    c.setFillColor(MAROON); c.rect(0, 0, w * 0.62, 0.32 * inch, stroke=0, fill=1)
    c.setFillColor(GREY); c.rect(w * 0.62, 0, w * 0.38, 0.32 * inch, stroke=0, fill=1)
    c.restoreState()


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if hasattr(f, "_toc"):
            level, text = f._toc
            key = "h" + str(abs(hash(text)))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


doc = Doc(OUT, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
          topMargin=1.0 * inch, bottomMargin=0.8 * inch,
          title="PDF Measurements — Master Flow & User Guide",
          author="Florida Steel Frame & Truss Manufacturing LLC",
          subject="ERP PDF Measurements (takeoff) guide")
doc._hseq = 0
fw = letter[0] - 1.5 * inch
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[Frame(0.75 * inch, 0.8 * inch, fw, letter[1] - 1.6 * inch, id="c")], onPage=on_cover),
    PageTemplate(id="main", frames=[Frame(0.75 * inch, 0.8 * inch, fw, letter[1] - 1.8 * inch, id="m")], onPage=on_page),
])

S = []
from reportlab.platypus.doctemplate import NextPageTemplate

# ── Cover ──────────────────────────────────────────────────────────────────
S += [Spacer(1, 1.1 * inch), Image(LOGO, width=5.2 * inch, height=1.3 * inch), Spacer(1, 0.55 * inch)]
S.append(Paragraph("PDF Measurements", ParagraphStyle("ct", fontName="Arial-Bold", fontSize=34, leading=40, textColor=MAROON, alignment=TA_CENTER)))
S.append(Paragraph("Master Flow &amp; User Guide", ParagraphStyle("cs", fontName="Arial", fontSize=19, leading=25, textColor=GREY, alignment=TA_CENTER)))
S.append(Spacer(1, 0.35 * inch))
S.append(Paragraph("How to take off a drawing set in the ERP, from upload to the finished, marked-up PDF: "
                   "scale, Auto Takeoff, Bluebeam Revu-style tools, legends, saving and sharing.",
                   ParagraphStyle("cd", fontName="Arial", fontSize=11, leading=16, textColor=INK, alignment=TA_CENTER, leftIndent=40, rightIndent=40)))
S.append(Spacer(1, 1.3 * inch))
S.append(Paragraph("Florida Steel Frame &amp; Truss Manufacturing LLC<br/>ERP module: Takeoff &gt; PDF Measurements<br/>Edition: 6 November 2026 · covers every change in <font name='Consolas'>deliveries/</font> (18 delivery folders)",
                   ParagraphStyle("cf", fontName="Arial", fontSize=9.5, leading=14, textColor=GREY, alignment=TA_CENTER)))
S += [NextPageTemplate("main"), PageBreak()]

# ── Contents ───────────────────────────────────────────────────────────────
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle("t0", fontName="Arial-Bold", fontSize=10.5, leading=16, textColor=MAROON, leftIndent=0),
    ParagraphStyle("t1", fontName="Arial", fontSize=9.2, leading=13, textColor=INK, leftIndent=16),
]
S += [Paragraph("Contents", ss["h1"]), toc, PageBreak()]

# ── 1. About ───────────────────────────────────────────────────────────────
S.append(H1("1. What PDF Measurements is"))
S.append(P("PDF Measurements is the ERP's drawing takeoff workspace. It looks and works like Bluebeam Revu, and it adds "
           "<b>Auto Takeoff</b>, which reads structural and cold-formed steel (CFS) drawings and places the markups for you. "
           "Every markup is saved on the ERP server against the project, so the whole team sees the same takeoff."))
S.append(P("You open it from <b>Takeoff &gt; PDF Measurements</b> (address <font name='Consolas'>/takeoff?tab=measurements</font>)."))
S.append(P("There are two ways to take off, and you normally use both:", "body"))
S += B([
    "<b>Auto Takeoff</b>: columns, beams, joists, trusses, deck, CFS walls (with studs and header areas), headers, jambs, "
    "shear and strap-braced walls, holdowns, base plates, stairs and more. It reads the schedules, legends and sheet titles first, "
    "the way an estimator does. The rules work without AI; an AI step is optional and uses your own key.",
    "<b>Manual Revu tools</b>: Length, Polylength, Area, Count, Volume and the other measure tools, plus markups "
    "(Text Box, Cloud, Cloud+, Callout, Highlight ...), the Tool Chest of structural tools, legends and the Markups list.",
])
S.append(P("<b>Who this guide is for:</b> anyone receiving a copy of this ERP who needs to understand the takeoff workflow "
           "and test it. Section 2 covers setting it up on another PC; section 3 is the one-page master flow; the rest explains each step."))

# ── 2. Setup ───────────────────────────────────────────────────────────────
S.append(H1("2. Before you start (setting up on another PC)"))
S.append(P("Share the <b>whole project folder</b> (zipped), but <b>leave out</b> <font name='Consolas'>node_modules</font>: it is very large and "
           "built for one machine. The receiving PC needs Node.js, Python with the backend installed, and PostgreSQL."))
S.append(table([
    ["Step", "What to do", "Notes"],
    ["1. Install the frontend", f"In the project folder and in {K('frontend')}: {K('npm ci')}",
     "Installs everything, including <b>pdf-lib</b>, which page tools and Download PDF need."],
    ["2. Database", "Start PostgreSQL.", "Projects, drawings and markups live in the database, not in the folder (see section 14)."],
    ["3. Backend", f"Start it on port 8000, e.g. {K('openconstructionerp serve --port 8000')}",
     "No hot reload: <b>restart the backend</b> after any backend update, or Auto Takeoff runs old rules."],
    ["4. Frontend", f"In {K('frontend')}: {K('npm run dev')} then open {K('http://localhost:5173')}", "Hot-reloads. After updates press <b>Ctrl+Shift+R</b>."],
    ["5. Sign in", "Sign in as the administrator. Admins add people under <b>Users &gt; Create account</b>.",
     "Password: 12+ characters with a letter and a digit. The account is active at once. Demo sign-in is off."],
    ["6. AI (optional)", "Settings &gt; AI: paste your own API key.", "Only for the optional AI step of Auto Takeoff. The rules run without it."],
], [1.25 * inch, 2.75 * inch, 3.0 * inch]))
S.append(P("<b>Restoring a delivery:</b> every change is also kept in <font name='Consolas'>deliveries/&lt;date-name&gt;/</font> with a "
           "<font name='Consolas'>restore.py</font>. Run them oldest first (2026-11-02 ... 2026-11-12) to rebuild the takeoff module on a fresh copy; "
           "add <font name='Consolas'>--dry-run</font> to preview.", "note"))

# ── 3. Master flow ─────────────────────────────────────────────────────────
S.append(PageBreak())
S.append(H1("3. The master flow"))
S.append(P("This is the order to work in for every drawing set. Each step has its own section later in this guide."))
S.append(Spacer(1, 4))
S.append(MasterFlow(fw))
S.append(Spacer(1, 10))
S.append(table([
    ["Step", "Section", "Done when ..."],
    ["1 Upload & open", "5", "The drawing is open and its thumbnails show sheet labels."],
    ["2 Check the sheets", "6", "You know which sheets are plans and which have no scale (orange pill)."],
    ["3 Set the scale", "7", "Every plan sheet shows a green scale pill."],
    ["4 Run Auto Takeoff", "8", "The results panel shows the sheets recognised and the schedules read."],
    ["5 Review", "9", "\"Not taken off\" is empty or every row has been checked."],
    ["6 Measure by hand", "10–11", "Everything Auto Takeoff could not read is measured."],
    ["7 Organise", "12–13", "Subjects, captions and colours are right; the legend is placed."],
    ["8–10 Save, output, close", "15", "Saved (Ctrl+S); Download PDF made; tab closed."],
], [1.7 * inch, 0.8 * inch, 4.5 * inch]))

# ── 4. Screen ──────────────────────────────────────────────────────────────
S.append(PageBreak())
S.append(H1("4. The screen"))
S.append(P("With a drawing open, the workspace fills the browser window like Revu. The numbers match the table below."))
S.append(ScreenMap(fw))
S.append(Spacer(1, 8))
S.append(table([
    ["#", "Area", "What it is for"],
    ["1", "Menu bar", "File / Edit / View / Document / Measure / Markup / Tools / Window / Help. The drawing's tab with × at the top right saves and closes."],
    ["2", "Toolbar", "One wrapping row: Pages, Legend, Show/Hide, Names, Values, Combine, New, Save, Download PDF, Fullscreen, Recognize, Count similar ..."],
    ["3", "Properties bar", "Appears only while a tool is armed or markups are selected, floating over the drawing so it never jumps. Colour, line, width, fill, opacity, units, caption, font. The tool button at its left opens Subject / Label / Layer, Set as Default and Add to Tool Chest."],
    ["4", "Left icon rail", "Thumbs, Index (bookmarks / page index), Measure, Tools (Tool Chest), Scale, AI, Auto (Auto Takeoff), Search. Click an open tab again to close it."],
    ["5", "Left panel", "Shows the tab picked on the rail. Drag its edge to resize."],
    ["6", "Drawing", "The sheet. Wheel zooms at the cursor; deep zoom stays sharp."],
    ["7", "Tool strip", "Every measure and markup tool in one scrolling column (▲ / ▼ to scroll), name under each icon. Order: markups | shapes | measurements."],
    ["8", "Markups list", "Bottom table of markups (Alt+L). Drag it taller. This sheet | All sheets switch."],
    ["9", "Status bar", "Select, Pan, Text Select; page number; SNAP; REUSE; scale button (opens Apply Scale to Pages); units; SYNC; zoom; sheet size; cursor X/Y."],
], [0.3 * inch, 1.15 * inch, 5.55 * inch]))
S.append(P("<b>Compact header:</b> when a drawing is open, the ERP's page header shrinks to one slim tab bar to give the drawing more room. "
           "The ▼ button brings the full header back.", "note"))

# ── 5. Upload ──────────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("5. Step 1 — Upload and open a drawing"))
S += B([
    "Open a project, then <b>Takeoff &gt; PDF Measurements</b>. With no drawing open you see <b>Current &amp; recent drawings</b>: "
    "the open one is tagged CURRENT, then the most recently opened.",
    "Upload a PDF (button or drop zone). The card shows a progress bar, e.g. <i>42% · 12.4 / 30.1 MB · 9 s left</i>, then "
    "<i>Uploaded · reading drawing…</i>. The upload answers after a quick read; tables are extracted in the background.",
    "The drawing <b>opens by itself</b> when the upload finishes. With several files, the first to finish opens; the others join the list.",
    "The drawing you had open comes back, on the same page, when you return to PDF Measurements. A browser refresh keeps it too.",
    "A PDF saved with <b>Download PDF</b> (section 15) can be uploaded again: its markups and page scales come back editable.",
])
S.append(H2("Moving around"))
S.append(table([
    ["Action", "How"],
    ["Next / previous page", "Up / Down arrow (when nothing is selected), Page Down / Page Up, Ctrl+Right / Ctrl+Left, or Ctrl+mouse wheel (one page per notch)"],
    ["First / last page", "Home / End"],
    ["Zoom", "Mouse wheel (zooms at the cursor), + / −, trackpad pinch. Ctrl+9 fit page, Ctrl+0 fit width, Ctrl+8 actual size"],
    ["Pan", "Pan tool in the status bar or Shift+V; hold Space while drawing"],
    ["Split view", "Ctrl+2 vertical, Ctrl+H horizontal, Ctrl+Shift+2 unsplit. SYNC keeps both panes on the same page, zoom and pan"],
], [1.7 * inch, 5.3 * inch]))
S.append(P("Pages you have seen come back instantly and sharp; the next and previous pages are rendered ahead while the browser is idle."))

# ── 6. Thumbnails ──────────────────────────────────────────────────────────
S.append(H1("6. Step 2 — Check the sheets (Thumbnails)"))
S.append(P("Open <b>Thumbs</b> on the left rail (Alt+T). Each thumbnail shows:"))
S += B([
    "<b>Sheet label pill</b> (dark): read from the title block (S1.00, A-101 ...), else the PDF's own page label. Click to edit it.",
    "<b>Page number badge</b> (blue on the current page).",
    "<b>Scale pill</b>: <font color='#2E7D32'><b>green</b></font> with the scale, or <font color='#C66A00'><b>orange \"Scale Not Set\"</b></font>. Click it to set that page's scale.",
])
S.append(P("Ctrl+click or Shift+click selects several pages. Right-click opens the page menu (it works on all selected pages):"))
S.append(table([
    ["Group", "Items"],
    ["Pages", "Page Setup (size / rotation), Set Scale…, Cut / Copy / Paste Pages, Insert Blank Page…, Insert Pages…, Replace Pages…, Delete Pages…, Rotate Pages ► (90 / −90 / 180)"],
    ["Labels", "Number Pages… (prefix + start), Rename Page Label, Reset All Page Labels"],
    ["Out", "Extract Pages…, Export Pages ► (PDF / PNG), Email Pages…, Print Pages…, Copy Page to Snapshot (PNG to clipboard), Markup Summary ► CSV"],
    ["Other", "Apply Stamp…, Repair PDF, Flatten… (picture PDF of the pages with markups)"],
], [1.0 * inch, 6.0 * inch]))
S.append(P("<b>Your original is never changed.</b> Insert, delete, rotate, replace, paste, cut and repair are made on the real vector file and "
           "saved as a new copy, <i>&lt;name&gt; (…).pdf</i>, which is added to the project and opened. Its markups and page scales "
           "are carried across (rotated with the page where needed).", "note"))
S.append(H2("Extract, Delete, Combine, New PDF"))
S += B([
    "<b>Extract Pages…</b>: pages Current / Selected / Custom… (e.g. 3-5 or 1,5) / All. Options: delete pages after extracting; separate files "
    "named by page label (S-3.01.pdf); overwrite same-name drawings; open files after extraction (else download). Markups go with the pages.",
    "<b>Delete Pages…</b>: same page picker; saves a copy without those pages. A drawing keeps at least one page.",
    "<b>Combine</b> (toolbar, File &gt; Combine Files…): pick project drawings and/or PDFs from the PC, order them, name the result.",
    "<b>New PDF</b> (toolbar, File &gt; New PDF…): size \"Same as this drawing\" by default (or ANSI, ARCH, ISO, custom), orientation, "
    "1–500 pages, and optionally this drawing's scale on the new pages.",
])

# ── 7. Scale ───────────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("7. Step 3 — Set the scale"))
S.append(P("Every measurement depends on the page scale. Open the <b>Apply Scale to Pages</b> window from any of: the scale button in the "
           "status bar, the Scale tab on the left rail (Scale, Calibrate or the calibration chip), a thumbnail's scale pill, or "
           "Measure &gt; Set Scale…"))
S.append(table([
    ["Field", "Use"],
    ["Pages", "Current (n) / All Pages (1-N) from the ▼ menu, or type pages: 3-5 or 1,5"],
    ["(•) Preset", "Architectural, engineering and metric scales, plus your Saved presets"],
    ["○ Custom", "[1\"] [in] = [12'-6\"] [ft]. Units on both sides: in, ft, ft' in\", in\", yd, mi, mm, cm, m, km. A read-out shows the scale as understood (e.g. 1/8\" on paper = 1'-0\")"],
    ["+ Add Preset", "Saves the custom scale to your Saved presets"],
    ["Precision", "1\", 1/2\" … 1/64\""],
    ["Calibrate / Recalibrate", "Click two points on a known dimension (they snap to the drawing's lines), then type the real length and Apply Scale. Applies to all pages picked"],
], [1.5 * inch, 5.5 * inch]))
S.append(P("Lengths can be typed in any normal form: <font name='Consolas'>12   12.5   12'   12'-6\"   12' 6\"   12'-6 1/2\"   12 ft 6 in   1 1/2\"   1/8\"   300 mm   3.5 m</font>."))
S.append(H2("If a sheet has no scale"))
S += B([
    "You can still draw. When the measurement is finished, the scale window opens. <b>Apply</b> keeps the markup and re-measures it.",
    "<b>Cancel</b> (or Esc during a calibration started from it) <b>removes</b> that unscaled measurement. The window keeps asking after every "
    "measurement until the sheet has a scale.",
    "A \"Detected scale … Use this\" suggestion appears when the sheet prints a scale the ERP can read.",
])
S.append(P("<b>How Auto Takeoff finds a scale on its own:</b> the printed scale first; if none, the feet-inch dimension strings are checked against the "
           "lines they measure and the scale most of them agree on wins (weighted by length, so overall building dimensions decide); if a sheet has "
           "neither, it borrows the most common scale from the nearest same-size sheets (never a detail scale larger than 1/4\" = 1'-0\"). "
           "Sheets whose text is drawn as lines must be calibrated by hand.", "note"))

# ── 8. Auto Takeoff ────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("8. Step 4 — Run Auto Takeoff"))
S.append(P("Open <b>Auto</b> on the left rail (or Tools &gt; Auto Takeoff…). Pick what to take off, the options, and Run on this page or the whole set."))
S.append(H2("What to take off (member types)"))
S.append(table([
    ["Group", "Member types"],
    ["Structural steel", "Columns · Beams · Joists (SJI K / LH / DLH, KCS, SLH) · Joist girders (SJI G / BG / VG) · Deck areas (Type B / F / A roof deck, composite VL / VLI / VLR, form deck, Type N, cellular) · Base plates · Steel braces · Angles"],
    ["Cold-formed steel", "Load bearing walls, headers, jambs · Shear walls · Strap braced walls · Non-load bearing walls, headers, jambs · Holdowns · Trusses (roof / floor) · CFS joists · CFS beams · Hat channels · Track"],
    ["Other", "Bays · Walls with no tag / CMU (check type)"],
    ["Miscellaneous steel", "Stairs (one area per flight with treads, risers, width, going and approximate stringer LF)"],
], [1.4 * inch, 5.6 * inch]))
S.append(P("A re-run only touches the member types you ticked."))
S.append(H2("Options"))
S.append(table([
    ["Option", "What it does"],
    ["House framing rules (on by default)", "Reads each sheet's title-block title and takes off only what that sheet is for (table below)."],
    ["Zoom in by parts", "Splits each sheet's drawing area into 4, 6, 9, 12 or 16 overlapping parts (auto by how busy it is) and checks each part zoomed in, one by one, for columns, beams, joists / trusses and deck."],
    ["Detailed scan", "Reads the sheet again at full detail in small tiles: finds columns drawn in any style (rotated, loose lines, rounded), removes false ones (grid bubbles, deck arrows, section heads), traces labelled beams that had no line, and curved beams."],
    ["AI step (optional)", "Uses the key in Settings &gt; AI. Scanned sheets are read zoomed in as four quarters. Everything else works without it."],
], [1.9 * inch, 5.1 * inch]))
S.append(H2("How it reads a drawing set"))
S.append(P("<b>Schedules and notes first.</b> Wall framing, shear wall, brace wall, header, CFMF truss / joist / beam, base plate and diaphragm "
           "schedules, column marks, legends and notes are read from all sheets before anything is drawn (cached per set). "
           "The run report says what was read, e.g. <i>Read first: 3 sheets of schedules and notes · 4 wall types · 2 column marks</i>."))
S.append(table([
    ["Sheet (from its title)", "Taken off", "Not taken off"],
    ["Floor framing plan", "Every joist and truss, one per schedule spacing (T / RT, J / RJ), steel beams, CFS beams (B-x), deck (D1 ...)", "Walls, headers, holdowns"],
    ["Roof framing plan", "Roof trusses and joists, CFS beams, deck", "Walls"],
    ["Shear wall plan of floor N", "Walls W1–W4 with schedule row N TO N+1 (stud, spacing, height), headers H1–H4, shear walls SW-x, strap-braced BR-x, holdowns (HD, counted), steel braces", "Trusses, joists, steel beams"],
    ["Foundation plan", "Columns (at each size label's leader) and base plates (BP-x, counted at the column)", "Footings, slabs"],
    ["Details, sections, notes", "Read for schedules only", "Everything"],
], [1.6 * inch, 3.7 * inch, 1.7 * inch]))
S.append(H2("How each member is measured"))
S.append(table([
    ["Member", "Rule"],
    ["Joists / trusses", "The tag's leader is followed to the span line; both distribution arrows are followed to their tips (stopping at walls). One member per spacing across the bay (13 ft at 24\" = 7). Fields of 6+ parallel lines at 12 / 16 / 19.2 / 24\" o.c. are named from the zone mark, legend or callout."],
    ["Beams", "Each end is moved, along its own line, onto the exact column centre or the framing line it stops at, so lengths read centre to centre. Unlabelled beams in the beam pen are added as \"BEAM (no size on plan)\" at low confidence."],
    ["Columns", "Found at each label's leader and by symbol. Drawn by section shape: W = I-shape turned as on the plan, square / rectangular HSS = tube, round HSS / pipe = circle. Marks (C1, C2) are resolved through the schedule."],
    ["Stud walls", "A see-through band at the real wall width (read from the two faces), on the true centre line. Studs = (length ÷ spacing, rounded up) + 1, spacing from the plan / schedule, else 24\" o.c."],
    ["Header areas", "Where the wall faces stop at an opening (2–20 ft), the opening becomes its own hatched \"HEADER\" piece with no studs, sized from the nearest header tag."],
    ["Shear / strap walls", "Length = the hatched panel, set to its dimension when drawn. The panel sits on top of the bearing wall and counts no field studs of its own (no double count)."],
    ["Legend walls", "Where walls have no tags but a colour legend, every row of that pattern is taken off as that wall type."],
    ["Untagged walls", "Double-line walls in the wall pen that no tag reached are added (continuing the tagged wall, else \"WALL (no tag on the plan)\")."],
], [1.3 * inch, 5.7 * inch]))
S.append(H2("Load bearing or not"))
S.append(P("Decided in this order:"))
S += B([
    "<b>1. What the drawings say</b>: wall-type text, schedule, legend, house rules. CMU / masonry / concrete stay CMU walls; "
    "2-1/2\", 3-5/8\" or 4\" metal stud walls are partitions.",
    "<b>2. The framing above</b>: the floor framing sheet is laid over the wall sheet; joists landing on a wall make it Load Bearing, "
    "joists running alongside make it Non-Load Bearing. The reason is written in the spec.",
    "<b>3. Defaults</b> when nothing says: exterior and demising walls are load bearing (600S162-54); every other wall is non-load bearing (362S125-18). "
    "Headers and jambs follow the wall they sit in; with no wall nearby, 54 mil and heavier counts as load bearing.",
])
S.append(H2("Re-running is safe"))
S += B([
    "Re-runs <b>never duplicate</b>. Your edits, profile changes and Subjects you typed survive.",
    "A markup you delete <b>on its own</b> stays deleted on re-runs (it was a wrong detection).",
    "Markups deleted <b>several at once</b> are placed again on the next run. When a re-run skips ones you deleted, the panel offers "
    "<b>Bring them back and re-run</b>.",
])

# ── 9. Review ──────────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("9. Step 5 — Review the results"))
S.append(P("After a run, the Auto panel shows the result lines and the <b>Detected markups</b> list."))
S.append(table([
    ["Part of the panel", "What it tells you"],
    ["Result line", "Markups added, sheets recognised (e.g. \"p.8 1st floor shear walls\"), schedules read."],
    ["Detailed scan / Zoomed check", "Areas checked, columns added, false columns removed, beams added and how many need a size. \"Part by part\": click a part to zoom to it."],
    ["Not taken off (n)", "Every structural tag with no markup of its type within 4 ft. Click a row to zoom to the tag. When nothing is missed: \"Every tag on the plans read was taken off.\""],
    ["Detected markups", "Grouped by category and size. Each group shows its material chip (e.g. 600S200-68 (50)), total length and, for walls, \"· N studs\". Each row: length × height = wall area · N studs @ 24\" o.c. · material."],
], [1.8 * inch, 5.2 * inch]))
S.append(H2("Working in the list"))
S += B([
    "<b>Click</b> a row: selects it and zooms to it. <b>Ctrl+click</b>: add / remove. <b>Shift+click</b>: the whole run from the last row clicked.",
    "<b>Select all</b> on a category (e.g. all beams on the sheet), then delete, recolour or edit them together.",
    "<b>Walls filter chips</b>: All walls · Load Bearing Wall · Shear Wall · Strap Braced Wall · Header areas. Only those show in the list and on the sheet.",
    "<b>pencil rename</b> a profile (e.g. give \"BEAM (no size on plan)\" its size). Column heights can be set and are saved.",
    "<b>Colour</b>: each parameter set (role, profile, spacing, width, height, header vs wall) gets its own picklist colour automatically: "
    "warm for headers, cool for walls. Pick a different colour for a group from its picklist; it is kept on re-runs.",
    "<b>Highlight all</b>: every column taken off gets a soft green disc, so gaps stand out.",
    "On the sheet, <b>right-click &gt; Select same profile</b> (this sheet, or all sheets) picks every markup of that size, found or added by you.",
])
S.append(P("<b>Columns you add by hand count too.</b> Place a Count markup and give it a column profile (Material such as HSS6X6X1/2 or "
           "W18X158) or the Subject \"Column\". It is drawn with the column symbol and listed under Columns as \"&lt;profile&gt; · added by you\".", "note"))

# ── 10. Manual tools ───────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("10. Step 6 — Measure and mark up by hand"))
S.append(P("Pick a tool from the right tool strip, the Measure / Markup menus or its key. Every tool draws its shape live as you move the mouse."))
S.append(H2("Measure tools"))
S.append(table([
    ["Tool", "Key", "How to draw"],
    ["Length", "Shift+Alt+L", "Two clicks"],
    ["Polylength", "Shift+Alt+Q", "Click points; double-click, right-click or Enter (2+ points) to finish"],
    ["Area", "Shift+Alt+A", "Click points and finish (Enter, 3+ points), or press-and-drag a rectangle"],
    ["Perimeter", "Shift+Alt+P", "As Area"],
    ["Volume", "Shift+Alt+V", "As Area, with a depth in the Area options bar"],
    ["Count", "Shift+Alt+C", "One click per item; keeps counting until Esc"],
    ["Diameter / Radius / 3-point Radius", "Shift+Alt+D / Shift+Alt+U", "Line and circle / centre to circle / circle through points"],
    ["Angle", "Shift+Alt+G", "Both arms"],
    ["Arc", "Shift+C", "Arc length"],
    ["Dynamic Fill", "J", "Fills a closed region"],
    ["Polygon / Ellipse Cutout", "", "Cut a hole out of an area (shaded red while drawing)"],
], [2.0 * inch, 1.4 * inch, 3.6 * inch]))
S.append(H2("Markup tools"))
S.append(table([
    ["Tool", "Key", "How to draw"],
    ["Text Box", "T", "Press and drag the box (or click for default width); type in place. Enter = new line; Ctrl+Enter / Esc / click outside = done"],
    ["Cloud", "C", "Drag a rectangle, or click points and finish with Enter / double-click"],
    ["Cloud+", "K", "Draw the cloud, then the leader slides round the cloud; click to drop the comment box and type. It can be left empty; double-click later to edit"],
    ["Callout / Note", "Q / N", "First click = the point; second click places the box; type in place"],
    ["Highlight", "H", "Drag. Over readable text it snaps to the words, one highlight per line, and keeps the words"],
    ["Line, Arrow, Polyline", "L, A, —", "Clicks; Polyline finishes with double-click / right-click / Enter"],
    ["Rectangle, Ellipse, Polygon", "R, E, Shift+P", "Drag (rectangle, ellipse) or click points (polygon)"],
    ["Pen, Stamp", "P, S", "Freehand / one click with a stamp preset"],
], [1.7 * inch, 1.0 * inch, 4.3 * inch]))
S.append(H2("Drawing behaviour (Revu style)"))
S += B([
    "<b>A tool exits after one markup</b> and goes back to Select. <b>Double-click</b> a tool button to lock it on (lock badge). "
    "The <b>REUSE</b> button in the status bar keeps every tool on (remembered). Count always continues until Esc.",
    "<b>Straight lines by default</b>: every segment snaps to 0 / 45 / 90°. Hold <b>Ctrl+Shift</b> while clicking for a free point. "
    "The toolbar ortho button turns it off.",
    "<b>SNAP (magnet)</b>: points lock onto the drawing's line ends, midpoints, edges and crossings (small ring). Toggle SNAP in the status bar. "
    "A straight segment that snaps onto a line lands exactly where its direction meets that line, so lines between walls are square.",
    "<b>Enter</b> finishes Area, Volume, Perimeter, cutouts, Polygon, Cloud, Cloud+ and Polyline / Polylength. "
    "<b>Esc</b> cancels and returns to Select. Hold <b>Space</b> to pan while drawing.",
    "<b>Text Select</b> (status bar): drag over text to copy it to the clipboard.",
])

# ── 11. Properties & Tool Chest ───────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("11. Properties bar and Tool Chest"))
S.append(H2("Properties bar"))
S.append(P("Shown while a tool is armed or markups are selected; only the fields that fit the markup type appear:"))
S += B([
    "Colour (picklist), line type, width, fill, opacity %.",
    "Units: in, ft, ft-in, mm, cm, m, km; area units sq in, sq ft, sq cm, sq m, sq mm.",
    "Wall Height (drives Wall Area) and <b>Caption</b>: Label, Length, Area, Perimeter, Wall Area, Depth, Volume, Count.",
    "Font, size, text colour, Bold / Italic / Underline, and selection totals.",
    "<b>Area options bar</b> (Area / Volume): length, area and volume units, Depth, and <b>Slope</b> (pitch rise/run, degrees or grade %). "
    "Slope is part of the area: 166.7 sf at 30° = 192.5 sf.",
    "<b>Tool button</b> (left end): Subject, Label, Layer; <b>Set as Default</b> (the look and Subject/Label/Layer become the tool's defaults); "
    "<b>Add to Tool Chest ▼</b>.",
])
S.append(P("<b>Labels:</b> every measurement shows its label and dimension by default. A markup's own Caption decides what it shows "
           "(e.g. \"Label\" only). The toolbar Names / Values switches only hide labels for the current session.", "note"))
S.append(H2("Tool Chest (left rail > Tools, Alt+X)"))
S.append(P("Saved tools that carry their type, Subject, Label, group and every property. One click arms the tool."))
S.append(table([
    ["Set", "Contents"],
    ["Recent Tools / My Tools", "Automatic recent list; your own tools (plus any sets you create)"],
    ["AISC steel", "W Beams (46), W Columns (32), WT (11), HSS Square &amp; Rectangular (20), HSS Round &amp; Pipe (10), Channels C / MC (8), Angles (10)"],
    ["SJI / deck", "SJI Steel Joists (24), Metal Deck (13)"],
    ["SSMA cold-formed", "Load Bearing Walls (17), Non-Load Bearing Walls (11), Shear Walls (9), Load / Non-Load Bearing Headers, Load / Non-Load Bearing Jambs, Floor Joists (10), CFS Joists, Track &amp; Accessories (10), Hat Channels"],
    ["CFS trusses", "Floor Trusses (6), Roof Trusses (10): common, girder, hip, hip girder, jack, mono, scissor, gable end, valley, attic"],
], [1.6 * inch, 5.4 * inch]))
S += B([
    "Each tile draws the member's cross-section with a badge (W, WT, HSS, L, C, CFS, TRK, DECK, JST, hat, header, jamb). Names follow AISC (W12x26, HSS6x6x1/4).",
    "Each tool's Subject is the member role with its role colour; walls use polyline, jambs and W columns use count, the rest use length.",
    "<b>New tool</b> in any set: type, Subject, Label, name, colour, width, line style. Drawing mode or Properties mode per set; "
    "icon or detail view; drag between sets; double-click to rename. The library button brings deleted structural sets back.",
])

# ── 12. Markups list ──────────────────────────────────────────────────────
S.append(H1("12. Step 7 — Organise: the Markups list"))
S += B([
    "Open with <b>Alt+L</b> or Window &gt; Markups list. <b>This sheet | All sheets</b> (default All, sorted by page). Clicking a row on another sheet goes there.",
    "Columns include Subject, Label, Length / Area / Unit (exactly what the sheet caption shows), Material, Status. "
    "Add a <b>Level</b> column to see the level Auto Takeoff stored.",
    "Click / Ctrl+click / Shift+click select as on the sheet.",
    "<b>Right-click</b> (one or many rows): n markups selected · Go to markup · Properties · Set Status (None / Accepted / Rejected / Cancelled / Completed) · "
    "Colour · Lock / Unlock · Hide / Show · Select All (this page) · Select same profile · Duplicate · Multiply · Offset · RFI · Legend ► · "
    "Rotate / flip / align · Group · Delete (all selected).",
    "<b>Copy / paste</b>: Ctrl+C then Ctrl+V on any page (Shift+Ctrl+C / V also work): same position, re-measured with that page's scale, one undo.",
    "<b>Multiply</b>: Direction / Distance / Copies with live preview. <b>Offset</b>: typed distance in any length form.",
])

# ── 13. Legend ─────────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("13. Legends"))
S.append(P("The legend summarises the markups: one row per Subject and look, with symbol, <b>Count</b>, Description (Subject), total Length / Area and Unit "
           "(the <b>Revu</b> layout, default). The older per-length layout is <b>Detailed</b>, one click away in the legend panel header."))
S.append(H2("Create a legend for chosen markups"))
S += B([
    "Select markups, right-click &gt; <b>Legend ► Create New Legend (this sheet)</b> (or the toolbar Legend button with markups selected), then click the sheet to place it.",
    "<b>Legend Setup</b>: title and \"show the title row on top\"; columns to keep and their order; table lines Grid / Horizontal / Vertical / Outline / None; <b>Keep it live</b>.",
    "<b>Live</b>: markups drawn later with the same Subject and colour join the legend automatically.",
    "<b>Legend ► None</b> takes the selected markups out of every legend on the sheet.",
])
S.append(H2("Legend properties"))
S.append(P("Click a placed legend: its properties appear in the top bar: Font · Colour · Title ► (text, size, B/I/U, colour) · Columns ► · Cells ► · "
           "Opacity · Line colour · Style ► · Width · Fill · Fill opacity · Live. Dragging a corner scales the whole legend (0.25× to 4×). "
           "Each legend keeps its own setup, saved on the server."))

# ── 14. Where things are stored ───────────────────────────────────────────
S.append(H1("14. What is saved where (important when sharing)"))
S.append(table([
    ["Saved on the ERP server (database)", "Saved only in this browser"],
    [P("Projects and drawings (the PDFs)<br/>Every markup with its properties, caption style, text-box style, legend setup<br/>"
       "Auto Takeoff deletions you made<br/>Page scales", "cell"),
     P("Tool Chest sets and your own tools<br/>Sheet-label edits on thumbnails<br/>Auto Takeoff colour assignments<br/>"
       "Legend layout choice, list scope, REUSE, ortho<br/>Thumbnail cache<br/>Estimation sheets", "cell")],
], [3.5 * inch, 3.5 * inch]))
S.append(P("<b>Sharing the ERP folder shares the code, not the data.</b> Someone running your folder on another PC starts with an empty "
           "database: upload a drawing set to test. To give them your projects and markups too, give them a database backup "
           "(pg_dump / pg_restore). A <b>Download PDF</b> file carries its markups and scales and opens editable in any copy of this ERP.", "note"))

# ── 15. Save & output ─────────────────────────────────────────────────────
S.append(H1("15. Steps 8–10 — Save, output and close"))
S.append(table([
    ["Action", "Where", "Result"],
    ["Save", "Save button, Ctrl+S, File &gt; Save", "Saves to the ERP now and confirms (work also auto-saves)."],
    ["Download PDF", "Green toolbar button, File &gt; Download PDF (with markups)",
     "The original vector PDF with every markup as a real PDF annotation on an \"OE Markups\" layer, each with its drawn appearance and dimension "
     "label (12'-6\", 45.2 sf, n ea). Shows the same in Revu, Acrobat, Chrome and Edge. Opens editable again in the ERP."],
    ["Export flattened PDF", "File menu", "Picture PDF of the pages with markups burned in."],
    ["Markup Summary CSV", "Thumbnail menu &gt; Markup Summary ► CSV", "Spreadsheet of the markups."],
    ["Extract / Email / Print", "Thumbnail menu", "See section 6."],
    ["Close", "× on the drawing tab (top right), File &gt; Close PDF", "Saves, then returns to Current &amp; recent drawings."],
], [1.4 * inch, 2.1 * inch, 3.5 * inch]))

# ── 16. Shortcuts ─────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("16. Keyboard shortcuts"))
S.append(P("Help &gt; Keyboard Shortcuts shows the full list inside the ERP."))
sc_left = [
    ["Key", "Action"],
    ["V", "Select"], ["Shift+V", "Pan"], ["Z", "Zoom tool"], ["+ / −", "Zoom in / out"],
    ["Ctrl+9 / 0 / 8", "Fit page / fit width / actual size"],
    ["Up / Down, PgDn / PgUp", "Next / previous page"],
    ["Ctrl+Right / Left", "Next / previous page"], ["Home / End", "First / last page"],
    ["Ctrl+2 / Ctrl+H", "Split vertical / horizontal"], ["Ctrl+Shift+2", "Unsplit"],
    ["Ctrl+4 / Ctrl+5", "Single page / continuous"], ["F11", "Full screen"],
    ["Alt+T / B / L", "Thumbnails / Index / Markups list"],
    ["Alt+X / U / 1", "Tool Chest / Measurements / Search"],
    ["Ctrl+F", "Find"],
]
sc_right = [
    ["Key", "Action"],
    ["Ctrl+S", "Save"], ["Ctrl+Z / Ctrl+Y", "Undo / redo"], ["Ctrl+C / Ctrl+V", "Copy / paste markups"],
    ["Ctrl+D", "Duplicate"], ["Ctrl+A", "Select all"], ["Delete", "Delete markup or vertex"],
    ["Arrows (Shift = ×10)", "Nudge selected markups"], ["[ / ]", "Shorten / lengthen a line"],
    ["Ctrl+G / Ctrl+Shift+G", "Group / ungroup"], ["Ctrl+Shift+L", "Lock / unlock"],
    ["Ctrl+Shift+J / [", "Bring to front / send to back"],
    ["Ctrl+Shift+F8 / F7", "Snap to content / markup"],
    ["Ctrl+B / I / U", "Bold / italic / underline (text)"],
    ["Esc", "Cancel, back to Select"], ["Enter / double-click", "Finish a shape"],
]
t1 = table(sc_left, [1.45 * inch, 1.95 * inch]); t2 = table(sc_right, [1.45 * inch, 1.95 * inch])
S.append(Table([[t1, t2]], colWidths=[3.5 * inch, 3.5 * inch], style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
S.append(P("Measure and markup tool keys are in section 10.", "small"))

# ── 17. Troubleshooting ───────────────────────────────────────────────────
S.append(H1("17. Troubleshooting"))
S.append(table([
    ["What you see", "What to do"],
    ["Auto Takeoff misses things that should work, or gives old results", "Restart the backend (port 8000). It does not reload new code by itself."],
    ["The scale window keeps opening", "The sheet has no scale. Apply one (Pages: All Pages to set the whole set at once)."],
    ["A measurement vanished after Cancel", "By design: a measurement drawn without a scale is removed when the scale window is cancelled."],
    ["A deleted auto markup does not come back on re-run", "Single deletions are remembered. Use \"Bring them back and re-run\"."],
    ["Labels or lengths not shown", "Check the markup's Caption in the Properties bar; Names / Values reset to on each session."],
    ["Page tools / Download PDF fail after copying the ERP", f"Run {K('npm ci')} in {K('frontend')} (pdf-lib must be installed)."],
    ["Old logo, icons or behaviour after an update", "Hard refresh: Ctrl+Shift+R."],
    ["Thumbnails slow the first time", "Sheets with many large photos take a few seconds once; after that they load from the browser cache."],
], [2.6 * inch, 4.4 * inch]))

# ── 18. Known limits ──────────────────────────────────────────────────────
S.append(H1("18. Known limits"))
S += B([
    "Tool Chest sets and sheet-label edits are saved per browser, not on the server.",
    "Revu's Eraser, Snapshot tool, Image and Lasso tools are not included. Bookmarks and Search are a simple page index and Find. "
    "The scale window has no \"Separate Y scale\".",
    "Columns drawn only as part of a wall (no symbol of their own) are not added; on plain foundation sheets without house rules, a column "
    "drawn as separate crossing lines can be missed (house rules find it).",
    "Load bearing is read from framing only where a framing sheet lines up with the wall sheet; otherwise the drawing text, gauge and defaults decide.",
    "Stairs without UP / DN text are not found. Ladders, grating, lintels and embeds are not read yet. "
    "Some joist fields broken by many crossing lines are partly missed.",
])

# ── Appendix ──────────────────────────────────────────────────────────────
S.append(CondPageBreak(3.2 * inch))
S.append(H1("Appendix — for developers"))
S.append(P("All custom code is marked with <font name='Consolas'>OE-DELIVERY: &lt;date&gt;-&lt;name&gt;</font> comments. Main files:"))
S.append(table([
    ["Area", "Files"],
    ["Viewer", "frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx, useMeasurementPersistence.ts"],
    ["Revu UI", "components/RevuMenuBar, RevuPropertiesBar, RevuToolStrip, RevuToolChest, SetScaleDialog, LegendSetupDialog, LegendPropertiesPanel, TextFormatBar, ColorPicklist, PageToolsDialogs, PdfCreateDialogs, revu-icons"],
    ["Viewer data", "modules/pdf-takeoff/data/: auto-takeoff, auto-colours, column-shape, stud-wall, text-box, structural-tools, tool-chest-sets, revu-shortcuts, sheet-index, pdf-pages, length-input, text-words, thumb-cache"],
    ["Takeoff page", "frontend/src/features/takeoff/: TakeoffPage.tsx, components/MeasurementLedger.tsx, UploadProgressBar.tsx, lib/takeoff-*.ts"],
    ["Auto Takeoff engine", "backend/app/modules/takeoff/: auto_takeoff.py, auto_takeoff_ai.py, detail_scan.py, framing_rules.py, bearing_walls.py, detect.py, router.py, schemas.py"],
    ["Tests", "backend/tests/unit/test_takeoff_*.py; frontend vitest next to each data file"],
    ["History", "deliveries/2026-11-02-… to 2026-11-12-revu-ui: CHANGES.md, files/, patch_scripts/, e2e/, restore.py"],
], [1.4 * inch, 5.6 * inch]))

doc.multiBuild(S)
print("ok", OUT)

from pathlib import Path
p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding='utf-8')
BS = chr(92)
def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)
rep("  useEffect(() => { pageWordsRef.current = new Map(); }, [pdfDoc]);", "  useEffect(() => { pageWordsRef.current = new Map(); }, [pdfDoc]);\n  /** Always the current reader (the canvas handlers are memoised). */\n  const wordsOfPageRef = useRef(wordsOfPage);\n  wordsOfPageRef.current = wordsOfPage;")
rep("        const sel = wordsInRect(await wordsOfPage(pg), { x0: st.x, y0: st.y, x1: tp.x, y1: tp.y });", "        const sel = wordsInRect(await wordsOfPageRef.current(pg), { x0: st.x, y0: st.y, x1: tp.x, y1: tp.y });")
rep("              const sel = wordsInRect(await wordsOfPage(pg), { x0: a.x, y0: a.y, x1: ep.x, y1: ep.y });", "              const sel = wordsInRect(await wordsOfPageRef.current(pg), { x0: a.x, y0: a.y, x1: ep.x, y1: ep.y });")
old = "                annotation: sel.length ? textOf(sel).split('" + BS + "n')[i]?.slice(0, 120) ?? '' : nextAnnotation(tool),"
new = ("                annotation: nextAnnotation(tool),\n"
       "                // The highlighted words, kept for the list / export (not drawn).\n"
       "                customFields: { ...((extra as { customFields?: Record<string, string> }).customFields ?? {}), ...(sel.length ? { Text: textOf(sel).split('" + BS + "n')[i]?.slice(0, 200) ?? '' } : {}) },")
rep(old, new)
p.write_text(s, encoding='utf-8'); print('ok')

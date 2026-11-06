import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text(encoding='utf-8')
old="""  DRAWING_SCALE_PRESETS,
  pixelDistance,
  toRealDistance,"""
new="""  DRAWING_SCALE_PRESETS,
  // Viewport scale dialog (OE-DELIVERY 2026-11-02-revu-viewports-sketch).
  presetScale,
  ratioFromScale,
  pixelDistance,
  toRealDistance,"""
assert s.count(old)==1, s.count(old)
p.write_text(s.replace(old,new),encoding='utf-8'); print('ok')

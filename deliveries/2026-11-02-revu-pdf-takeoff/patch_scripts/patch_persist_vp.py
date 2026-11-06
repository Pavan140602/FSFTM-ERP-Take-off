import sys
from pathlib import Path
p=Path('useMeasurementPersistence.ts'); s=p.read_text(encoding='utf-8')
pairs=[
("""  reconcilePageScales,
  scaleForPage,
} from './data/page-scales';""","""  reconcilePageScales,
  // Viewport-aware scale per measurement (OE-DELIVERY 2026-11-02-revu-viewports-sketch).
  scaleForMeasurement,
  viewportAt,
} from './data/page-scales';"""),
("""  const scale = pageScales ? scaleForPage(pageScales, m.page) : undefined;""",
"""  // A measurement inside a viewport sends that viewport's ratio instead
  // (OE-DELIVERY 2026-11-02-revu-viewports-sketch).
  const scale = pageScales ? scaleForMeasurement(pageScales, m.page, m.points) : undefined;"""),
("""  const scaleCalibrated = pageScales
    ? pageIsCalibrated(pageScales, m.page)
    : false;""","""  const scaleCalibrated = pageScales
    ? pageIsCalibrated(pageScales, m.page) || viewportAt(pageScales, m.page, m.points[0]) != null
    : false;"""),
("""                scaleForPage(pageScales, m.page),
                pageIsCalibrated(pageScales, m.page),""","""                scaleForMeasurement(pageScales, m.page, m.points),
                pageIsCalibrated(pageScales, m.page) || viewportAt(pageScales, m.page, m.points[0]) != null,"""),
]
bad=[(o[:60],s.count(o)) for o,_ in pairs if s.count(o)!=1]
if bad: print('NOT WRITTEN',bad); sys.exit(1)
for o,n in pairs: s=s.replace(o,n)
p.write_text(s,encoding='utf-8'); print('ok')

"""Profile editing in the Detected markups list (all-or-nothing).
OE-DELIVERY: 2026-11-02-auto-takeoff-profile-edit"""
import sys
from pathlib import Path

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
TAG = 'OE-DELIVERY 2026-11-02-auto-takeoff-profile-edit'

PROFILE_INPUT = '''/** Inline profile editor (TAGX): type a size or pick one of the
 *  profiles already on the drawing; Enter / tick saves, Esc / cross
 *  cancels. */
function ProfileInput(props: { initial: string; onSave: (v: string) => void; onCancel: () => void }) {
  const { initial, onSave, onCancel } = props;
  const [v, setV] = useState(initial === 'COLUMN' ? '' : initial);
  const done = useRef(false);
  const save = () => {
    if (done.current) return;
    done.current = true;
    if (v.trim()) onSave(v);
    else onCancel();
  };
  return (
    <span className="flex flex-1 items-center gap-0.5 min-w-0" onClick={(e) => e.stopPropagation()}>
      <input
        autoFocus
        type="text"
        value={v}
        list="auto-profile-options"
        placeholder="e.g. W12X26, HSS6X6X1/4"
        onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => {
          e.stopPropagation();
          if (e.key === 'Enter') save();
          if (e.key === 'Escape') {
            done.current = true;
            onCancel();
          }
        }}
        className="min-w-0 flex-1 rounded border border-oe-blue bg-surface-primary px-1 py-0 text-[10px] uppercase"
        data-testid="auto-profile-input"
      />
      <button
        type="button"
        title="Save profile"
        className="rounded p-0.5 text-emerald-600 hover:bg-surface-secondary"
        onMouseDown={(e) => e.preventDefault()}
        onClick={save}
        data-testid="auto-profile-save"
      >
        <Check size={11} />
      </button>
      <button
        type="button"
        title="Cancel"
        className="rounded p-0.5 text-content-tertiary hover:bg-surface-secondary"
        onMouseDown={(e) => e.preventDefault()}
        onClick={() => {
          done.current = true;
          onCancel();
        }}
      >
        <X size={11} />
      </button>
    </span>
  );
}

'''.replace('TAGX', TAG)

pairs = [
("""import { ChevronDown, ChevronRight, Crosshair, MousePointer2, Trash2 } from 'lucide-react';""",
 """import { Check, ChevronDown, ChevronRight, Crosshair, MousePointer2, Pencil, Trash2, X } from 'lucide-react';"""),
("""/** Column height box: type""", PROFILE_INPUT + """/** Column height box: type"""),
("""  /** Save a column height (feet; null clears) on the given markups. */
  onSetHeight: (ids: string[], ft: number | null) => void;
}""", """  /** Save a column height (feet; null clears) on the given markups. */
  onSetHeight: (ids: string[], ft: number | null) => void;
  /** Set the profile of the given markups by hand (""" + TAG + """). */
  onSetProfile: (ids: string[], profile: string) => void;
  /** Profiles to suggest while typing (the ones on this drawing). */
  profileOptions: string[];
}"""),
("""  const { rows, currentPage, selectedIds, formatTotal, onFocus, onSelect, onDelete, onSetHeight } = props;""",
 """  const { rows, currentPage, selectedIds, formatTotal, onFocus, onSelect, onDelete, onSetHeight, onSetProfile, profileOptions } = props;
  /** What is being renamed: `g:<cat>|<des>` (a whole size group) or `r:<id>`. */
  const [editing, setEditing] = useState<string>('');"""),
("""                    <div className="flex items-center gap-1 px-1.5 py-1">
                      <button type="button" onClick={() => setOpenGroups((p) => toggle(p, key))} className="flex-1 flex items-center gap-1 text-left min-w-0">""",
 """                    <div className="flex items-center gap-1 px-1.5 py-1">
                      {editing === `g:${key}` ? (
                        <ProfileInput
                          initial={g.des}
                          onSave={(v) => {
                            setEditing('');
                            onSetProfile(ids, v);
                          }}
                          onCancel={() => setEditing('')}
                        />
                      ) : (
                      <button type="button" onClick={() => setOpenGroups((p) => toggle(p, key))} className="flex-1 flex items-center gap-1 text-left min-w-0">"""),
("""                        })()}
                      </button>
                      {cat.cat === 'columns' && (
                        <HeightInput""", """                        })()}
                      </button>
                      )}
                      {editing !== `g:${key}` && (
                        <button
                          type="button"
                          title={`Change the profile of all ${g.rows.length}`}
                          className="rounded p-0.5 hover:bg-surface-secondary"
                          onClick={() => setEditing(`g:${key}`)}
                          data-testid="auto-profile-edit-group"
                        >
                          <Pencil size={11} />
                        </button>
                      )}
                      {cat.cat === 'columns' && (
                        <HeightInput"""),
("""                              <span className="flex-1 truncate text-content-primary" title={r.label}>
                                {cat.cat === 'columns' ? (r.label ?? r.des) : r.valueText}
                              </span>""", """                              {editing === `r:${r.id}` ? (
                                <ProfileInput
                                  initial={r.des}
                                  onSave={(v) => {
                                    setEditing('');
                                    onSetProfile([r.id], v);
                                  }}
                                  onCancel={() => setEditing('')}
                                />
                              ) : (
                                <>
                                  <span className="flex-1 truncate text-content-primary" title={r.label}>
                                    {cat.cat === 'columns' ? (r.label ?? r.des) : r.valueText}
                                  </span>
                                  <button
                                    type="button"
                                    title="Change the profile of this markup"
                                    className="rounded p-0.5 text-content-tertiary opacity-60 group-hover:opacity-100 hover:bg-surface-secondary"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditing(`r:${r.id}`);
                                    }}
                                    data-testid="auto-profile-edit"
                                  >
                                    <Pencil size={10} />
                                  </button>
                                </>
                              )}"""),
("""      <p className="text-content-tertiary leading-snug">
        Click a row to zoom to it""", """      <datalist id="auto-profile-options">
        {profileOptions.map((o) => (
          <option key={o} value={o} />
        ))}
      </datalist>
      <p className="text-content-tertiary leading-snug">
        <Pencil size={10} className="inline" /> changes a profile (one markup, or a whole size) when Auto Takeoff read it wrong or not at
        all. Your profile is kept on every re-run.
      </p>
      <p className="text-content-tertiary leading-snug">
        Click a row to zoom to it"""),
]
bad = [(o[:80], s.count(o)) for o, _ in pairs if s.count(o) != 1]
if bad:
    print('NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in pairs:
    s = s.replace(o, n)
p.write_text(s, encoding='utf-8')
print('list ok')

# Viewer wiring
v = Path(sys.argv[2])
t = v.read_text(encoding='utf-8')
vpairs = [
("""  const selectAutoIds = useCallback((ids: string[]) => {""", """  /** Profile set by hand in the list (""" + TAG + """): the markup's
   *  name, its size group and its auto tag change together, and the tag is
   *  flagged so re-runs keep the user's profile. */
  const setAutoProfile = useCallback((ids: string[], profile: string) => {
    const des = normalizeProfile(profile);
    if (!des) return;
    const set = new Set(ids);
    setMeasurements((prev) =>
      prev.map((m) =>
        set.has(m.id) && m.auto
          ? { ...m, annotation: des, group: autoGroupName(m.auto.cat, des), auto: { ...m.auto, des, ud: true } }
          : m,
      ),
    );
    addToast({ type: 'success', title: `Profile set to ${des}`, message: `${ids.length} markup${ids.length === 1 ? '' : 's'} updated. Re-runs keep it.` });
  }, [addToast]);

  const autoProfileOptions = useMemo(() => {
    const out = new Set<string>();
    for (const m of measurements) if (m.auto && m.auto.des && m.auto.des !== 'COLUMN') out.add(m.auto.des);
    return [...out].sort();
  }, [measurements]);

  const selectAutoIds = useCallback((ids: string[]) => {"""),
("""                  onSetHeight: setAutoColumnHeight,""", """                  onSetHeight: setAutoColumnHeight,
                  onSetProfile: setAutoProfile,
                  profileOptions: autoProfileOptions,"""),
("""  hasCombinedAutoCounts,
  rejectedFrom,""", """  hasCombinedAutoCounts,
  normalizeProfile,
  rejectedFrom,"""),
]
bad = [(o[:80], t.count(o)) for o, _ in vpairs if t.count(o) != 1]
if bad:
    print('VIEWER NOT WRITTEN:', *bad, sep='\n  ')
    sys.exit(1)
for o, n in vpairs:
    t = t.replace(o, n)
v.write_text(t, encoding='utf-8')
print('viewer ok')

// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * @mentions for the Team comments and the Studio chat.
 *
 * Type @ and every other person is listed; keep typing a first name, last
 * name or email and the list narrows (names with spaces work: "@K Pavan").
 * Picking one writes "@Full Name" into the text. Mentioned names are
 * highlighted while typing and in the posted text.
 */
import { useMemo, useRef, useState, type ReactNode } from 'react';

export type MentionPerson = { id: string; name: string; email: string };

export const personLabel = (p: { name?: string; email?: string }) => (p.name || '').trim() || p.email || 'Someone';

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Does a person match what was typed after @ ? */
export function matchesPerson(p: MentionPerson, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const name = personLabel(p).toLowerCase();
  if (name.startsWith(q) || p.email.toLowerCase().startsWith(q)) return true;
  // Any word of the name ("pavan" finds "K Pavan Kumar"), or the email's
  // first part.
  const words = name.split(/\s+/);
  for (let i = 0; i < words.length; i++) if (words.slice(i).join(' ').startsWith(q)) return true;
  return p.email.toLowerCase().split('@')[0]!.includes(q);
}

/** The text typed after the last @ before the caret (up to 3 words), or null. */
export function mentionQuery(text: string, caret: number): string | null {
  const upto = text.slice(0, caret);
  const m = /(^|\s)@([^@\n]{0,40})$/.exec(upto);
  if (!m) return null;
  const q = m[2]!;
  if (q.split(/\s+/).length > 4) return null;
  return q;
}

/** People named in a text: "@Full Name", "@email", or a unique "@FirstName". */
export function mentionedIn(text: string, people: MentionPerson[]): MentionPerson[] {
  const low = text.toLowerCase();
  const out = new Map<string, MentionPerson>();
  for (const p of people) {
    if (low.includes(`@${personLabel(p).toLowerCase()}`) || low.includes(`@${p.email.toLowerCase()}`)) out.set(p.id, p);
  }
  for (const m of low.matchAll(/@([^\s@]+)/g)) {
    const word = m[1]!.replace(/[.,;:!?]+$/, '');
    const hits = people.filter((p) => personLabel(p).toLowerCase().split(/\s+/).includes(word));
    if (hits.length === 1) out.set(hits[0]!.id, hits[0]!);
  }
  return [...out.values()];
}

/** The text with @mentions marked (known names first, then any @word). */
export function highlightMentions(text: string, people: MentionPerson[], markClass: string): ReactNode[] {
  const names = people
    .flatMap((p) => [personLabel(p), p.email])
    .filter(Boolean)
    .sort((a, b) => b.length - a.length)
    .map(escapeRe);
  const re = new RegExp(`(@(?:${names.length ? `${names.join('|')}|` : ''}[^\\s@]+))`, 'gi');
  return text.split(re).map((part, i) =>
    part.startsWith('@') ? (
      <mark key={i} className={markClass}>
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

/** State for a textarea / input with @ suggestions. */
export function useMentionComposer(people: MentionPerson[], me: string | null) {
  const [text, setText] = useState('');
  const [caret, setCaret] = useState(0);
  const boxRef = useRef<HTMLTextAreaElement | HTMLInputElement | null>(null);
  const others = useMemo(() => people.filter((p) => p.id !== me), [people, me]);
  const query = mentionQuery(text, caret);
  const suggestions = query === null ? [] : others.filter((p) => matchesPerson(p, query)).slice(0, 50);
  const onChange = (value: string, pos: number | null) => {
    setText(value);
    setCaret(pos ?? value.length);
  };
  const pick = (p: MentionPerson) => {
    const pos = caret;
    const before = text.slice(0, pos).replace(/@([^@\n]{0,40})$/, `@${personLabel(p)} `);
    const next = before + text.slice(pos);
    setText(next);
    setCaret(before.length);
    requestAnimationFrame(() => {
      const el = boxRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(before.length, before.length);
    });
  };
  const reset = () => {
    setText('');
    setCaret(0);
  };
  return { text, setText: (v: string) => onChange(v, v.length), onChange, setCaret, boxRef, query, suggestions, pick, reset, others };
}

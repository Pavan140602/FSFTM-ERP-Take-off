import { describe, expect, it } from 'vitest';
import {
  RECENT_ID,
  RECENT_MAX,
  addItem,
  addSet,
  defaultSets,
  deleteSet,
  itemFromMarkup,
  migrateV1,
  moveItem,
  parseSets,
  recordRecent,
  type ChestItem,
} from './tool-chest-sets';

const it1 = (id: string, color = '#ff0000'): ChestItem => ({ id, name: id, tool: 'distance', subject: 'Beam', label: id, style: { color } });

describe('tool chest sets', () => {
  it('always has Recent Tools first', () => {
    const sets = parseSets(JSON.stringify([{ id: 'x', name: 'Mine', items: [] }]));
    expect(sets[0]!.id).toBe(RECENT_ID);
    expect(sets[1]!.name).toBe('Mine');
    expect(parseSets('garbage')).toHaveLength(2);
  });
  it('records recent tools deduplicated and capped', () => {
    let sets = defaultSets();
    sets = recordRecent(sets, it1('a'));
    sets = recordRecent(sets, { ...it1('a2'), label: 'a', name: 'a' });
    expect(sets[0]!.items).toHaveLength(1); // same type, Subject, Label and look = one tool
    sets = recordRecent(sets, { ...it1('a3'), label: 'a', id: 'zz' });
    for (let i = 0; i < 20; i++) sets = recordRecent(sets, it1(`n${i}`));
    expect(sets[0]!.items.length).toBe(RECENT_MAX);
    expect(sets[0]!.items[0]!.id).toBe('n19');
  });
  it('moves between sets and copies out of Recent', () => {
    let sets = addSet(defaultSets(), 'CFS');
    const cfs = sets[2]!.id;
    sets = addItem(sets, 'my-tools', it1('t1'));
    sets = moveItem(sets, 't1', cfs);
    expect(sets.find((s) => s.id === cfs)!.items.map((i) => i.id)).toEqual(['t1']);
    expect(sets.find((s) => s.id === 'my-tools')!.items).toHaveLength(0);
    sets = recordRecent(sets, it1('r1'));
    sets = moveItem(sets, 'r1', 'my-tools');
    expect(sets[0]!.items).toHaveLength(1);
    expect(sets.find((s) => s.id === 'my-tools')!.items[0]!.id).not.toBe('r1');
    expect(deleteSet(sets, RECENT_ID)).toHaveLength(sets.length);
  });
  it('builds a tool from a markup and migrates v1', () => {
    const t = itemFromMarkup({ type: 'distance', annotation: 'W12X26', group: 'Beams', customFields: { Subject: 'Beam' }, color: '#123456', lineStyle: 'dashed', dispUnit: 'mm', bogus: 1 });
    expect(t).toMatchObject({ tool: 'distance', subject: 'Beam', label: 'W12X26', group: 'Beams', name: 'W12X26' });
    expect(t.style).toMatchObject({ color: '#123456', lineStyle: 'dashed', dispUnit: 'mm' });
    expect(migrateV1(JSON.stringify([{ id: 'o', name: 'Old', tool: 'area', color: '#00ff00' }]))[0]).toMatchObject({ name: 'Old', style: { color: '#00ff00' } });
  });
});

// OE-DELIVERY: 2026-11-05-upload-progress
import { describe, expect, it } from 'vitest';
import { formatTimeLeft, uploadStats } from '../lib/upload-progress';

const MB = 1024 * 1024;

describe('uploadStats', () => {
  it('reports percent, MB and time left at the average speed', () => {
    const s = uploadStats({ loaded: 10 * MB, total: 40 * MB, startedAt: 0 }, 5000);
    expect(s.percent).toBe(25);
    expect(s.sentMB).toBe(10);
    expect(s.totalMB).toBe(40);
    expect(s.secondsLeft).toBe(15); // 2 MB/s, 30 MB to go
    expect(s.processing).toBe(false);
  });

  it('has no estimate right at the start', () => {
    expect(uploadStats({ loaded: 1000, total: 40 * MB, startedAt: 0 }, 100).secondsLeft).toBeNull();
  });

  it('switches to processing once every byte is sent', () => {
    const s = uploadStats({ loaded: 40 * MB, total: 40 * MB, startedAt: 0 }, 9000);
    expect(s.percent).toBe(100);
    expect(s.processing).toBe(true);
    expect(s.secondsLeft).toBeNull();
  });
});

describe('formatTimeLeft', () => {
  it('reads like a person would say it', () => {
    expect(formatTimeLeft(null)).toBe('estimating time…');
    expect(formatTimeLeft(8)).toBe('8 s left');
    expect(formatTimeLeft(75)).toBe('1 min 15 s left');
    expect(formatTimeLeft(120)).toBe('2 min left');
  });
});

import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { clearShared, getShared, useSharedState } from './shared-state';

describe('useSharedState (split workspace shared by every viewer)', () => {
  it('shares one value between two components', () => {
    const a = renderHook(() => useSharedState('t.mode', 'off'));
    const b = renderHook(() => useSharedState('t.mode', 'off'));
    act(() => a.result.current[1]('vertical'));
    expect(b.result.current[0]).toBe('vertical');
    act(() => b.result.current[1]((prev) => (prev === 'vertical' ? 'horizontal' : prev)));
    expect(a.result.current[0]).toBe('horizontal');
    expect(getShared('t.mode')).toBe('horizontal');
  });

  it('clearing resets the workspace', () => {
    const h = renderHook(() => useSharedState('t2.x', 1));
    act(() => h.result.current[1](5));
    h.unmount();
    clearShared('t2.');
    expect(getShared('t2.x')).toBeUndefined();
    const again = renderHook(() => useSharedState('t2.x', 1));
    expect(again.result.current[0]).toBe(1);
  });
});

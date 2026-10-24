/**
 * The timeout that ends a wait nobody answered.
 *
 * This path never ran on the live instance: every start and stop came back
 * inside the window, so the only exercise it gets is here.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { PendingTimers } from '../src/rows';

const TIMEOUT = 20000;

describe('PendingTimers', () => {
  let timers: PendingTimers;
  let expired: string[];

  beforeEach(() => {
    vi.useFakeTimers();
    timers = new PendingTimers(TIMEOUT);
    expired = [];
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const record = (id: string) => expired.push(id);

  it('ends a wait nobody answered, once the timeout is up', () => {
    timers.start('switch.a', record);

    vi.advanceTimersByTime(TIMEOUT - 1);
    expect(expired).toEqual([]);

    vi.advanceTimersByTime(1);
    expect(expired).toEqual(['switch.a']);
  });

  it('forgets a wait it has ended, so nothing is left armed', () => {
    timers.start('switch.a', record);
    vi.advanceTimersByTime(TIMEOUT);

    expect(timers.size).toBe(0);
  });

  it('never fires a wait that was answered first', () => {
    timers.start('switch.a', record);
    timers.stop('switch.a');

    vi.advanceTimersByTime(TIMEOUT * 3);
    expect(expired).toEqual([]);
    expect(timers.size).toBe(0);
  });

  it('does not complain about stopping a wait that is not there', () => {
    expect(() => timers.stop('switch.never')).not.toThrow();
    expect(() => timers.stopAll()).not.toThrow();
  });

  it('times each switch on its own clock', () => {
    timers.start('switch.a', record);
    vi.advanceTimersByTime(TIMEOUT / 2);
    timers.start('switch.b', record);

    vi.advanceTimersByTime(TIMEOUT / 2);
    expect(expired).toEqual(['switch.a']);

    vi.advanceTimersByTime(TIMEOUT / 2);
    expect(expired).toEqual(['switch.a', 'switch.b']);
  });

  it('replaces a wait rather than stacking a second one on the same switch', () => {
    timers.start('switch.a', record);
    vi.advanceTimersByTime(TIMEOUT - 1);
    timers.start('switch.a', record);

    expect(timers.size).toBe(1);

    // The first timeout would have fired here had it survived the restart.
    vi.advanceTimersByTime(1);
    expect(expired).toEqual([]);

    vi.advanceTimersByTime(TIMEOUT - 1);
    expect(expired).toEqual(['switch.a']);
  });

  it('cancels everything on teardown, so nothing fires at a detached card', () => {
    timers.start('switch.a', record);
    timers.start('switch.b', record);

    timers.stopAll();

    vi.advanceTimersByTime(TIMEOUT * 3);
    expect(expired).toEqual([]);
    expect(timers.size).toBe(0);
  });

  it('is usable again after a teardown, a card being reconnected on every edit', () => {
    timers.start('switch.a', record);
    timers.stopAll();
    timers.start('switch.a', record);

    vi.advanceTimersByTime(TIMEOUT);
    expect(expired).toEqual(['switch.a']);
  });

  it('counts what is armed', () => {
    expect(timers.size).toBe(0);

    timers.start('switch.a', record);
    timers.start('switch.b', record);
    expect(timers.size).toBe(2);

    timers.stop('switch.a');
    expect(timers.size).toBe(1);
  });
});

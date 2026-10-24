import { describe, expect, it } from 'vitest';

import { HISTORY_WINDOW_MS, appendSample, parseHistory, sparklinePath } from '../src/history';
import type { Sample } from '../src/history';

const NOW = 1_800_000_000_000;

describe('parseHistory', () => {
  it('turns compressed states into readings, oldest first', () => {
    const response = {
      'sensor.cpu': [
        { s: '20', lu: 1_700_000_010 },
        { s: '10.5', lu: 1_700_000_000 },
      ],
    };

    expect(parseHistory(response, 'sensor.cpu')).toEqual([
      [1_700_000_000_000, 10.5],
      [1_700_000_010_000, 20],
    ]);
  });

  it('drops readings that are not numbers', () => {
    const response = {
      'sensor.cpu': [
        { s: 'unavailable', lu: 1 },
        { s: '', lu: 2 },
        { s: '7', lu: 3 },
      ],
    };

    expect(parseHistory(response, 'sensor.cpu')).toEqual([[3000, 7]]);
  });

  it('has nothing for an entity the recorder does not know', () => {
    expect(parseHistory({}, 'sensor.cpu')).toEqual([]);
  });
});

describe('appendSample', () => {
  const series: Sample[] = [[NOW - 1000, 5]];

  it('adds a newer reading', () => {
    expect(appendSample(series, NOW, '9', NOW)).toEqual([...series, [NOW, 9]]);
  });

  it('keeps the same series for a reading it already has, so Lit sees no change', () => {
    expect(appendSample(series, NOW - 1000, '5', NOW)).toBe(series);
  });

  it('keeps the same series for a state that is not a number', () => {
    expect(appendSample(series, NOW, 'unavailable', NOW)).toBe(series);
  });

  it('drops what has left the window', () => {
    const old: Sample[] = [
      [NOW - HISTORY_WINDOW_MS - 1, 1],
      [NOW - 10, 2],
    ];

    expect(appendSample(old, NOW, '3', NOW)).toEqual([
      [NOW - 10, 2],
      [NOW, 3],
    ]);
  });
});

describe('sparklinePath', () => {
  it('needs two points to draw a line', () => {
    expect(sparklinePath([], NOW, 100, 28)).toBeUndefined();
    expect(sparklinePath([[NOW, 50]], NOW, 100, 28)).toBeUndefined();
  });

  it('carries the last reading on to now', () => {
    expect(sparklinePath([[NOW - HISTORY_WINDOW_MS / 2, 50]], NOW, 100, 28)).toBe('M50.0,14.0L100.0,14.0');
  });

  it('starts at the window edge with the reading that held there', () => {
    expect(sparklinePath([[NOW - 2 * HISTORY_WINDOW_MS, 100]], NOW, 100, 28)).toBe('M0.0,0.0L100.0,0.0');
  });

  it('keeps values outside 0–100 on the chart', () => {
    expect(sparklinePath([[NOW - HISTORY_WINDOW_MS, 250]], NOW, 100, 28)).toBe('M0.0,0.0L100.0,0.0');
  });
});

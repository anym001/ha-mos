import { describe, expect, it } from 'vitest';

import { GAUGE_SIZE, gaugeGeometry, gaugePercent, severityFor } from '../src/gauge';

describe('severityFor', () => {
  it.each([
    [0, 'low'],
    [50, 'low'],
    [50.1, 'medium'],
    [75, 'medium'],
    [90, 'high'],
    [90.1, 'critical'],
    [100, 'critical'],
  ] as const)('reads %s%% as %s', (percent, severity) => {
    expect(severityFor(percent)).toBe(severity);
  });
});

describe('severityFor, inverted', () => {
  it('reads a full battery as fine and an empty one as critical', () => {
    expect(severityFor(100, true)).toBe('low');
    expect(severityFor(5, true)).toBe('critical');
  });
});

describe('gaugePercent', () => {
  it('reads a numeric state', () => {
    expect(gaugePercent('12.61')).toBe(12.61);
  });

  it('clamps to the ring, since a container can report more than one core', () => {
    expect(gaugePercent('240')).toBe(100);
    expect(gaugePercent('-3')).toBe(0);
  });

  it.each([undefined, '', ' ', 'unknown', 'unavailable'])('has no value for %j', (state) => {
    expect(gaugePercent(state)).toBeUndefined();
  });
});

describe('gaugeGeometry', () => {
  it('keeps the stroke inside the box and leaves a quarter open', () => {
    const { radius, circumference, sweep } = gaugeGeometry(4);

    expect(radius * 2 + 4).toBe(GAUGE_SIZE);
    expect(sweep / circumference).toBeCloseTo(0.75);
  });
});

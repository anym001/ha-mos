/**
 * Config validation, defaults, and the editor's two filter lines.
 *
 * The parity test at the end is the one that matters most: the editor showing a
 * switch as off while the card behaves as on is invisible until someone opens
 * the editor, saves, and finds their card has quietly changed.
 */
import { describe, expect, it } from 'vitest';

import {
  CARD_DEFAULTS,
  MAX_COLUMNS,
  OVERVIEW_DEFAULTS,
  OVERVIEW_TOGGLES,
  TOGGLES,
  foldFilter,
  normalizeConfig,
  normalizeOverviewConfig,
  patternsToText,
  textToPatterns,
} from '../src/config';
import { MOS_DEVICE_KINDS, ROW_SORTS, SECONDARY_INFO_MODES } from '../src/devices';
import type { MosCardConfig } from '../src/types';

const base = { type: 'custom:mos-card' } as MosCardConfig;

describe('normalizeConfig validation', () => {
  it('rejects nothing at all', () => {
    expect(() => normalizeConfig(undefined as unknown as MosCardConfig)).toThrow(/configuration/i);
  });

  it('rejects kinds that are not a list', () => {
    expect(() => normalizeConfig({ ...base, kinds: 'docker_container' } as unknown as MosCardConfig)).toThrow(/list/i);
  });

  it('rejects an empty kinds list rather than rendering an empty card', () => {
    expect(() => normalizeConfig({ ...base, kinds: [] })).toThrow(/empty/i);
  });

  it('names the unknown kind it found', () => {
    expect(() =>
      normalizeConfig({ ...base, kinds: ['docker_container', 'toaster'] } as unknown as MosCardConfig),
    ).toThrow(/toaster/);
  });

  it.each([...ROW_SORTS])('accepts the sort %s', (sort) => {
    expect(() => normalizeConfig({ ...base, sort })).not.toThrow();
  });

  it.each([...SECONDARY_INFO_MODES])('accepts the secondary info %s', (secondary_info) => {
    expect(() => normalizeConfig({ ...base, secondary_info })).not.toThrow();
  });

  it.each(['newest', '', 'NAME'])('rejects the sort %o', (sort) => {
    expect(() => normalizeConfig({ ...base, sort } as unknown as MosCardConfig)).toThrow(/sort/i);
  });

  it.each([0, -1, 1.5, '3'])('rejects max_rows %o', (max_rows) => {
    expect(() => normalizeConfig({ ...base, max_rows } as unknown as MosCardConfig)).toThrow();
  });

  it.each([0, MAX_COLUMNS + 1, 2.5])('rejects columns %o', (columns) => {
    expect(() => normalizeConfig({ ...base, columns } as unknown as MosCardConfig)).toThrow();
  });

  it('accepts every column the styles cover', () => {
    for (let columns = 1; columns <= MAX_COLUMNS; columns += 1) {
      expect(() => normalizeConfig({ ...base, columns })).not.toThrow();
    }
  });

  it('stops at two columns, the widest a card ever gets being about 500 px', () => {
    // Three was offered once and rendered as two, which is an option lying
    // about what it does. Pinned so it does not come back by way of a bigger
    // MAX_COLUMNS without the styles and the measurement behind it.
    expect(MAX_COLUMNS).toBe(2);
    expect(() => normalizeConfig({ ...base, columns: 3 })).toThrow(/columns/i);
  });
});

describe('normalizeConfig defaults', () => {
  it('shows all six kinds when none are named', () => {
    expect(normalizeConfig(base).kinds).toEqual([...MOS_DEVICE_KINDS]);
  });

  it('opens the more-info dialog on tap', () => {
    expect(normalizeConfig(base).tap_action).toEqual({ action: 'more-info' });
  });

  it('leaves the config alone where it speaks', () => {
    const config = normalizeConfig({ ...base, show_icon: false, sort: 'state', kinds: ['disk'] });

    expect(config.show_icon).toBe(false);
    expect(config.sort).toBe('state');
    expect(config.kinds).toEqual(['disk']);
  });

  it('keeps a false the caller set, rather than treating it as absent', () => {
    expect(normalizeConfig({ ...base, show_problem: false }).show_problem).toBe(false);
    expect(normalizeConfig({ ...base, show_update: false }).show_update).toBe(false);
  });

  it('adds no key the config did not ask for and the defaults do not name', () => {
    const config = normalizeConfig(base);

    expect(config.filter).toBeUndefined();
    expect(config.max_rows).toBeUndefined();
    expect(config.title).toBeUndefined();
    expect(config.server).toBeUndefined();
  });

  it('shows a fault unasked and hides nothing unasked', () => {
    const config = normalizeConfig(base);

    expect(config.show_problem).toBe(true);
    expect(config.hide_unavailable).toBe(false);
    expect(config.confirm_stop).toBe(false);
  });

  it('does not share the kinds array between two cards', () => {
    // The expected length is captured first on purpose. Reading
    // `MOS_DEVICE_KINDS.length` after the pop compares the mutated array with
    // itself, which passes even when every card shares one array.
    const expected = MOS_DEVICE_KINDS.length;
    const first = normalizeConfig(base);
    const second = normalizeConfig(base);

    first.kinds?.pop();

    expect(second.kinds).toHaveLength(expected);
    expect(second.kinds).not.toBe(first.kinds);
    expect(MOS_DEVICE_KINDS).toHaveLength(expected);
  });
});

describe('patternsToText and textToPatterns', () => {
  it('shows a list as one line and reads it back', () => {
    expect(patternsToText(['*arr', 'plex'])).toBe('*arr, plex');
    expect(textToPatterns('*arr, plex')).toEqual(['*arr', 'plex']);
  });

  it('shows a bare string, which the config also allows', () => {
    expect(patternsToText('arr')).toBe('arr');
  });

  it('shows nothing for nothing', () => {
    expect(patternsToText(undefined)).toBe('');
    expect(textToPatterns(undefined)).toEqual([]);
    expect(textToPatterns('')).toEqual([]);
  });

  it('drops blanks and stray whitespace rather than storing them', () => {
    expect(textToPatterns('  a ,, b  ,')).toEqual(['a', 'b']);
    expect(textToPatterns('   ')).toEqual([]);
  });

  it('round-trips a list unchanged', () => {
    const patterns = ['*arr', 'plex', 'home?age'];

    expect(textToPatterns(patternsToText(patterns))).toEqual(patterns);
  });
});

describe('foldFilter', () => {
  it('keeps no filter at all when both lines are empty', () => {
    expect(foldFilter('', '')).toBeUndefined();
    expect(foldFilter(undefined, undefined)).toBeUndefined();
    expect(foldFilter('  ', ' , ')).toBeUndefined();
  });

  it('keeps only the half that was filled in', () => {
    expect(foldFilter('*arr', '')).toEqual({ include: ['*arr'] });
    expect(foldFilter('', 'test')).toEqual({ exclude: ['test'] });
  });

  it('keeps both when both are filled in', () => {
    expect(foldFilter('*arr, plex', 'test')).toEqual({ include: ['*arr', 'plex'], exclude: ['test'] });
  });
});

describe('editor and card defaults', () => {
  const booleanDefaults = Object.entries(CARD_DEFAULTS)
    .filter(([, value]) => typeof value === 'boolean')
    .map(([name]) => name);

  it('offers a switch for every boolean the card has', () => {
    expect([...TOGGLES].sort()).toEqual([...booleanDefaults].sort());
  });

  it('offers no switch for an option the card does not have', () => {
    for (const option of TOGGLES) {
      expect(CARD_DEFAULTS).toHaveProperty(option);
    }
  });

  it('gives the editor the same answer the card acts on', () => {
    const config = normalizeConfig(base) as Record<string, unknown>;

    for (const [option, value] of Object.entries(CARD_DEFAULTS)) {
      expect(config[option]).toBe(value);
    }
  });

  it('starts every switch where the card behaves, not where it looks tidy', () => {
    // The three that are off are off for a reason, and flipping one silently
    // would change what an existing dashboard renders.
    expect(CARD_DEFAULTS.confirm_stop).toBe(false);
    expect(CARD_DEFAULTS.hide_unavailable).toBe(false);
    expect(CARD_DEFAULTS.show_server_summary).toBe(false);
    expect(CARD_DEFAULTS.compact).toBe(false);
    expect(CARD_DEFAULTS.show_problem).toBe(true);
    expect(CARD_DEFAULTS.show_update).toBe(true);
  });
});

describe('normalizeOverviewConfig', () => {
  it('turns every section on by default', () => {
    expect(normalizeOverviewConfig({ type: 'custom:mos-overview-card' })).toMatchObject(OVERVIEW_DEFAULTS);
  });

  it('keeps what the config sets', () => {
    expect(normalizeOverviewConfig({ type: 'x', show_ups: false }).show_ups).toBe(false);
  });

  it('rejects a switch that is not a boolean', () => {
    expect(() => normalizeOverviewConfig({ type: 'x', show_ups: 'no' as unknown as boolean })).toThrow('show_ups');
  });

  it('has a switch in the editor for every default', () => {
    expect([...OVERVIEW_TOGGLES].sort()).toEqual(Object.keys(OVERVIEW_DEFAULTS).sort());
  });
});

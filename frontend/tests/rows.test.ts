/**
 * Row logic: tone, order, capping and the pending power buttons.
 *
 * All of this used to sit on the component, where the only way to check it was
 * to render a card against a live Home Assistant. These are the cases that were
 * reasoned about rather than observed when it did.
 */
import { describe, expect, it } from 'vitest';
import type { ActionConfig } from 'custom-card-helpers';

import { MOS_DEVICE_KINDS } from '../src/devices';
import type { MosDeviceKind } from '../src/devices';
import {
  TONES,
  capRows,
  compareRows,
  countGroup,
  fillPlaceholders,
  isLinkableUrl,
  moreInfoEntity,
  settledPending,
  showsMeasurements,
  toneFor,
  upsFlags,
  uptimeSince,
} from '../src/rows';

describe('toneFor', () => {
  it.each(['running', 'on', 'active', 'ol', 'online', 'RUNNING', 'On'])('reads %s as active', (state) => {
    expect(toneFor('docker_container', state)).toBe('active');
  });

  it.each(['paused', 'frozen', 'standby', 'idle', 'sleeping', 'starting'])('reads %s as idle', (state) => {
    expect(toneFor('virtual_machine', state)).toBe('idle');
  });

  it.each(['exited', 'stopped', 'off', 'shut down'])('reads %s as inactive', (state) => {
    expect(toneFor('lxc_container', state)).toBe('inactive');
  });

  it.each(['unavailable', 'unknown', undefined])('reads %o as unknown, before anything else', (state) => {
    expect(toneFor('docker_container', state)).toBe('unknown');
    expect(toneFor('disk', state)).toBe('unknown');
  });

  it.each(['disk', 'storage_pool'] as const)('leaves %s neutral whatever it reports', (kind) => {
    // A disk reporting `active` names its ATA power mode, not good news.
    expect(toneFor(kind, 'active')).toBe('neutral');
    expect(toneFor(kind, 'standby')).toBe('neutral');
    expect(toneFor(kind, '42')).toBe('neutral');
  });

  it('colours the UPS, which has no power switch but does report mains power', () => {
    // `ol` is NUT for "on line". Grouping the UPS with the other switchless
    // kinds is the obvious simplification and the wrong one.
    expect(toneFor('ups', 'ol')).toBe('active');
    expect(toneFor('ups', 'ob')).toBe('inactive');
  });

  it.each([...MOS_DEVICE_KINDS])('always answers with a tone the styles cover, for %s', (kind) => {
    for (const state of ['running', 'weird', 'unknown', '']) {
      expect(TONES).toContain(toneFor(kind, state));
    }
  });
});

describe('compareRows', () => {
  const row = (name: string, kind: MosDeviceKind = 'docker_container', state?: string) => ({ name, kind, state });

  type Row = ReturnType<typeof row>;

  const stateOf = (r: Row) => r.state;

  it('sorts by name when asked for name, whatever the states are', () => {
    const rows = [row('Zulu', 'docker_container', 'running'), row('Alpha', 'docker_container', 'exited')];

    expect([...rows].sort(compareRows('name', stateOf)).map((r) => r.name)).toEqual(['Alpha', 'Zulu']);
  });

  it('sorts by name when the config says nothing', () => {
    const rows = [row('Zulu'), row('Alpha')];

    expect([...rows].sort(compareRows(undefined, stateOf)).map((r) => r.name)).toEqual(['Alpha', 'Zulu']);
  });

  it('puts running first, then idle, then stopped, then unknown', () => {
    const rows = [
      row('d', 'docker_container', 'unavailable'),
      row('c', 'docker_container', 'exited'),
      row('b', 'docker_container', 'paused'),
      row('a', 'docker_container', 'running'),
    ];

    expect([...rows].sort(compareRows('state', stateOf)).map((r) => r.name)).toEqual(['a', 'b', 'c', 'd']);
  });

  it('falls back to the name inside one state, so the order is stable', () => {
    const rows = [row('Zulu', 'docker_container', 'running'), row('Alpha', 'docker_container', 'running')];

    expect([...rows].sort(compareRows('state', stateOf)).map((r) => r.name)).toEqual(['Alpha', 'Zulu']);
  });

  it('leaves disks alphabetical under state sorting, their tone being neutral', () => {
    const rows = [row('vdb', 'disk', 'standby'), row('vda', 'disk', 'active')];

    expect([...rows].sort(compareRows('state', stateOf)).map((r) => r.name)).toEqual(['vda', 'vdb']);
  });

  it('ranks a running container above a neutral disk', () => {
    const rows = [row('disk', 'disk', 'active'), row('box', 'docker_container', 'running')];

    expect([...rows].sort(compareRows('state', stateOf)).map((r) => r.name)).toEqual(['box', 'disk']);
  });
});

describe('capRows', () => {
  const rows = ['a', 'b', 'c', 'd'];

  it('hides nothing without a cap', () => {
    expect(capRows(rows, undefined, false)).toEqual({ rows, hidden: 0 });
  });

  it('hides nothing when the group is opened', () => {
    expect(capRows(rows, 2, true)).toEqual({ rows, hidden: 0 });
  });

  it('hides nothing when there are fewer rows than the cap', () => {
    expect(capRows(rows, 9, false)).toEqual({ rows, hidden: 0 });
  });

  it('reports no overflow when the count matches the cap exactly', () => {
    expect(capRows(rows, 4, false)).toEqual({ rows, hidden: 0 });
  });

  it('keeps the top of the order and counts the rest', () => {
    expect(capRows(rows, 2, false)).toEqual({ rows: ['a', 'b'], hidden: 2 });
  });

  it('keeps the top of a state-sorted order, the cap being applied after sorting', () => {
    const sorted = [
      { name: 'up', kind: 'docker_container' as const, state: 'running' },
      { name: 'down', kind: 'docker_container' as const, state: 'exited' },
    ].sort(compareRows('state', (r) => r.state));

    expect(capRows(sorted, 1, false).rows.map((r) => r.name)).toEqual(['up']);
  });

  it('returns a copy, so a caller cannot sort the stored rows by accident', () => {
    const capped = capRows(rows, undefined, false);

    capped.rows.push('e');
    expect(rows).toHaveLength(4);
  });
});

describe('settledPending', () => {
  const states: Record<string, string> = { 'switch.a': 'on', 'switch.b': 'off' };
  const stateOf = (id: string) => states[id];

  it('reports nothing while every switch still reads as it did', () => {
    expect(settledPending(new Map([['switch.a', 'on']]), stateOf)).toEqual([]);
  });

  it('reports a switch that has flipped', () => {
    expect(settledPending(new Map([['switch.a', 'off']]), stateOf)).toEqual(['switch.a']);
  });

  it('treats a switch that has gone away as answered, rather than spinning to the timeout', () => {
    expect(settledPending(new Map([['switch.gone', 'on']]), stateOf)).toEqual(['switch.gone']);
  });

  it('treats a press on an entity that had no state as answered once it gets one', () => {
    expect(settledPending(new Map([['switch.a', '']]), stateOf)).toEqual(['switch.a']);
    expect(settledPending(new Map([['switch.gone', '']]), stateOf)).toEqual([]);
  });

  it('answers each switch on its own', () => {
    const pending = new Map([
      ['switch.a', 'on'],
      ['switch.b', 'on'],
    ]);

    expect(settledPending(pending, stateOf)).toEqual(['switch.b']);
  });

  it('reports nothing for an empty wait', () => {
    expect(settledPending(new Map(), stateOf)).toEqual([]);
  });
});

describe('isLinkableUrl', () => {
  it.each([
    'http://10.0.1.30:8080/',
    'https://nas.example.org',
    'http://192.168.1.5',
    'homeassistant://navigate/lovelace/0',
  ])('accepts %s', (url) => {
    expect(isLinkableUrl(url)).toBe(true);
  });

  it('rejects a javascript: URL, which would run on click', () => {
    expect(isLinkableUrl('javascript:alert(1)')).toBe(false);
    expect(isLinkableUrl('JavaScript:alert(1)')).toBe(false);
  });

  it.each(['data:text/html,<script>1</script>', 'vbscript:msgbox', 'file:///etc/passwd'])('rejects %s', (url) => {
    expect(isLinkableUrl(url)).toBe(false);
  });

  it('rejects a scheme with no host, which is not a web interface', () => {
    // `https:///path` is deliberately not in here: the WHATWG parser reads the
    // extra slash away and resolves it to `https://path/`, host and all, which
    // is exactly what a browser would follow.
    expect(isLinkableUrl('http://')).toBe(false);
    expect(isLinkableUrl('homeassistant:')).toBe(false);
  });

  it('rejects something that is not a URL at all', () => {
    expect(isLinkableUrl('not a url')).toBe(false);
    expect(isLinkableUrl('/local/page.html')).toBe(false);
  });

  it('treats an absent URL as no link', () => {
    expect(isLinkableUrl(undefined)).toBe(false);
    expect(isLinkableUrl('')).toBe(false);
  });
});

describe('fillPlaceholders', () => {
  const values = {
    entity: 'sensor.immich_cli',
    power: undefined,
    device_id: 'dev-1',
    name: 'immich-cli',
    kind: 'lxc_container',
  };

  it('replaces a placeholder that is the whole string', () => {
    expect(fillPlaceholders('[[entity]]', values)).toBe('sensor.immich_cli');
  });

  it('replaces every occurrence inside a longer string', () => {
    expect(fillPlaceholders('[[name]] ([[kind]]) → [[name]]', values)).toBe('immich-cli (lxc_container) → immich-cli');
  });

  it('reaches placeholders nested in objects and arrays', () => {
    const config = {
      action: 'fire-dom-event',
      browser_mod: {
        service: 'browser_mod.popup',
        data: {
          title: '[[name]]',
          content: { type: 'entities', entities: ['[[entity]]', 'sensor.fixed'] },
        },
      },
    };

    expect(fillPlaceholders(config, values)).toEqual({
      action: 'fire-dom-event',
      browser_mod: {
        service: 'browser_mod.popup',
        data: {
          title: 'immich-cli',
          content: { type: 'entities', entities: ['sensor.immich_cli', 'sensor.fixed'] },
        },
      },
    });
  });

  // The config object is the card's, shared by every row. Substituting into it
  // would give the second row the first row's entity, and permanently: the
  // placeholder is gone from the config after the first tap.
  it('leaves the config it was given untouched', () => {
    const config = { action: 'navigate', navigation_path: '/lovelace/[[name]]' };
    const filled = fillPlaceholders(config, values);

    expect(config.navigation_path).toBe('/lovelace/[[name]]');
    expect(filled.navigation_path).toBe('/lovelace/immich-cli');
  });

  it('leaves a key it does not know in place, so a typo is visible', () => {
    expect(fillPlaceholders('[[entty]]', values)).toBe('[[entty]]');
  });

  // Inherited properties are not values: `[[constructor]]` is a typo like any
  // other, not a placeholder that happens to resolve against Object.prototype.
  it('leaves an inherited property name in place', () => {
    expect(fillPlaceholders('[[constructor]]', values)).toBe('[[constructor]]');
  });

  it('empties a key the row has no value for', () => {
    expect(fillPlaceholders({ entity: '[[power]]' }, values)).toEqual({ entity: '' });
  });

  it('returns what it cannot substitute into unchanged', () => {
    expect(fillPlaceholders(undefined, values)).toBeUndefined();
    expect(fillPlaceholders({ action: 'toggle', confirmation: true, size: 3 }, values)).toEqual({
      action: 'toggle',
      confirmation: true,
      size: 3,
    });
  });
});

describe('moreInfoEntity', () => {
  const values = {
    entity: 'sensor.immich_cli',
    power: 'switch.immich_cli',
    device_id: 'dev-1',
    name: 'immich-cli',
    kind: 'lxc_container',
  };

  it('lifts the entity a more-info action names, substituted', () => {
    expect(moreInfoEntity({ action: 'more-info', entity: '[[power]]' }, values)).toBe('switch.immich_cli');
  });

  it('takes a literal entity as written', () => {
    expect(moreInfoEntity({ action: 'more-info', entity: 'sensor.fixed' }, values)).toBe('sensor.fixed');
  });

  it('has nothing to lift from a more-info action without an entity', () => {
    expect(moreInfoEntity({ action: 'more-info' }, values)).toBeUndefined();
    expect(moreInfoEntity(undefined, values)).toBeUndefined();
  });

  // An `entity` inside a `fire-dom-event` payload belongs to whatever the popup
  // does with it, and opening a more-info dialog is not that.
  it('leaves an entity in another action where it is', () => {
    expect(
      moreInfoEntity({ action: 'fire-dom-event', entity: '[[power]]' } as unknown as ActionConfig, values),
    ).toBeUndefined();
    expect(
      moreInfoEntity({ action: 'toggle', entity: '[[power]]' } as unknown as ActionConfig, values),
    ).toBeUndefined();
  });

  // A row that has no switch — a disk, a pool, the UPS. The caller falls back
  // to the row's own entity, so the tap opens its dialog instead of none.
  it('reports nothing when the placeholder empties', () => {
    expect(
      moreInfoEntity({ action: 'more-info', entity: '[[power]]' }, { ...values, power: undefined }),
    ).toBeUndefined();
  });

  it('keeps an unknown key, so a typo opens a dialog that names it', () => {
    expect(moreInfoEntity({ action: 'more-info', entity: '[[entty]]' }, values)).toBe('[[entty]]');
  });
});

describe('countGroup', () => {
  it('counts the rows that are up and the ones with an update waiting', () => {
    expect(
      countGroup('docker_container', [
        { state: 'running', update: 'on' },
        { state: 'exited', update: 'off' },
        { state: 'running', update: undefined },
        { state: 'unavailable', update: 'on' },
      ]),
    ).toEqual({ running: 2, total: 4, updates: 2 });
  });

  it('is zero across the board for an empty group', () => {
    expect(countGroup('virtual_machine', [])).toEqual({ running: 0, total: 0, updates: 0 });
  });
});

describe('uptimeSince', () => {
  const now = Date.parse('2026-10-23T12:00:00Z');

  it('splits the time since boot into days, hours and minutes', () => {
    expect(uptimeSince('2026-10-21T09:33:00Z', now)).toEqual({ days: 2, hours: 2, minutes: 27 });
  });

  it.each([undefined, '', 'unknown', '2026-10-24T00:00:00Z'])('has no uptime for %j', (state) => {
    expect(uptimeSince(state, now)).toBeUndefined();
  });
});

describe('showsMeasurements', () => {
  it.each(['running', 'paused'])('shows a guest that is %s', (state) => {
    expect(showsMeasurements('lxc_container', state)).toBe(true);
  });

  it.each(['stopped', 'exited', 'unavailable', undefined])('hides a guest that is %s', (state) => {
    expect(showsMeasurements('docker_container', state)).toBe(false);
  });

  it('always shows the kinds that do not run', () => {
    expect(showsMeasurements('storage_pool', undefined)).toBe(true);
    expect(showsMeasurements('ups', 'OB')).toBe(true);
  });
});

describe('upsFlags', () => {
  it('splits a status into its flags and marks the known ones', () => {
    expect(upsFlags('OL CHRG')).toEqual([
      { flag: 'OL', known: true },
      { flag: 'CHRG', known: true },
    ]);
  });

  it('keeps a flag it does not know', () => {
    expect(upsFlags('OB  XYZ')).toEqual([
      { flag: 'OB', known: true },
      { flag: 'XYZ', known: false },
    ]);
  });

  it('has no flags for an empty status', () => {
    expect(upsFlags(undefined)).toEqual([]);
  });
});

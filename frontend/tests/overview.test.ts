/**
 * The overview card's condensing: per-kind counts and sums, the disk line,
 * pools and the UPS, read off registry entries and a state lookup.
 */
import { describe, expect, it } from 'vitest';

import { GUEST_KINDS, activeProblems, buildOverview, sumStates } from '../src/overview';
import type { StateLookup } from '../src/overview';
import { SERVER, device, entity } from './fixtures';

const states = (values: Record<string, string | [string, Record<string, unknown>]>): StateLookup => {
  return (id) => {
    const value = values[id];

    if (value === undefined) {
      return undefined;
    }

    return Array.isArray(value) ? { state: value[0], attributes: value[1] } : { state: value, attributes: {} };
  };
};

const guest = (id: string, kind: string) => device({ id, name: `Pluto ${id}`, model_id: kind, via_device_id: 'srv1' });

const DEVICES = [
  SERVER,
  guest('c1', 'docker_container'),
  guest('c2', 'docker_container'),
  guest('vm1', 'virtual_machine'),
  guest('d1', 'disk'),
  guest('d2', 'disk'),
  guest('p1', 'storage_pool'),
  guest('u1', 'ups'),
];

const ENTITIES = [
  entity({ entity_id: 'sensor.mem_docker', translation_key: 'memory_docker', device_id: 'srv1' }),
  entity({ entity_id: 'sensor.c1_state', translation_key: 'docker_state', device_id: 'c1' }),
  entity({ entity_id: 'sensor.c1_cpu', translation_key: 'docker_cpu_usage', device_id: 'c1' }),
  entity({ entity_id: 'binary_sensor.c1_update', translation_key: 'docker_update_available', device_id: 'c1' }),
  entity({ entity_id: 'sensor.c2_state', translation_key: 'docker_state', device_id: 'c2' }),
  entity({ entity_id: 'sensor.c2_cpu', translation_key: 'docker_cpu_usage', device_id: 'c2' }),
  entity({ entity_id: 'sensor.vm1_state', translation_key: 'vm_state', device_id: 'vm1' }),
  entity({ entity_id: 'sensor.d1_power', translation_key: 'disk_power_status', device_id: 'd1' }),
  entity({ entity_id: 'sensor.d1_temp', translation_key: 'disk_temperature', device_id: 'd1' }),
  entity({ entity_id: 'binary_sensor.d1_smart', translation_key: 'disk_smart_warning', device_id: 'd1' }),
  entity({ entity_id: 'sensor.d2_power', translation_key: 'disk_power_status', device_id: 'd2' }),
  entity({ entity_id: 'sensor.d2_temp', translation_key: 'disk_temperature', device_id: 'd2' }),
  entity({ entity_id: 'sensor.p1_usage', translation_key: 'pool_usage', device_id: 'p1' }),
  entity({ entity_id: 'sensor.p1_free', translation_key: 'pool_free_space', device_id: 'p1' }),
  entity({ entity_id: 'sensor.p1_total', translation_key: 'pool_total_space', device_id: 'p1' }),
  entity({ entity_id: 'binary_sensor.p1_scrub', translation_key: 'pool_scrub_running', device_id: 'p1' }),
  entity({ entity_id: 'sensor.u1_status', translation_key: 'ups_status', device_id: 'u1' }),
  entity({ entity_id: 'sensor.u1_charge', translation_key: 'ups_battery_charge', device_id: 'u1' }),
];

const STATES = states({
  'sensor.c1_state': 'running',
  'sensor.c1_cpu': '2.5',
  'binary_sensor.c1_update': 'on',
  'sensor.c2_state': 'exited',
  'sensor.c2_cpu': 'unavailable',
  'sensor.vm1_state': 'running',
  'sensor.d1_power': 'active',
  'sensor.d1_temp': '41',
  'binary_sensor.d1_smart': ['on', { device_class: 'problem' }],
  'sensor.d2_power': 'standby',
  'sensor.d2_temp': '35',
});

describe('sumStates', () => {
  it('adds up the states that are numbers', () => {
    expect(sumStates(['1.5', 'unavailable', undefined, '', '2'])).toBe(3.5);
  });

  it('has no sum when nothing is a number', () => {
    expect(sumStates(['unknown', undefined])).toBeUndefined();
  });
});

describe('buildOverview', () => {
  const overview = buildOverview(DEVICES, ENTITIES, SERVER, STATES);

  it('summarises only the guest kinds the server has, in kind order', () => {
    expect(overview.kinds.map((kind) => kind.kind)).toEqual(['docker_container', 'virtual_machine']);
    expect(GUEST_KINDS).not.toContain('disk');
  });

  it('counts what runs and what waits on an update, and adds up the CPU', () => {
    const [docker] = overview.kinds;

    expect(docker.counts).toEqual({ running: 1, total: 2, updates: 1 });
    expect(docker.cpu).toBe(2.5);
    expect(docker.memory?.entity_id).toBe('sensor.mem_docker');
  });

  it('has no memory for a kind the server keeps no total for', () => {
    expect(overview.kinds[1].memory).toBeUndefined();
    expect(overview.kinds[1].cpu).toBeUndefined();
  });

  it('condenses the disks into one line', () => {
    expect(overview.disks).toMatchObject({ total: 2, standby: 1, problems: 1 });
    expect(overview.disks?.hottest?.entity_id).toBe('sensor.d1_temp');
  });

  it('keeps each pool with its usage, free of total and jobs', () => {
    const [pool] = overview.pools;

    expect(pool.usage?.entity_id).toBe('sensor.p1_usage');
    expect(pool.free?.entity.entity_id).toBe('sensor.p1_free');
    expect(pool.free?.over?.entity_id).toBe('sensor.p1_total');
    expect(pool.activities.map((a) => a.entity.entity_id)).toEqual(['binary_sensor.p1_scrub']);
  });

  it('gives the UPS its status and the measurements it has', () => {
    const [ups] = overview.ups;

    expect(ups.status?.entity_id).toBe('sensor.u1_status');
    expect(ups.metrics.map((m) => m.entity.entity_id)).toEqual(['sensor.u1_charge']);
  });

  it('lists every entity it read, so the card can watch them', () => {
    const watched = [
      ...overview.kinds.flatMap((kind) => kind.entityIds),
      ...(overview.disks?.entityIds ?? []),
      ...overview.pools.flatMap((pool) => pool.entityIds),
      ...overview.ups.flatMap((ups) => ups.entityIds),
    ];

    expect(new Set(watched)).toEqual(new Set(ENTITIES.map((e) => e.entity_id)));
  });

  it('has no disk line for a server without disks', () => {
    expect(buildOverview([SERVER], [], SERVER, STATES).disks).toBeUndefined();
  });
});

describe('activeProblems', () => {
  it('counts problem sensors that are on, and nothing else', () => {
    const candidates = [
      entity({ entity_id: 'binary_sensor.d1_smart' }),
      entity({ entity_id: 'sensor.d1_temp' }),
      entity({ entity_id: 'binary_sensor.missing' }),
    ];

    expect(activeProblems(STATES, candidates)).toBe(1);
  });
});

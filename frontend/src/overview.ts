/**
 * What the overview card condenses a server into: one summary per guest kind,
 * one line for the disks, the pools and the UPS as they are.
 *
 * Takes registry entries and a state lookup and returns plain values, so it
 * runs without a DOM — the card only draws what comes out of here.
 */
import {
  KIND_INFO,
  MOS_DEVICE_KINDS,
  entitiesByDevice,
  findActivities,
  findMetricEntity,
  findProblemCandidates,
  findStateEntity,
  findUpdateEntity,
  metricsForMode,
  selectMosDevices,
} from './devices';
import type { DeviceRegistryEntry, EntityRegistryEntry, MetricRef, MosDeviceKind, RowMetric } from './devices';
import { countGroup } from './rows';
import type { GroupCounts } from './rows';

/** Reads an entity's state; undefined when Home Assistant has none. */
export type StateLookup = (entityId: string) => { state: string; attributes: Record<string, unknown> } | undefined;

/** The kinds that run, and so are summarised by how many of them do. */
export const GUEST_KINDS: readonly MosDeviceKind[] = MOS_DEVICE_KINDS.filter((kind) => KIND_INFO[kind].hasPower);

/**
 * The server sensor carrying the memory a kind uses altogether.
 *
 * Read off the server rather than summed from the guests, because the guests
 * report in whatever unit suits each one and the server already has the total.
 * Compose stacks run as Docker containers, so their memory is in Docker's.
 */
const KIND_MEMORY: Partial<Record<MosDeviceKind, MetricRef>> = {
  docker_container: {
    translationKey: 'memory_docker',
    keySuffix: 'memory_docker',
    label: 'memory',
    icon: 'mdi:memory',
  },
  lxc_container: { translationKey: 'memory_lxc', keySuffix: 'memory_lxc', label: 'memory', icon: 'mdi:memory' },
  virtual_machine: { translationKey: 'memory_vms', keySuffix: 'memory_vms', label: 'memory', icon: 'mdi:memory' },
};

export interface KindSummary {
  readonly kind: MosDeviceKind;
  readonly counts: GroupCounts;
  /** The guests' CPU usage added up, in percent; undefined when none reports one. */
  readonly cpu?: number;
  /** The server's sensor for this kind's memory, where it has one. */
  readonly memory?: EntityRegistryEntry;
  /** Every entity the summary was read from, for the card's re-render check. */
  readonly entityIds: readonly string[];
}

export interface DiskSummary {
  readonly total: number;
  readonly standby: number;
  /** The warmest disk's temperature entity, for its figure and unit. */
  readonly hottest?: EntityRegistryEntry;
  readonly problems: number;
  readonly entityIds: readonly string[];
}

export interface PoolSummary {
  readonly device: DeviceRegistryEntry;
  readonly usage?: EntityRegistryEntry;
  readonly free?: RowMetric;
  readonly activities: readonly RowMetric[];
  readonly problems: readonly EntityRegistryEntry[];
  readonly entityIds: readonly string[];
}

export interface UpsSummary {
  readonly device: DeviceRegistryEntry;
  readonly status?: EntityRegistryEntry;
  readonly metrics: readonly RowMetric[];
  readonly problems: readonly EntityRegistryEntry[];
  readonly entityIds: readonly string[];
}

export interface ServerOverview {
  readonly kinds: readonly KindSummary[];
  readonly disks?: DiskSummary;
  readonly pools: readonly PoolSummary[];
  readonly ups: readonly UpsSummary[];
}

/** The numbers among some states added up; undefined when none of them is a number. */
export function sumStates(states: ReadonlyArray<string | undefined>): number | undefined {
  const numbers = states
    .filter((state): state is string => state !== undefined && state.trim() !== '')
    .map(Number)
    .filter(Number.isFinite);

  return numbers.length ? numbers.reduce((total, value) => total + value, 0) : undefined;
}

const ids = (...entities: Array<EntityRegistryEntry | undefined>): string[] =>
  entities.filter((entity): entity is EntityRegistryEntry => entity !== undefined).map((entity) => entity.entity_id);

const isProblem = (states: StateLookup, entity: EntityRegistryEntry): boolean => {
  const stateObj = states(entity.entity_id);

  return stateObj?.attributes.device_class === 'problem' && stateObj.state === 'on';
};

/** Condense one server into what the overview card shows. */
export function buildOverview(
  devices: DeviceRegistryEntry[],
  entities: EntityRegistryEntry[],
  server: DeviceRegistryEntry,
  states: StateLookup,
): ServerOverview {
  const index = entitiesByDevice(entities);
  const serverEntities = index.get(server.id) ?? [];
  const stateOf = (entity?: EntityRegistryEntry): string | undefined =>
    entity ? states(entity.entity_id)?.state : undefined;

  const kinds = GUEST_KINDS.flatMap((kind): KindSummary[] => {
    const guests = selectMosDevices(devices, [kind], server.id);

    if (!guests.length) {
      return [];
    }

    const [cpuRef] = metricsForMode(kind, 'cpu');
    const memoryRef = KIND_MEMORY[kind];
    const memory = memoryRef ? findMetricEntity(serverEntities, memoryRef) : undefined;
    const rows = guests.map((guest) => {
      const guestEntities = index.get(guest.id) ?? [];

      return {
        stateEntity: findStateEntity(guestEntities, kind),
        updateEntity: findUpdateEntity(guestEntities, kind),
        cpuEntity: cpuRef ? findMetricEntity(guestEntities, cpuRef) : undefined,
      };
    });

    return [
      {
        kind,
        counts: countGroup(
          kind,
          rows.map((row) => ({ state: stateOf(row.stateEntity), update: stateOf(row.updateEntity) })),
        ),
        cpu: sumStates(rows.map((row) => stateOf(row.cpuEntity))),
        memory,
        entityIds: [...ids(memory), ...rows.flatMap((row) => ids(row.stateEntity, row.updateEntity, row.cpuEntity))],
      },
    ];
  });

  const diskDevices = selectMosDevices(devices, ['disk'], server.id);
  let disks: DiskSummary | undefined;

  if (diskDevices.length) {
    const [, temperatureRef] = metricsForMode('disk', 'auto');
    const rows = diskDevices.map((disk) => {
      const diskEntities = index.get(disk.id) ?? [];

      return {
        power: findStateEntity(diskEntities, 'disk'),
        temperature: temperatureRef ? findMetricEntity(diskEntities, temperatureRef) : undefined,
        problems: findProblemCandidates(diskEntities),
      };
    });
    const hottest = rows
      .map((row) => row.temperature)
      .filter((entity): entity is EntityRegistryEntry => entity !== undefined)
      .filter((entity) => Number.isFinite(Number(stateOf(entity))))
      .sort((a, b) => Number(stateOf(b)) - Number(stateOf(a)))[0];

    disks = {
      total: diskDevices.length,
      standby: rows.filter((row) => stateOf(row.power) === 'standby').length,
      hottest,
      problems: rows.filter((row) => row.problems.some((entity) => isProblem(states, entity))).length,
      entityIds: rows.flatMap((row) => [...ids(row.power, row.temperature), ...ids(...row.problems)]),
    };
  }

  const pools = selectMosDevices(devices, ['storage_pool'], server.id).map((pool): PoolSummary => {
    const poolEntities = index.get(pool.id) ?? [];
    const usage = findStateEntity(poolEntities, 'storage_pool');
    const [freeRef] = metricsForMode('storage_pool', 'auto');
    const freeEntity = findMetricEntity(poolEntities, freeRef);
    const free = freeEntity
      ? { ref: freeRef, entity: freeEntity, over: freeRef.over && findMetricEntity(poolEntities, freeRef.over) }
      : undefined;
    const activities = findActivities(poolEntities, 'storage_pool');
    const problems = findProblemCandidates(poolEntities);

    return {
      device: pool,
      usage,
      free,
      activities,
      problems,
      entityIds: [
        ...ids(usage, free?.entity, free?.over),
        ...activities.map((a) => a.entity.entity_id),
        ...ids(...problems),
      ],
    };
  });

  const ups = selectMosDevices(devices, ['ups'], server.id).map((device): UpsSummary => {
    const upsEntities = index.get(device.id) ?? [];
    const status = findStateEntity(upsEntities, 'ups');
    const metrics = metricsForMode('ups', 'auto').flatMap((ref) => {
      const entity = findMetricEntity(upsEntities, ref);

      return entity ? [{ ref, entity }] : [];
    });
    const problems = findProblemCandidates(upsEntities);

    return {
      device,
      status,
      metrics,
      problems,
      entityIds: [...ids(status), ...metrics.map((m) => m.entity.entity_id), ...ids(...problems)],
    };
  });

  return { kinds, disks, pools, ups };
}

/** The problems among some candidates that are reporting one right now. */
export function activeProblems(states: StateLookup, candidates: readonly EntityRegistryEntry[]): number {
  return candidates.filter((entity) => isProblem(states, entity)).length;
}

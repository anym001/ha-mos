/**
 * Device discovery for the MOS NAS integration.
 *
 * Everything this card renders comes out of the Home Assistant **device
 * registry**, filtered on `model_id`. That is a deliberate, documented contract
 * on the integration side — see `docs/development/ARCHITECTURE.md` ("Base
 * Entity") and the decision log entry _Container Devices Carry Their Kind in
 * `model_id`_ in `docs/development/DECISIONS.md` in the ha-mos repository.
 *
 * Two things follow from anchoring here rather than anywhere else:
 *
 *  - `model_id` is machine-readable by contract, where a device's `identifiers`
 *    carry an internal format the integration reserves the right to change and
 *    the display name belongs to the user. Matching either of those would break
 *    on a rename or a refactor; matching `model_id` does not.
 *  - The integration adds and removes these devices at runtime through
 *    `async_setup_dynamic_entities`, so following the registry gets lifecycle
 *    for free. A deleted container disappears from the card, a new one shows
 *    up, and a container behind a failing endpoint keeps its device and merely
 *    reports its entities unavailable. There is nothing to refresh by hand.
 */

import { createCollection } from 'home-assistant-js-websocket';
import type { Connection, UnsubscribeFunc } from 'home-assistant-js-websocket';

/**
 * The `model_id` values the integration writes onto its container devices.
 *
 * These are a released, public contract: the integration treats them as fixed
 * once shipped, and this card matches on them verbatim. The MOS *server* device
 * deliberately carries no `model_id` at all — it is identified instead by being
 * the `via_device_id` target of the devices below.
 */
export const MOS_DEVICE_KINDS = [
  'docker_container',
  'compose_stack',
  'lxc_container',
  'virtual_machine',
  'disk',
  'storage_pool',
  'ups',
] as const;

export type MosDeviceKind = (typeof MOS_DEVICE_KINDS)[number];

const MOS_DEVICE_KIND_SET: ReadonlySet<string> = new Set(MOS_DEVICE_KINDS);

/** The order rows are listed in within a group. */
export const ROW_SORTS = ['name', 'state'] as const;

export type RowSort = (typeof ROW_SORTS)[number];

export function isMosDeviceKind(value: unknown): value is MosDeviceKind {
  return typeof value === 'string' && MOS_DEVICE_KIND_SET.has(value);
}

/**
 * Per-kind rendering facts.
 *
 * `stateTranslationKey` names the entity that carries the row's headline value.
 * For the four guest kinds that entity also carries the MOS template icon as
 * its `entity_picture`, and the two Docker ones additionally carry
 * `web_ui_url` as an attribute — beside the container's `repo`, `network_mode`
 * and image metadata, or the stack's services, containers and images — which is
 * why a whole row can be built from a single entity.
 *
 * `stateKeySuffix` is the same entity's `key` on the integration side, used only
 * as a fallback when the entity registry does not hand us a `translation_key`
 * (older Home Assistant cores omit it from the websocket payload).
 */
/**
 * Which measurement a row shows beside its state.
 *
 * `auto` is per kind — see `KindMetrics.auto`. The two explicit modes only
 * resolve on the kinds that have such a number; a disk asked for CPU shows
 * nothing rather than something else.
 */
export const SECONDARY_INFO_MODES = ['none', 'auto', 'cpu', 'memory'] as const;

export type SecondaryInfo = (typeof SECONDARY_INFO_MODES)[number];

/**
 * How to find one measurement on a device.
 *
 * The same two-step lookup the state entity uses: `translationKey` is the
 * integration's own name for the entity and survives renames, `keySuffix` is
 * the entity description key the `unique_id` ends with and covers the cores
 * that do not serialize a translation key into the registry payload.
 */
export interface MetricRef {
  readonly translationKey: string;
  readonly keySuffix: string;
  /** Key under `metrics.` in the language files, naming the figure where it stands on its own. */
  readonly label: string;
  /** Drawn beside the figure, unless the figure is a percentage and gets a ring instead. */
  readonly icon: string;
  /** A percentage where more is better, like a battery's charge: its ring turns red as it falls. */
  readonly inverse?: boolean;
  /**
   * A total this measurement counts against, shown as one figure — `3/5`.
   *
   * For the pair of numbers a Compose stack has, where neither says much on its
   * own: a bare "3" beside the state could be the containers that are up or the
   * services the stack declares, and printing both as separate values asks the
   * same question twice. A device missing the total shows the count alone
   * rather than nothing.
   */
  readonly over?: MetricRef;
}

/** The measurements a kind can show beside its state. */
interface KindMetrics {
  readonly cpu?: MetricRef;
  readonly memory?: MetricRef;
  /**
   * What `auto` shows for this kind, in order.
   *
   * Chosen per kind rather than uniformly, because the interesting number is
   * not the same everywhere: a guest is busy or idle, a disk is warm or cool,
   * a pool is full or empty. For the four guest kinds this is CPU and memory,
   * and a Compose stack leads with how many of its containers are up — a figure
   * no other kind has. The other three have one number each and no CPU or
   * memory at all.
   */
  readonly auto: readonly MetricRef[];
}

const guestMetrics = (prefix: string): KindMetrics => {
  const cpu = { translationKey: `${prefix}_cpu_usage`, keySuffix: 'cpu_usage', label: 'cpu', icon: 'mdi:speedometer' };
  const memory = {
    translationKey: `${prefix}_memory_usage`,
    keySuffix: 'memory_usage',
    label: 'memory',
    icon: 'mdi:memory',
  };

  return { cpu, memory, auto: [cpu, memory] };
};

interface KindInfo {
  /** Fallback icon, used when the state entity has no `entity_picture`. */
  readonly icon: string;
  readonly stateTranslationKey: string;
  readonly stateKeySuffix: string;
  /** Whether devices of this kind carry a start/stop switch. */
  readonly hasPower: boolean;
  /**
   * The `translation_key` of the kind's update-available binary sensor.
   *
   * Only the two Docker kinds have one: MOS tracks an image's local and remote
   * version, and neither LXC nor VM has an equivalent. Omitted for the kinds
   * that carry no update information at all.
   */
  readonly updateTranslationKey?: string;
  /** The measurements this kind can show beside its state. */
  readonly metrics: KindMetrics;
  /**
   * Binary sensors that say the device is busy with a long job of its own — a
   * scrub, a parity check, a preclear. Shown while on, because the NAS is
   * slower for as long as one runs.
   */
  readonly activities?: readonly MetricRef[];
}

/**
 * The `unique_id` suffix of every update-available entity, used as the fallback
 * when a core does not serialize `translation_key` into the registry payload.
 * The integration builds the id from the entity description's key, which is
 * `update_available` for the kinds that have one.
 */
const UPDATE_KEY_SUFFIX = '_update_available';

const composeMetrics = guestMetrics('compose');

export const KIND_INFO: Readonly<Record<MosDeviceKind, KindInfo>> = {
  docker_container: {
    icon: 'mdi:docker',
    stateTranslationKey: 'docker_state',
    stateKeySuffix: 'state',
    hasPower: true,
    updateTranslationKey: 'docker_update_available',
    metrics: guestMetrics('docker'),
  },
  compose_stack: {
    icon: 'mdi:layers',
    stateTranslationKey: 'compose_state',
    stateKeySuffix: 'state',
    hasPower: true,
    updateTranslationKey: 'compose_update_available',
    // The same CPU and memory as the other guests, plus the counter no other
    // kind has. It leads because it is the one figure a stack always reports:
    // CPU and memory are summed from the member containers and only exist while
    // the integration's separate Compose stats option is on, so a row falls
    // back to the counter alone rather than to nothing.
    metrics: {
      ...composeMetrics,
      auto: [
        {
          translationKey: 'compose_running_containers',
          keySuffix: 'running_containers',
          label: 'containers',
          icon: 'mdi:package-variant-closed',
          over: {
            translationKey: 'compose_container_count',
            keySuffix: 'container_count',
            label: 'containers',
            icon: 'mdi:package-variant-closed',
          },
        },
        ...composeMetrics.auto,
      ],
    },
  },
  lxc_container: {
    icon: 'mdi:linux',
    stateTranslationKey: 'lxc_state',
    stateKeySuffix: 'state',
    hasPower: true,
    metrics: guestMetrics('lxc'),
  },
  virtual_machine: {
    icon: 'mdi:server',
    stateTranslationKey: 'vm_state',
    stateKeySuffix: 'state',
    hasPower: true,
    metrics: guestMetrics('vm'),
  },
  disk: {
    icon: 'mdi:harddisk',
    stateTranslationKey: 'disk_power_status',
    stateKeySuffix: 'power_status',
    hasPower: false,
    metrics: {
      auto: [
        { translationKey: 'disk_usage', keySuffix: 'usage', label: 'used', icon: 'mdi:harddisk' },
        { translationKey: 'disk_temperature', keySuffix: 'temperature', label: 'temperature', icon: 'mdi:thermometer' },
      ],
    },
    activities: [
      {
        translationKey: 'disk_preclear_running',
        keySuffix: 'preclear_running',
        label: 'preclear',
        icon: 'mdi:autorenew',
      },
    ],
  },
  storage_pool: {
    icon: 'mdi:database',
    stateTranslationKey: 'pool_usage',
    stateKeySuffix: 'usage',
    hasPower: false,
    metrics: {
      auto: [
        {
          translationKey: 'pool_free_space',
          keySuffix: 'free_space',
          label: 'free',
          icon: 'mdi:database-outline',
          over: { translationKey: 'pool_total_space', keySuffix: 'total_space', label: 'total', icon: 'mdi:database' },
        },
      ],
    },
    activities: [
      { translationKey: 'pool_scrub_running', keySuffix: 'scrub_running', label: 'scrub', icon: 'mdi:autorenew' },
      { translationKey: 'pool_balance_running', keySuffix: 'balance_running', label: 'balance', icon: 'mdi:autorenew' },
      { translationKey: 'pool_parity_running', keySuffix: 'parity_running', label: 'parity', icon: 'mdi:autorenew' },
    ],
  },
  ups: {
    icon: 'mdi:power-plug',
    stateTranslationKey: 'ups_status',
    stateKeySuffix: 'ups_status',
    hasPower: false,
    metrics: {
      auto: [
        {
          translationKey: 'ups_battery_charge',
          keySuffix: 'ups_battery_charge',
          label: 'battery',
          icon: 'mdi:battery',
          inverse: true,
        },
        {
          translationKey: 'ups_battery_runtime',
          keySuffix: 'ups_battery_runtime',
          label: 'runtime',
          icon: 'mdi:timer-outline',
        },
        { translationKey: 'ups_load', keySuffix: 'ups_load', label: 'load', icon: 'mdi:gauge' },
      ],
    },
  },
};

export interface DeviceRegistryEntry {
  id: string;
  name: string | null;
  name_by_user: string | null;
  model: string | null;
  model_id: string | null;
  manufacturer: string | null;
  via_device_id: string | null;
  configuration_url: string | null;
  area_id: string | null;
  disabled_by: string | null;
  identifiers: Array<[string, string]>;
  config_entries: string[];
}

export interface EntityRegistryEntry {
  entity_id: string;
  device_id: string | null;
  platform: string;
  unique_id?: string;
  translation_key?: string | null;
  disabled_by: string | null;
  hidden_by: string | null;
  entity_category: string | null;
}

/**
 * Registry collections.
 *
 * `createCollection` caches per websocket connection, so several MOS cards on
 * one dashboard share a single fetch and a single event subscription. The
 * registry-updated events are what make the card follow container churn without
 * polling.
 */
export const subscribeDeviceRegistry = (
  conn: Connection,
  onChange: (devices: DeviceRegistryEntry[]) => void,
): UnsubscribeFunc =>
  createCollection<DeviceRegistryEntry[]>(
    '_mosDeviceRegistry',
    (connection) => connection.sendMessagePromise<DeviceRegistryEntry[]>({ type: 'config/device_registry/list' }),
    (connection, store) =>
      connection.subscribeEvents(
        () =>
          connection
            .sendMessagePromise<DeviceRegistryEntry[]>({ type: 'config/device_registry/list' })
            .then((devices) => store.setState(devices, true)),
        'device_registry_updated',
      ),
    conn,
    onChange,
  );

export const subscribeEntityRegistry = (
  conn: Connection,
  onChange: (entities: EntityRegistryEntry[]) => void,
): UnsubscribeFunc =>
  createCollection<EntityRegistryEntry[]>(
    '_mosEntityRegistry',
    (connection) => connection.sendMessagePromise<EntityRegistryEntry[]>({ type: 'config/entity_registry/list' }),
    (connection, store) =>
      connection.subscribeEvents(
        () =>
          connection
            .sendMessagePromise<EntityRegistryEntry[]>({ type: 'config/entity_registry/list' })
            .then((entities) => store.setState(entities, true)),
        'entity_registry_updated',
      ),
    conn,
    onChange,
  );

/**
 * The icons an integration declares in its `icons.json`, as the frontend serves
 * them: domain, then `translation_key`, then a default and optional per-state
 * overrides.
 */
export interface IntegrationIcons {
  [domain: string]: Record<string, { default?: string; state?: Record<string, string> }>;
}

/**
 * Fetch the integration's own entity icons.
 *
 * Since ha-mos moved its icons into `icons.json`, they no longer arrive as the
 * `icon` attribute on a state: Home Assistant resolves them in the frontend
 * from the entity's `translation_key`. A card that wants to show what the
 * integration intends therefore has to ask for them, which is what this does —
 * the same websocket command the frontend itself uses.
 *
 * One request per card, answered from Home Assistant's own cache, and the
 * result never changes for a given integration version.
 */
export const fetchIntegrationIcons = (conn: Connection, integration: string): Promise<IntegrationIcons> =>
  conn
    .sendMessagePromise<{ resources: Record<string, IntegrationIcons> }>({
      type: 'frontend/get_icons',
      category: 'entity',
      integration,
    })
    .then((result) => result.resources?.[integration] ?? {});

/**
 * The icon `icons.json` declares for an entity, if it declares one.
 *
 * A `translation_key` is what ties the entity to its entry, so an entity
 * without one — or a kind the integration gives no icon, which is the case for
 * the Docker, LXC and VM state sensors that carry a picture instead — resolves
 * to nothing and leaves the caller to fall back.
 */
export function declaredIcon(
  icons: IntegrationIcons | undefined,
  entity: EntityRegistryEntry | undefined,
  state: string | undefined,
): string | undefined {
  if (!icons || !entity?.translation_key) {
    return undefined;
  }

  const domain = entity.entity_id.split('.')[0];
  const declared = icons[domain]?.[entity.translation_key];

  if (!declared) {
    return undefined;
  }

  return (state !== undefined ? declared.state?.[state] : undefined) ?? declared.default;
}

/**
 * The MOS server devices: the `via_device_id` targets of the container devices.
 *
 * Derived rather than matched, precisely because the server device carries no
 * `model_id` of its own to match on. Anything that is the parent of a device
 * with a MOS kind is by definition a MOS server.
 */
export function findServerDevices(devices: DeviceRegistryEntry[]): DeviceRegistryEntry[] {
  const byId = new Map(devices.map((device) => [device.id, device]));
  const serverIds = new Set<string>();

  for (const device of devices) {
    if (isMosDeviceKind(device.model_id) && device.via_device_id) {
      serverIds.add(device.via_device_id);
    }
  }

  return [...serverIds]
    .map((id) => byId.get(id))
    .filter((device): device is DeviceRegistryEntry => device !== undefined);
}

/**
 * Every container device of one of the requested kinds, optionally scoped to a
 * single server.
 *
 * Disabled devices are left out: the user disabled them, and the integration
 * will not be producing states for them either.
 */
export function selectMosDevices(
  devices: DeviceRegistryEntry[],
  kinds: readonly MosDeviceKind[],
  serverId?: string,
): DeviceRegistryEntry[] {
  const wanted = new Set<string>(kinds);

  return devices.filter(
    (device) =>
      device.disabled_by === null &&
      isMosDeviceKind(device.model_id) &&
      wanted.has(device.model_id) &&
      (serverId === undefined || device.via_device_id === serverId),
  );
}

/**
 * Container devices that hang off none of the given servers.
 *
 * A container device is tied to its server by `via_device_id`. One whose link
 * is missing, or points at a device this registry does not have, belongs under
 * no server and would otherwise be selected by nothing at all — a row silently
 * absent is the worst way for a card to be wrong, because there is nothing left
 * to notice. Collected here so the caller can list them rather than lose them.
 *
 * `null` is not a member of the set either, so a device with no link at all
 * falls out of the same check as one with a dangling one. With no servers to
 * compare against every selected device is unassigned, which is exactly the
 * fallback a registry with no resolvable server needs.
 */
export function selectUnassignedMosDevices(
  devices: DeviceRegistryEntry[],
  kinds: readonly MosDeviceKind[],
  serverIds: readonly string[],
): DeviceRegistryEntry[] {
  const known: ReadonlySet<string | null> = new Set<string | null>(serverIds);

  return selectMosDevices(devices, kinds).filter((device) => !known.has(device.via_device_id));
}

/** Index the entity registry by device, dropping entities that cannot render. */
export function entitiesByDevice(entities: EntityRegistryEntry[]): Map<string, EntityRegistryEntry[]> {
  const index = new Map<string, EntityRegistryEntry[]>();

  for (const entity of entities) {
    if (!entity.device_id || entity.disabled_by !== null || entity.hidden_by !== null) {
      continue;
    }
    const existing = index.get(entity.device_id);
    if (existing) {
      existing.push(entity);
    } else {
      index.set(entity.device_id, [entity]);
    }
  }

  return index;
}

/**
 * Pick the entity whose state is the headline value for a device of this kind.
 *
 * `translation_key` first: it is the integration's own name for the entity and
 * survives renames and entity_id changes. The `unique_id` suffix is a fallback
 * for cores that do not serialize `translation_key` into the registry payload,
 * and the first plain sensor is the last resort so a row still renders if the
 * integration grows a kind this card has not been taught about.
 */
export function findStateEntity(
  entities: readonly EntityRegistryEntry[],
  kind: MosDeviceKind,
): EntityRegistryEntry | undefined {
  const info = KIND_INFO[kind];

  return (
    entities.find((entity) => entity.translation_key === info.stateTranslationKey) ??
    entities.find(
      (entity) => entity.entity_id.startsWith('sensor.') && entity.unique_id?.endsWith(`_${info.stateKeySuffix}`),
    ) ??
    entities.find((entity) => entity.entity_id.startsWith('sensor.'))
  );
}

/**
 * The start/stop switch for a guest, if it has one.
 *
 * Each of the four guest kinds contributes exactly one switch to its device —
 * a stack's starts and stops every service in it — so matching the domain is
 * enough and does not depend on the switch's name.
 */
export function findPowerEntity(
  entities: readonly EntityRegistryEntry[],
  kind: MosDeviceKind,
): EntityRegistryEntry | undefined {
  if (!KIND_INFO[kind].hasPower) {
    return undefined;
  }

  return entities.find((entity) => entity.entity_id.startsWith('switch.'));
}

/**
 * The entity reporting that an update is waiting for this device, if it has one.
 *
 * Matched the same way as the state entity — `translation_key` first, the
 * `unique_id` suffix as the fallback — but with no last-resort guess: an
 * unrecognised entity would light up an update badge on a device that has no
 * update, which is worse than showing none.
 */
export function findUpdateEntity(
  entities: readonly EntityRegistryEntry[],
  kind: MosDeviceKind,
): EntityRegistryEntry | undefined {
  const translationKey = KIND_INFO[kind].updateTranslationKey;

  if (!translationKey) {
    return undefined;
  }

  return (
    entities.find((entity) => entity.translation_key === translationKey) ??
    entities.find(
      (entity) => entity.entity_id.startsWith('binary_sensor.') && entity.unique_id?.endsWith(UPDATE_KEY_SUFFIX),
    )
  );
}

/**
 * Name patterns deciding which rows a card lists.
 *
 * Matched against the name the row is *displayed* under, which is the name the
 * user reads and would type. That is a deliberate exception to the rule that
 * this card never matches on names: device *selection* is anchored on
 * `model_id` and stays that way, and this filter narrows an already-selected
 * list to the user's own taste. A renamed device therefore changes what this
 * matches, which is correct — the user renamed the thing they are filtering on.
 */
export interface NameFilter {
  include?: string | readonly string[];
  exclude?: string | readonly string[];
}

const asPatterns = (value: string | readonly string[] | undefined): string[] => {
  if (value === undefined) {
    return [];
  }

  return (typeof value === 'string' ? [value] : value).map((pattern) => pattern.trim()).filter(Boolean);
};

/**
 * Whether a name matches a glob pattern, case-insensitively.
 *
 * `*` and `?` only — the two wildcards someone types without being told the
 * syntax. A pattern with neither is a substring match rather than an equality
 * one, because "show me my arr containers" is what people mean when they type
 * `arr`, and demanding `*arr*` for it is a syntax lesson nobody asked for.
 */
export function matchesPattern(name: string, pattern: string): boolean {
  const subject = name.toLowerCase();
  const glob = pattern.toLowerCase();

  if (!glob.includes('*') && !glob.includes('?')) {
    return subject.includes(glob);
  }

  const expression = glob
    .split('')
    .map((character) => {
      if (character === '*') {
        return '.*';
      }
      if (character === '?') {
        return '.';
      }

      return character.replace(/[.+^${}()|[\]\\]/g, '\\$&');
    })
    .join('');

  return new RegExp(`^${expression}$`).test(subject);
}

/**
 * Whether a row survives the configured name filter.
 *
 * An absent or empty `include` lets everything through, so a filter that only
 * excludes does not have to name everything it keeps. `exclude` is applied
 * after and wins, which is the order that lets "all the arr containers except
 * the test one" be written the obvious way.
 */
export function passesFilter(name: string, filter: NameFilter | undefined): boolean {
  if (!filter) {
    return true;
  }

  const include = asPatterns(filter.include);
  const exclude = asPatterns(filter.exclude);

  if (include.length && !include.some((pattern) => matchesPattern(name, pattern))) {
    return false;
  }

  return !exclude.some((pattern) => matchesPattern(name, pattern));
}

/**
 * The binary sensors on a device that could report a fault.
 *
 * Deliberately every one of them rather than a per-kind list: which of an
 * integration's binary sensors mean "something is wrong" is not this card's
 * judgement to make, and Home Assistant already has a word for it — the
 * `problem` device class, which the integration sets on exactly those. That
 * word lives on the state and not in the registry, though, so the registry can
 * only narrow the field to the candidates and the caller does the rest.
 *
 * The consequence is worth stating: a fault the integration adds later is
 * badged without this card being taught about it.
 */
export function findProblemCandidates(entities: readonly EntityRegistryEntry[]): EntityRegistryEntry[] {
  return entities.filter((entity) => entity.entity_id.startsWith('binary_sensor.'));
}

/**
 * The entity carrying one measurement on a device, if it has one.
 *
 * Same two-step lookup as the state entity, and the same deliberate absence of
 * a last-resort guess: a wrong entity here would print a number that means
 * something else entirely, which is worse than printing nothing.
 */
export function findMetricEntity(
  entities: readonly EntityRegistryEntry[],
  metric: MetricRef,
  domain = 'sensor',
): EntityRegistryEntry | undefined {
  return (
    entities.find((entity) => entity.translation_key === metric.translationKey) ??
    entities.find(
      (entity) => entity.entity_id.startsWith(`${domain}.`) && entity.unique_id?.endsWith(`_${metric.keySuffix}`),
    )
  );
}

/** The binary sensors behind a kind's long-running jobs, as far as the device has them. */
export function findActivities(entities: readonly EntityRegistryEntry[], kind: MosDeviceKind): RowMetric[] {
  return (KIND_INFO[kind].activities ?? []).flatMap((ref) => {
    const entity = findMetricEntity(entities, ref, 'binary_sensor');

    return entity ? [{ ref, entity }] : [];
  });
}

/**
 * One measurement as a row shows it: the entity carrying the number, and the
 * entity carrying the total it counts against where the kind names one.
 *
 * Resolved as a pair rather than as two entries in a flat list, because the two
 * are one figure — `3/5` — and a caller handed them side by side could only
 * put them back together by guessing which is which.
 */
export interface RowMetric<R extends MetricRef = MetricRef> {
  /** What was looked for, so a caller can present the figure by what it is. */
  readonly ref: R;
  readonly entity: EntityRegistryEntry;
  readonly over?: EntityRegistryEntry;
}

/**
 * The measurements one device can show, resolved against its own entities.
 *
 * A metric the device has no entity for is dropped; a missing *total* only
 * costs the row its denominator, since the count is still worth printing.
 */
export function resolveMetrics<R extends MetricRef>(
  entities: readonly EntityRegistryEntry[],
  metrics: readonly R[],
): RowMetric<R>[] {
  const resolved: RowMetric<R>[] = [];

  for (const metric of metrics) {
    const entity = findMetricEntity(entities, metric);

    if (!entity) {
      continue;
    }

    resolved.push({ ref: metric, entity, over: metric.over ? findMetricEntity(entities, metric.over) : undefined });
  }

  return resolved;
}

/**
 * The measurements a row shows for the requested mode.
 *
 * `none` is the default and resolves to nothing at all, which is what keeps the
 * card's out-of-the-box appearance unchanged.
 */
export function metricsForMode(kind: MosDeviceKind, mode: SecondaryInfo): readonly MetricRef[] {
  const metrics = KIND_INFO[kind].metrics;

  if (mode === 'auto') {
    return metrics.auto;
  }

  const chosen = mode === 'cpu' ? metrics.cpu : mode === 'memory' ? metrics.memory : undefined;

  return chosen ? [chosen] : [];
}

/** A server measurement, with what the heading needs to show it as a tile. */
export interface ServerMetricRef extends MetricRef {
  /** Whether the value is a percentage, drawn as a ring rather than a bare figure. */
  readonly gauge: boolean;
}

/**
 * What the MOS server itself reports about its load.
 *
 * Read off the server device, which carries no `model_id` and is therefore
 * never a row — these are for the heading above the rows. Anything the server
 * cannot measure reports unknown and is left out rather than printed.
 */
export const SERVER_METRICS: readonly ServerMetricRef[] = [
  { translationKey: 'cpu_load', keySuffix: 'cpu_load', icon: 'mdi:speedometer', label: 'cpu', gauge: true },
  { translationKey: 'memory_usage', keySuffix: 'memory_usage', icon: 'mdi:memory', label: 'memory', gauge: true },
  {
    translationKey: 'cpu_temperature',
    keySuffix: 'cpu_temperature',
    icon: 'mdi:thermometer',
    label: 'temperature',
    gauge: false,
  },
];

/** When the server last booted, shown as its uptime beside its name. */
export const SERVER_BOOT_TIME: MetricRef = {
  translationKey: 'boot_time',
  keySuffix: 'boot_time',
  label: 'uptime',
  icon: 'mdi:clock-outline',
};

/** A service the server runs, shown as a chip that is lit while it is on. */
export interface ServiceRef extends MetricRef {
  /** The service's own name, which is the same in every language. */
  readonly name: string;
}

export const SERVER_SERVICES: readonly ServiceRef[] = [
  { translationKey: 'ssh_enabled', keySuffix: 'ssh_enabled', label: 'service', icon: 'mdi:console', name: 'SSH' },
  {
    translationKey: 'samba_enabled',
    keySuffix: 'samba_enabled',
    label: 'service',
    icon: 'mdi:folder-network',
    name: 'Samba',
  },
  {
    translationKey: 'nfs_enabled',
    keySuffix: 'nfs_enabled',
    label: 'service',
    icon: 'mdi:folder-network-outline',
    name: 'NFS',
  },
  {
    translationKey: 'tailscale_online',
    keySuffix: 'tailscale_online',
    label: 'service',
    icon: 'mdi:vpn',
    name: 'Tailscale',
  },
  { translationKey: 'netbird_online', keySuffix: 'netbird_online', label: 'service', icon: 'mdi:vpn', name: 'NetBird' },
];

/** The services a server has, in the order they are shown. */
export function findServices(entities: readonly EntityRegistryEntry[]): RowMetric<ServiceRef>[] {
  return SERVER_SERVICES.flatMap((ref) => {
    const entity = findMetricEntity(entities, ref, 'binary_sensor');

    return entity ? [{ ref, entity }] : [];
  });
}

/**
 * The display name for a device row.
 *
 * The user's own name wins, then the registry name. The integration prefixes
 * container device names with the server and the kind ("Sirius Docker
 * pushbits") so they stay unique across servers; inside a card that is already
 * grouped by server and kind that prefix is noise, so it is trimmed off for
 * display only — never used for matching.
 */
export function deviceDisplayName(device: DeviceRegistryEntry, serverName?: string): string {
  const name = device.name_by_user || device.name || device.id;

  if (device.name_by_user) {
    return name;
  }

  let trimmed = name;

  if (serverName && trimmed.toLowerCase().startsWith(`${serverName.toLowerCase()} `)) {
    trimmed = trimmed.slice(serverName.length + 1);
  }

  for (const prefix of ['Docker ', 'Compose ', 'LXC ', 'VM ', 'Disk ', 'Pool ', 'UPS ']) {
    if (trimmed.startsWith(prefix)) {
      return trimmed.slice(prefix.length);
    }
  }

  return trimmed;
}

/** Whether a state string means "Home Assistant has no reading for this". */
export function isUnavailableState(state: string | undefined): boolean {
  return state === undefined || state === 'unavailable' || state === 'unknown';
}

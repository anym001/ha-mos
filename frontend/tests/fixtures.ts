/**
 * Registry entries shaped like the ones Home Assistant actually sends.
 *
 * The values are taken from a live instance running the `mos` integration
 * rather than invented: the device names carry the server-and-kind prefix the
 * integration writes, the `unique_id`s carry the config entry id followed by
 * the entity description key, and the server device has no `model_id` at all.
 * A fixture that gets those wrong would let a test pass on code that cannot
 * read the real thing.
 */
import type { DeviceRegistryEntry, EntityRegistryEntry } from '../src/devices';

const ENTRY = '01JQZ8N2V9K3XW4YB6C7D8E9F0';

export const device = (over: Partial<DeviceRegistryEntry> & { id: string }): DeviceRegistryEntry => ({
  name: null,
  name_by_user: null,
  model: null,
  model_id: null,
  manufacturer: 'MOS',
  via_device_id: null,
  configuration_url: null,
  area_id: null,
  disabled_by: null,
  identifiers: [],
  config_entries: [ENTRY],
  ...over,
});

export const entity = (over: Partial<EntityRegistryEntry> & { entity_id: string }): EntityRegistryEntry => ({
  device_id: null,
  platform: 'mos',
  disabled_by: null,
  hidden_by: null,
  entity_category: null,
  ...over,
});

/** The server device: the `via_device_id` target, carrying no `model_id`. */
export const SERVER = device({ id: 'srv1', name: 'Pluto', model: 'MOS NAS' });

export const SERVER_TWO = device({ id: 'srv2', name: 'Sirius', model: 'MOS NAS' });

export const DOCKER = device({
  id: 'dev-docker',
  name: 'Pluto Docker pushbits',
  model_id: 'docker_container',
  via_device_id: 'srv1',
});

export const COMPOSE = device({
  id: 'dev-compose',
  name: 'Pluto Compose media',
  model: 'Compose Stack',
  model_id: 'compose_stack',
  via_device_id: 'srv1',
});

export const LXC = device({
  id: 'dev-lxc',
  name: 'Pluto LXC testlxc',
  model_id: 'lxc_container',
  via_device_id: 'srv1',
});

export const DISK = device({
  id: 'dev-disk',
  name: 'Pluto Disk vda',
  name_by_user: 'Parity',
  model_id: 'disk',
  via_device_id: 'srv1',
});

export const POOL = device({
  id: 'dev-pool',
  name: 'Pluto Pool tank',
  model_id: 'storage_pool',
  via_device_id: 'srv1',
});

/** Docker entities as the integration creates them for one container. */
export const DOCKER_ENTITIES: EntityRegistryEntry[] = [
  entity({
    entity_id: 'sensor.pluto_docker_pushbits_state',
    device_id: 'dev-docker',
    translation_key: 'docker_state',
    unique_id: `${ENTRY}_docker_pushbits_state`,
  }),
  entity({
    entity_id: 'sensor.pluto_docker_pushbits_cpu_usage',
    device_id: 'dev-docker',
    translation_key: 'docker_cpu_usage',
    unique_id: `${ENTRY}_docker_pushbits_cpu_usage`,
  }),
  entity({
    entity_id: 'sensor.pluto_docker_pushbits_memory_usage',
    device_id: 'dev-docker',
    translation_key: 'docker_memory_usage',
    unique_id: `${ENTRY}_docker_pushbits_memory_usage`,
  }),
  entity({
    entity_id: 'switch.pluto_docker_pushbits_power',
    device_id: 'dev-docker',
    translation_key: 'docker_power',
    unique_id: `${ENTRY}_docker_pushbits_power`,
  }),
  entity({
    entity_id: 'binary_sensor.pluto_docker_pushbits_update_available',
    device_id: 'dev-docker',
    translation_key: 'docker_update_available',
    unique_id: `${ENTRY}_docker_pushbits_update_available`,
    entity_category: 'diagnostic',
  }),
  entity({
    entity_id: 'binary_sensor.pluto_docker_pushbits_health',
    device_id: 'dev-docker',
    translation_key: 'docker_healthy',
    unique_id: `${ENTRY}_docker_pushbits_healthy`,
    entity_category: 'diagnostic',
  }),
];

/**
 * Compose stack entities as the integration creates them for one stack.
 *
 * The counter pair is the difference that matters here: on top of the CPU and
 * memory every guest has, a stack carries how many of its containers are up
 * beside how many it has. Its stats sensors are included because the option
 * behind them is on for this stack; `COMPOSE_ENTITIES_NO_STATS` is the same
 * stack with it off.
 */
export const COMPOSE_ENTITIES: EntityRegistryEntry[] = [
  entity({
    entity_id: 'sensor.pluto_compose_media_state',
    device_id: 'dev-compose',
    translation_key: 'compose_state',
    unique_id: `${ENTRY}_compose_media_state`,
  }),
  entity({
    entity_id: 'sensor.pluto_compose_media_running_containers',
    device_id: 'dev-compose',
    translation_key: 'compose_running_containers',
    unique_id: `${ENTRY}_compose_media_running_containers`,
  }),
  entity({
    entity_id: 'sensor.pluto_compose_media_containers',
    device_id: 'dev-compose',
    translation_key: 'compose_container_count',
    unique_id: `${ENTRY}_compose_media_container_count`,
  }),
  entity({
    entity_id: 'sensor.pluto_compose_media_cpu_usage',
    device_id: 'dev-compose',
    translation_key: 'compose_cpu_usage',
    unique_id: `${ENTRY}_compose_media_cpu_usage`,
  }),
  entity({
    entity_id: 'sensor.pluto_compose_media_memory_usage',
    device_id: 'dev-compose',
    translation_key: 'compose_memory_usage',
    unique_id: `${ENTRY}_compose_media_memory_usage`,
  }),
  entity({
    entity_id: 'switch.pluto_compose_media_power',
    device_id: 'dev-compose',
    translation_key: 'compose_power',
    unique_id: `${ENTRY}_compose_media_power`,
  }),
  entity({
    entity_id: 'binary_sensor.pluto_compose_media_update_available',
    device_id: 'dev-compose',
    translation_key: 'compose_update_available',
    unique_id: `${ENTRY}_compose_media_update_available`,
    entity_category: 'diagnostic',
  }),
  entity({
    entity_id: 'binary_sensor.pluto_compose_media_health',
    device_id: 'dev-compose',
    translation_key: 'compose_healthy',
    unique_id: `${ENTRY}_compose_media_healthy`,
    entity_category: 'diagnostic',
  }),
  entity({
    entity_id: 'binary_sensor.pluto_compose_media_autostart',
    device_id: 'dev-compose',
    translation_key: 'compose_autostart',
    unique_id: `${ENTRY}_compose_media_autostart`,
  }),
];

/**
 * The same stack on an installation that leaves the Compose stats option off.
 *
 * The default state, and the one where `auto` has to fall back to the counter
 * pair rather than showing nothing.
 */
export const COMPOSE_ENTITIES_NO_STATS: EntityRegistryEntry[] = COMPOSE_ENTITIES.filter(
  (candidate) => !candidate.entity_id.endsWith('_cpu_usage') && !candidate.entity_id.endsWith('_memory_usage'),
);

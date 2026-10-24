import { LitElement, html, nothing, TemplateResult, css, CSSResultGroup, PropertyValues } from 'lit';
import { property, state } from 'lit/decorators.js';
import { HassEntity } from 'home-assistant-js-websocket';
import type { UnsubscribeFunc } from 'home-assistant-js-websocket';
import {
  HomeAssistant,
  hasAction,
  ActionConfig,
  ActionHandlerEvent,
  handleAction,
  LovelaceCardEditor,
} from 'custom-card-helpers';

import type { LovelaceGridOptions, MosCardConfig } from './types';
import {
  DeviceRegistryEntry,
  EntityRegistryEntry,
  IntegrationIcons,
  KIND_INFO,
  MOS_DEVICE_KINDS,
  MosDeviceKind,
  RowMetric,
  SERVER_BOOT_TIME,
  SERVER_METRICS,
  ServerMetricRef,
  ServiceRef,
  findActivities,
  findMetricEntity,
  findServices,
  MetricRef,
  declaredIcon,
  deviceDisplayName,
  entitiesByDevice,
  fetchIntegrationIcons,
  findPowerEntity,
  findProblemCandidates,
  findServerDevices,
  findStateEntity,
  findUpdateEntity,
  isUnavailableState,
  metricsForMode,
  passesFilter,
  resolveMetrics,
  selectMosDevices,
  selectUnassignedMosDevices,
  subscribeDeviceRegistry,
  subscribeEntityRegistry,
} from './devices';
import { normalizeConfig } from './config';
import {
  PendingTimers,
  capRows,
  compareRows,
  countGroup,
  fillPlaceholders,
  isLinkableUrl,
  moreInfoEntity,
  settledPending,
  showsMeasurements,
  toneFor,
} from './rows';
import type { GroupCounts, PlaceholderValues } from './rows';
import { HistoryLoader } from './history-loader';
import type { HistoryMap } from './history-loader';
import {
  formatState,
  formatUpsState,
  renderChip,
  renderFigure,
  renderServerTile,
  renderServices,
  renderUptime,
  summaryStyles,
} from './render';
import { actionHandler } from './action-handler-directive';
import { announceCard, defineWhenHostReady } from './register';
import type { CustomCardEntry } from './register';
import { localize, setLanguage } from './localize/localize';
// The overview card ships in the same bundle, so installing one installs both.
import './overview-card';

interface WindowWithCustomCards extends Window {
  customCards?: CustomCardEntry[];
}

const pickerWindow = window as unknown as WindowWithCustomCards;
pickerWindow.customCards = announceCard(pickerWindow.customCards, {
  type: 'mos-card',
  name: 'MOS NAS Card',
  description: 'Containers, Compose stacks, VMs, disks, pools and the UPS of a MOS NAS server',
});

/**
 * How long a power button stays in its waiting state before giving up on it.
 *
 * The switch normally settles well inside this: the integration flips its own
 * state optimistically as soon as the MOS call returns. The timeout is only
 * there so a request that never comes back leaves a usable button behind
 * rather than a permanently spinning one.
 */
const PENDING_TIMEOUT_MS = 20000;

/** One rendered line: a device plus the entities the row is built from. */
interface DeviceRow {
  device: DeviceRegistryEntry;
  kind: MosDeviceKind;
  name: string;
  stateEntity?: EntityRegistryEntry;
  powerEntity?: EntityRegistryEntry;
  updateEntity?: EntityRegistryEntry;
  /** The measurements to show beside the state, in the order they are shown. */
  metrics: RowMetric[];
  /** Binary sensors that could carry a fault; which do is read off the state. */
  problemCandidates: EntityRegistryEntry[];
  /** Binary sensors for the device's own long-running jobs; shown while one is on. */
  activities: RowMetric[];
}

/** Rows of one kind, under one server. */
interface RowGroup {
  kind: MosDeviceKind;
  rows: DeviceRow[];
  /** How many rows the cap is hiding; zero when nothing is hidden. */
  hidden: number;
  /** Identifies the group across renders, so an opened one stays open. */
  key: string;
  counts: GroupCounts;
}

/** Everything belonging to one MOS server. */
interface ServerSection {
  server?: DeviceRegistryEntry;
  groups: RowGroup[];
  /** What the server reports about itself, when the config asks for it. */
  serverMetrics: RowMetric<ServerMetricRef>[];
  bootTime?: EntityRegistryEntry;
  services: RowMetric<ServiceRef>[];
}

/** How a pool's state reads as a chip: it is the pool's usage in percent. */
const POOL_USAGE: MetricRef = {
  translationKey: 'pool_usage',
  keySuffix: 'usage',
  label: 'used',
  icon: 'mdi:database',
};

export class MosCard extends LitElement {
  public static async getConfigElement(): Promise<LovelaceCardEditor> {
    const { editorDefined } = await import('./editor');
    await editorDefined;
    return document.createElement('mos-card-editor');
  }

  public static getStubConfig(): Record<string, unknown> {
    return { kinds: [...MOS_DEVICE_KINDS] };
  }

  @property({ attribute: false }) public hass!: HomeAssistant;

  @state() private config!: MosCardConfig;

  /**
   * The registries, mirrored locally.
   *
   * These are the card's source of truth for *which* devices exist; `hass`
   * remains the source of truth for what state each one is in. Keeping them
   * apart is what makes the card follow container churn: the registry
   * subscriptions fire when the integration adds or removes a device, and
   * ordinary `hass` updates handle everything else.
   */
  @state() private devices?: DeviceRegistryEntry[];

  @state() private entities?: EntityRegistryEntry[];

  /**
   * The icons the integration declares for its entities.
   *
   * Fetched rather than read off the state, because `icons.json` icons are
   * resolved in the frontend and never reach a state attribute.
   */
  @state() private icons?: IntegrationIcons;

  /**
   * Power switches with a request in flight, each mapped to the state it had
   * when the button was pressed.
   *
   * Starting or stopping a guest is not instant — MOS has to do it and the
   * integration has to hear back — and without a mark the row looks like the
   * click did nothing, so people press again. The recorded state is what tells
   * the card the request landed: when the switch reports something else, the
   * wait is over. Replaced rather than mutated, so Lit sees the change.
   */
  @state() private pending: ReadonlyMap<string, string> = new Map();

  /**
   * Groups the reader has opened past `max_rows`.
   *
   * Kept per group rather than per card, so opening the containers does not
   * also unfold the disks. Replaced rather than mutated, so Lit sees it.
   */
  @state() private expanded: ReadonlySet<string> = new Set();

  /** The recent readings of the server measurements drawn as sparklines. */
  @state() private history: HistoryMap = new Map();

  private readonly historyLoader = new HistoryLoader((history) => {
    this.history = history;
  });

  private readonly pendingTimers = new PendingTimers(PENDING_TIMEOUT_MS);

  private unsubscribe: UnsubscribeFunc[] = [];

  private trackedCache?: {
    devices?: DeviceRegistryEntry[];
    entities?: EntityRegistryEntry[];
    config: MosCardConfig;
    ids: string[];
  };

  public setConfig(config: MosCardConfig): void {
    this.config = normalizeConfig(config);
  }

  public connectedCallback(): void {
    super.connectedCallback();
    this.subscribeRegistries();
    this.resumePendingTimers();
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribeRegistries();
    // The timeouts go — one firing against a detached element is exactly what
    // splitting them off was for — but the waits themselves stay. The request a
    // wait stands for is still in flight, and a card is detached and reattached
    // routinely while one is: a conditional card hiding it, a switch to another
    // view. Dropping the waits there left the button back with no sign that
    // anything was happening.
    this.pendingTimers.stopAll();
  }

  /**
   * Mirror the frontend's language, and drop any wait the incoming states have
   * answered.
   *
   * Both run before the render rather than after it: the language has to be set
   * before a single string is resolved, and the button that is about to be drawn
   * should already be the settled one rather than flickering through a frame of
   * spinner it no longer needs.
   */
  protected willUpdate(changedProps: PropertyValues): void {
    if (changedProps.has('hass')) {
      setLanguage(this.hass?.locale?.language);
      this.historyLoader.continue(this.hass);
    }

    if (!changedProps.has('hass') || !this.pending.size) {
      return;
    }

    for (const entityId of settledPending(this.pending, (id) => this.hass.states[id]?.state)) {
      this.clearPending(entityId);
    }
  }

  protected updated(changedProps: PropertyValues): void {
    // `hass` arrives after the element is connected on a fresh dashboard load,
    // so the subscription cannot be set up in connectedCallback alone.
    if (changedProps.has('hass') && !this.unsubscribe.length) {
      this.subscribeRegistries();
    }

    this.historyLoader.request(this.hass, this.historyEntityIds());
  }

  /**
   * Re-render only for state changes that can actually show up on this card.
   *
   * `hass` is replaced on every state change anywhere in Home Assistant, which
   * on a busy instance is many times a second. The card is interested in a
   * small, known set of entities — the ones `trackedEntityIds()` collects — so
   * everything else is filtered out here.
   */
  /** The server measurements a sparkline is drawn for, under the current config. */
  private historyEntityIds(): string[] {
    if (!this.config.show_server_summary || !this.config.show_history || !this.devices || !this.entities) {
      return [];
    }

    const entityIndex = entitiesByDevice(this.entities);

    return findServerDevices(this.devices).flatMap((server) =>
      resolveMetrics(entityIndex.get(server.id) ?? [], SERVER_METRICS)
        .filter((metric) => metric.ref.gauge)
        .map((metric) => metric.entity.entity_id),
    );
  }

  protected shouldUpdate(changedProps: PropertyValues): boolean {
    if (!this.config) {
      return false;
    }

    // The registry subscription is established in updated(), which only runs
    // after a render, so updates have to be let through unfiltered until it
    // stands. Narrowed to a connected element: a detached one will not
    // subscribe, and letting its updates through would re-render it on every
    // state change in the instance for as long as something holds a reference.
    if (!this.unsubscribe.length && this.isConnected) {
      return true;
    }

    if (
      changedProps.has('config') ||
      changedProps.has('devices') ||
      changedProps.has('entities') ||
      changedProps.has('icons') ||
      changedProps.has('pending') ||
      changedProps.has('expanded') ||
      changedProps.has('history')
    ) {
      return true;
    }

    if (!changedProps.has('hass')) {
      return false;
    }

    const oldHass = changedProps.get('hass') as HomeAssistant | undefined;

    if (!oldHass) {
      return true;
    }

    // A language, unit or format change re-renders every state the card shows
    // without any of those states changing, so the entity check below cannot
    // see it. `locale` carries the language and the number, date and time
    // formats; `localize` is replaced when the translations themselves reload.
    if (oldHass.locale !== this.hass.locale || oldHass.localize !== this.hass.localize) {
      return true;
    }

    return this.trackedEntityIds().some((entityId) => oldHass.states[entityId] !== this.hass.states[entityId]);
  }

  /**
   * The entity ids whose state this card displays.
   *
   * Derived from the registries and the config alone — deliberately *not* from
   * the rendered rows, because `hide_unavailable` drops rows based on state and
   * a hidden row's entity still has to be watched for it to ever come back.
   *
   * Memoized on the identity of its three inputs, all of which are replaced
   * wholesale rather than mutated, so a reference check is enough.
   */
  private trackedEntityIds(): string[] {
    const cache = this.trackedCache;

    if (cache && cache.devices === this.devices && cache.entities === this.entities && cache.config === this.config) {
      return cache.ids;
    }

    const ids: string[] = [];

    if (this.devices && this.entities) {
      const kinds = (this.config.kinds ?? [...MOS_DEVICE_KINDS]) as MosDeviceKind[];
      const entityIndex = entitiesByDevice(this.entities);

      for (const device of selectMosDevices(this.devices, kinds, this.config.server)) {
        const deviceEntities = entityIndex.get(device.id) ?? [];
        const kind = device.model_id as MosDeviceKind;
        const stateEntity = findStateEntity(deviceEntities, kind);
        const powerEntity = findPowerEntity(deviceEntities, kind);

        if (stateEntity) {
          ids.push(stateEntity.entity_id);
        }
        if (powerEntity) {
          ids.push(powerEntity.entity_id);
        }
        for (const metric of this.rowMetrics(deviceEntities, kind)) {
          ids.push(metric.entity.entity_id);

          if (metric.over) {
            ids.push(metric.over.entity_id);
          }
        }
        if (this.config.show_update) {
          const updateEntity = findUpdateEntity(deviceEntities, kind);

          if (updateEntity) {
            ids.push(updateEntity.entity_id);
          }
        }
        if (this.config.show_problem) {
          for (const candidate of findProblemCandidates(deviceEntities)) {
            ids.push(candidate.entity_id);
          }
        }
        for (const activity of findActivities(deviceEntities, kind)) {
          ids.push(activity.entity.entity_id);
        }
      }

      // The server's own entities, which no row is built from and which are
      // therefore not reached by the loop above.
      for (const server of findServerDevices(this.devices)) {
        const serverEntities = entityIndex.get(server.id) ?? [];

        if (this.config.show_server_summary) {
          for (const metric of resolveMetrics(serverEntities, SERVER_METRICS)) {
            ids.push(metric.entity.entity_id);
          }
          const bootTime = findMetricEntity(serverEntities, SERVER_BOOT_TIME);

          if (bootTime) {
            ids.push(bootTime.entity_id);
          }
        }
        if (this.config.show_services) {
          for (const service of findServices(serverEntities)) {
            ids.push(service.entity.entity_id);
          }
        }
      }
    }

    this.trackedCache = { devices: this.devices, entities: this.entities, config: this.config, ids };

    return ids;
  }

  /**
   * Mirror both registries, once, for as long as the card is on screen.
   *
   * The `isConnected` guard is what keeps that promise. `updated()` calls this
   * on a `hass` change, and a card element that has been detached can still be
   * handed a `hass` — at which point it would subscribe again with no
   * `disconnectedCallback` left to come and tear the subscription down. The
   * collection holds the callback, the callback holds this element, and the
   * card is re-rendered off screen for as long as something keeps a reference.
   */
  private subscribeRegistries(): void {
    if (this.unsubscribe.length || !this.isConnected || !this.hass?.connection) {
      return;
    }

    this.unsubscribe = [
      subscribeDeviceRegistry(this.hass.connection, (devices) => {
        this.devices = devices;
      }),
      subscribeEntityRegistry(this.hass.connection, (entities) => {
        this.entities = entities;
      }),
    ];

    // Best effort: without it the card falls back to its own per-kind icons,
    // which is a cosmetic loss and no reason to fail the whole card.
    fetchIntegrationIcons(this.hass.connection, 'mos')
      .then((icons) => {
        this.icons = icons;
      })
      .catch(() => undefined);
  }

  private unsubscribeRegistries(): void {
    for (const unsub of this.unsubscribe) {
      unsub();
    }
    this.unsubscribe = [];
  }

  /**
   * Card height in Lovelace's grid units, so masonry can lay the column out.
   *
   * One unit per row plus one for the card's own chrome, and a floor of 3 while
   * the registry is still loading so the card does not visibly jump once the
   * rows arrive.
   */
  public getCardSize(): number {
    const sections = this.buildSections();
    if (!sections) {
      return 3;
    }

    const rows = sections.reduce(
      (total, section) => total + section.groups.reduce((sum, group) => sum + group.rows.length, 0),
      0,
    );

    return Math.max(3, rows + 1);
  }

  /**
   * The card's footprint in the sections view.
   *
   * `getCardSize` above answers for masonry; the sections layout asks this
   * instead. Full width and content-driven height are what a card that answers
   * nothing already falls back to today, so declaring them changes no existing
   * dashboard — it states the card's shape rather than inheriting it from a
   * frontend default that is free to move.
   *
   * `min_columns` is the part that does something on its own: a row carries an
   * icon, a name, a state and up to two controls, and the frontend honours the
   * floor when a dashboard asks for less, so the card can no longer be squeezed
   * to a width where every name is ellipsis.
   */
  public getGridOptions(): LovelaceGridOptions {
    return { columns: 12, rows: 'auto', min_columns: 6 };
  }

  /**
   * Turn the two registries into the sections to render.
   *
   * Returns undefined while the registries are still in flight, which the
   * caller renders as a loading state rather than as "nothing found".
   */
  private buildSections(): ServerSection[] | undefined {
    if (!this.devices || !this.entities || !this.config) {
      return undefined;
    }

    const kinds = (this.config.kinds ?? [...MOS_DEVICE_KINDS]) as MosDeviceKind[];
    const entityIndex = entitiesByDevice(this.entities);

    const servers = this.config.server
      ? this.devices.filter((device) => device.id === this.config.server)
      : findServerDevices(this.devices);

    // Devices that hang off none of the servers above — a missing or dangling
    // `via_device_id`, or a registry with no resolvable server at all. Without
    // a section of their own they belong to no server id and are selected by
    // nothing, which drops the row and says nothing about having dropped it.
    // Not collected for a card scoped to one server: there the question is not
    // "which server" but "this one or not".
    const unassigned = this.config.server
      ? []
      : selectUnassignedMosDevices(
          this.devices,
          kinds,
          servers.map((server) => server.id),
        );

    // A configured server id that no longer resolves still deserves its
    // devices: fall back to filtering by via_device_id alone.
    const serverIds: Array<string | undefined> = this.config.server
      ? [this.config.server]
      : [...servers.map((server) => server.id), ...(unassigned.length ? [undefined] : [])];

    const sections: ServerSection[] = [];

    for (const serverId of serverIds) {
      const server = servers.find((candidate) => candidate.id === serverId);
      const serverName = server ? server.name_by_user || server.name || undefined : undefined;
      const devices = serverId === undefined ? unassigned : selectMosDevices(this.devices, kinds, serverId);
      const groups: RowGroup[] = [];

      for (const kind of kinds) {
        const rows = devices
          .filter((device) => device.model_id === kind)
          .map((device) => {
            const deviceEntities = entityIndex.get(device.id) ?? [];
            return {
              device,
              kind,
              name: deviceDisplayName(device, serverName),
              stateEntity: findStateEntity(deviceEntities, kind),
              powerEntity: findPowerEntity(deviceEntities, kind),
              updateEntity: findUpdateEntity(deviceEntities, kind),
              metrics: this.rowMetrics(deviceEntities, kind),
              problemCandidates: this.config.show_problem ? findProblemCandidates(deviceEntities) : [],
              activities: findActivities(deviceEntities, kind),
            };
          })
          .filter((row) => passesFilter(row.name, this.config.filter))
          .filter((row) => !this.config.hide_unavailable || !isUnavailableState(this.stateValue(row)))
          .sort(compareRows(this.config.sort, (row) => this.stateValue(row)));

        if (rows.length) {
          const key = `${serverId ?? ''}:${kind}`;

          const counts = countGroup(
            kind,
            rows.map((row) => ({
              state: this.stateValue(row),
              update: row.updateEntity ? this.hass?.states[row.updateEntity.entity_id]?.state : undefined,
            })),
          );

          groups.push({ kind, key, counts, ...capRows(rows, this.config.max_rows, this.expanded.has(key)) });
        }
      }

      if (groups.length) {
        const serverEntities = server ? (entityIndex.get(server.id) ?? []) : [];
        const summary = this.config.show_server_summary && server;

        sections.push({
          server,
          groups,
          serverMetrics: summary ? resolveMetrics(serverEntities, SERVER_METRICS) : [],
          bootTime: summary ? findMetricEntity(serverEntities, SERVER_BOOT_TIME) : undefined,
          services: this.config.show_services && server ? findServices(serverEntities) : [],
        });
      }
    }

    return sections;
  }

  private stateValue(row: DeviceRow): string | undefined {
    return row.stateEntity ? this.hass?.states[row.stateEntity.entity_id]?.state : undefined;
  }

  /** The measurements one row shows, in the order they are shown. */
  private rowMetrics(entities: readonly EntityRegistryEntry[], kind: MosDeviceKind): RowMetric[] {
    const mode = this.config.secondary_info ?? 'none';

    if (mode === 'none') {
      return [];
    }

    return resolveMetrics(entities, metricsForMode(kind, mode));
  }

  protected render(): TemplateResult {
    return html`
      <ha-card .header=${this.config.title}>
        <div class="card-content">${this.renderBody()}</div>
      </ha-card>
    `;
  }

  /**
   * The card body: a notice while the registries are still loading, a notice
   * when nothing matched, and the sections themselves otherwise.
   *
   * Written as early returns rather than the nested ternary this used to be.
   * Prettier changed how it indents nested ternaries between 3.8 and 3.9, so
   * that construct turned every Prettier bump into a lint failure on a line
   * whose behaviour never changed. Early returns format identically under both.
   */
  private renderBody(): TemplateResult | TemplateResult[] {
    const sections = this.buildSections();

    if (sections === undefined) {
      return this.renderNotice(localize('common.loading'));
    }

    if (sections.length === 0) {
      return this.renderNotice(localize('common.no_devices'));
    }

    return sections.map((section) => this.renderSection(section, sections.length > 1));
  }

  private renderNotice(message: string): TemplateResult {
    return html`<div class="notice">${message}</div>`;
  }

  private renderSection(section: ServerSection, showServerHeading: boolean): TemplateResult {
    const heading = section.server
      ? section.server.name_by_user || section.server.name || localize('common.server')
      : localize('common.server');
    const tiles = section.serverMetrics
      .map((metric) => renderServerTile(this.hass, metric, this.history.get(metric.entity.entity_id)))
      .filter((tile): tile is TemplateResult => tile !== undefined);
    const services = renderServices(this.hass, section.services);
    const uptime = renderUptime(this.hass, section.bootTime);

    // The heading is otherwise omitted for a single server, where it only
    // repeats the card's own title — but a summary has to hang off something,
    // so asking for one brings the name back with it.
    return html`
      ${
        showServerHeading || tiles.length || services !== nothing
          ? html`
              <div class="server-heading"><span>${heading}</span>${uptime}</div>
              ${tiles.length ? html`<div class="server-summary">${tiles}</div>` : nothing} ${services}
            `
          : nothing
      }
      ${section.groups.map((group) => this.renderGroup(group))}
    `;
  }

  private renderGroup(group: RowGroup): TemplateResult {
    return html`
      ${
        this.config.group_by_kind
          ? html`<div class="kind-heading">
              <span>${localize(`kinds.${group.kind}`)}</span>${this.renderCounts(group)}
            </div>`
          : nothing
      }
      <div class="group cols-${this.config.columns ?? 1}">${group.rows.map((row) => this.renderRow(row))}</div>
      ${this.renderMore(group)}
    `;
  }

  /**
   * How many of a group's guests are up, and how many wait on an update.
   *
   * Only for the kinds that run: a disk or a pool has no "up" worth counting.
   */
  private renderCounts(group: RowGroup): TemplateResult | typeof nothing {
    if (!KIND_INFO[group.kind].hasPower) {
      return nothing;
    }

    const { running, total, updates } = group.counts;

    return html`<span class="kind-counts">
      ${localize('counts.running', '{running}', String(running)).replace('{total}', String(total))}
      ${
        this.config.show_update && updates
          ? html`<span class="kind-updates"
              >· ${localize(updates === 1 ? 'counts.update' : 'counts.updates', '{count}', String(updates))}</span
            >`
          : nothing
      }
    </span>`;
  }

  /**
   * The line standing in for the rows `max_rows` folded away.
   *
   * A button rather than a note, because a count of what is hidden without a
   * way to see it is worse than not capping at all. Opening is one-way for the
   * life of the card: someone who asked to see the rest is not looking for a
   * way to hide them again.
   */
  private renderMore(group: RowGroup): TemplateResult | typeof nothing {
    if (!group.hidden) {
      return nothing;
    }

    return html`
      <button class="more" @click=${() => this.expandGroup(group.key)}>
        ${localize('common.show_more', '{count}', String(group.hidden))}
      </button>
    `;
  }

  private expandGroup(key: string): void {
    this.expanded = new Set(this.expanded).add(key);
  }

  private renderRow(row: DeviceRow): TemplateResult {
    const stateObj = row.stateEntity ? this.hass.states[row.stateEntity.entity_id] : undefined;
    const unavailable = isUnavailableState(stateObj?.state);

    return html`
      <div
        class="row ${unavailable ? 'unavailable' : ''} ${this.config.compact ? 'compact' : ''} tone-${toneFor(
          row.kind,
          stateObj?.state,
        )}"
      >
        <div
          class="row-body"
          @action=${(ev: ActionHandlerEvent) => this.handleAction(ev, row)}
          ${actionHandler({
            hasHold: hasAction(this.config.hold_action),
            hasDoubleClick: hasAction(this.config.double_tap_action),
          })}
          tabindex="0"
          role="button"
        >
          ${this.config.show_icon ? this.renderIcon(row, stateObj) : nothing}
          <div class="text">
            <span class="name" title=${row.name}>${row.name}</span>
            ${this.renderSecondary(row, stateObj)}
          </div>
        </div>
        ${this.config.show_link ? this.renderLink(row, stateObj) : nothing}
        ${this.config.show_power ? this.renderPower(row) : nothing}
      </div>
    `;
  }

  /** The icon and whatever is badged onto it. */
  private renderIcon(row: DeviceRow, stateObj?: HassEntity): TemplateResult {
    return html`
      <div class="icon-wrap">
        ${this.renderArtwork(row, stateObj)}${this.renderProblemBadge(row)}${this.renderUpdateBadge(row)}
      </div>
    `;
  }

  /**
   * The mark on a device that is reporting a fault.
   *
   * Which of a device's binary sensors count is the integration's call, not
   * this card's: it sets Home Assistant's `problem` device class on exactly
   * those, and everything with that class and an outright "on" is badged. The
   * same rule as the update badge applies to the state — unknown and
   * unavailable mean the integration cannot currently say, which is not a
   * fault.
   *
   * It sits at the top of the icon where the update badge sits at the bottom,
   * so a container that is both unhealthy and out of date shows both.
   */
  private renderProblemBadge(row: DeviceRow): TemplateResult | typeof nothing {
    if (!this.config.show_problem) {
      return nothing;
    }

    const problems = row.problemCandidates
      .map((entity) => this.hass.states[entity.entity_id])
      .filter((stateObj) => stateObj?.attributes.device_class === 'problem' && stateObj.state === 'on');

    if (!problems.length) {
      return nothing;
    }

    // The entity's own name says what broke — "SMART warning", "Overload" —
    // where a generic word would only repeat what the colour already says. It
    // arrives prefixed with the device name, which the row is already headed
    // with, so that half is dropped.
    const label =
      problems
        .map((stateObj) => this.problemName(row, stateObj))
        .filter(Boolean)
        .join(', ') || localize('common.problem');

    return html`
      <div class="problem-badge" role="img" aria-label=${label} title=${label}>
        <ha-icon icon="mdi:alert"></ha-icon>
      </div>
    `;
  }

  /** A problem entity's name with the device name it is prefixed with removed. */
  private problemName(row: DeviceRow, stateObj: HassEntity): string {
    const full = (stateObj.attributes.friendly_name as string | undefined) ?? '';
    const device = row.device.name_by_user || row.device.name || '';

    return device && full.startsWith(`${device} `) ? full.slice(device.length + 1) : full;
  }

  /**
   * The row icon, in the order Home Assistant itself resolves one.
   *
   * 1. `entity_picture` — the artwork MOS shows for a container, a stack, an
   *    LXC or a VM, which beats any glyph either side could pick.
   * 2. The `icon` state attribute, for an entity that still sets one directly.
   * 3. What the integration declares in its `icons.json`. Those are resolved in
   *    the frontend and never reach a state attribute, so they are fetched
   *    separately — without this step the card silently ignores the icons the
   *    integration went to the trouble of declaring.
   * 4. The card's own per-kind icon, for the kinds the integration names none
   *    for and for the moment before the fetch lands.
   */
  private renderArtwork(row: DeviceRow, stateObj?: HassEntity): TemplateResult {
    const picture = stateObj?.attributes.entity_picture;

    if (picture) {
      return html`<img class="icon picture" src=${picture} alt="" loading="lazy" />`;
    }

    const icon =
      stateObj?.attributes.icon ||
      declaredIcon(this.icons, row.stateEntity, stateObj?.state) ||
      KIND_INFO[row.kind].icon;

    return html`<ha-icon class="icon" .icon=${icon}></ha-icon>`;
  }

  /**
   * The mark on a device whose image has a newer version waiting.
   *
   * It sits on the icon rather than next to the link and the switch, because
   * the right end of a row is where the controls are and this is not one.
   * Only Docker containers and Compose stacks report updates — MOS tracks an
   * image's local and remote version, and no other kind has an equivalent — so
   * every other row finds no entity here and renders nothing.
   */
  private renderUpdateBadge(row: DeviceRow): TemplateResult | typeof nothing {
    if (!this.config.show_update || !row.updateEntity) {
      return nothing;
    }

    // Only an outright "on" earns the badge: unavailable and unknown mean the
    // integration cannot currently say, which is not the same as "up to date"
    // but is also no reason to tell someone to go and update something.
    if (this.hass.states[row.updateEntity.entity_id]?.state !== 'on') {
      return nothing;
    }

    const label = localize('common.update_available');

    return html`
      <div class="update-badge" role="img" aria-label=${label} title=${label}>
        <ha-icon icon="mdi:arrow-up"></ha-icon>
      </div>
    `;
  }

  /**
   * The line under the name: the state, the measurements, or both.
   *
   * They share one line rather than stacking, so a row keeps its height and the
   * card its density however many numbers are asked for. With nothing to say
   * the line is left out entirely instead of rendering empty.
   */
  private renderSecondary(row: DeviceRow, stateObj?: HassEntity): TemplateResult | typeof nothing {
    const parts: Array<string | TemplateResult> = [];

    // A pool's state is how full it is, which reads better as a ring than as a
    // word — but only where measurements were asked for, so a card left at its
    // defaults keeps the plain line it always had.
    const measured = (this.config.secondary_info ?? 'none') !== 'none';

    if (
      this.config.show_state &&
      measured &&
      row.kind === 'storage_pool' &&
      stateObj &&
      !isUnavailableState(stateObj.state)
    ) {
      parts.push(renderChip(POOL_USAGE, stateObj, renderFigure(this.hass, stateObj)));
    } else if (this.config.show_state) {
      parts.push(row.kind === 'ups' ? formatUpsState(this.hass, stateObj) : formatState(this.hass, stateObj));
    }

    const metrics = showsMeasurements(row.kind, stateObj?.state)
      ? row.metrics
          .map((metric) => this.renderMetric(metric))
          .filter((part): part is TemplateResult => part !== undefined)
      : [];

    parts.push(...metrics, ...this.renderActivities(row));

    if (!parts.length) {
      return nothing;
    }

    // Each part after the first carries its separator, so a line that wraps
    // breaks before a "·" rather than leaving one hanging at the end.
    return html`<span class="state ${metrics.length ? 'with-metrics' : ''}"
      >${parts.map((part, index) =>
        index ? html` <span class="part"><span class="separator">·</span> ${part}</span>` : part,
      )}</span
    >`;
  }

  /** The device's own long jobs that are running right now, each named. */
  private renderActivities(row: DeviceRow): TemplateResult[] {
    return row.activities
      .filter((activity) => this.hass?.states[activity.entity.entity_id]?.state === 'on')
      .map(
        (activity) =>
          html`<span class="chip activity"
            ><ha-icon class="chip-icon" .icon=${activity.ref.icon}></ha-icon>${localize(
              `metrics.${activity.ref.label}`,
            )}</span
          >`,
      );
  }

  /**
   * One measurement, as the count of a total where the kind names one.
   *
   * A measurement the server cannot currently report — a stopped container has
   * no CPU figure, a virtualised disk no temperature — is left out rather than
   * printed as "unknown", which would fill the line with non-answers on exactly
   * the rows that have least to say. A total that is itself unavailable leaves
   * the count on its own: "3" beside a Compose stack's state is less than "3/5",
   * but it is not nothing.
   */
  private renderMetric(metric: RowMetric): TemplateResult | undefined {
    const stateObj = this.hass?.states[metric.entity.entity_id];

    if (!stateObj || isUnavailableState(stateObj.state)) {
      return undefined;
    }

    const total = metric.over ? this.hass?.states[metric.over.entity_id] : undefined;

    const figure =
      total && !isUnavailableState(total.state)
        ? html`${renderFigure(this.hass, stateObj)}<span class="of">/</span>${renderFigure(this.hass, total)}`
        : renderFigure(this.hass, stateObj);

    return renderChip(metric.ref, stateObj, figure);
  }

  /**
   * A link out to the thing itself.
   *
   * `web_ui_url` on the Docker and Compose state sensors is the container's or
   * the stack's own web interface, and the integration omits the attribute
   * entirely for the ones that have none — so its presence is the test. The
   * device's configuration URL is the fallback, which is what the other kinds
   * have.
   */
  private renderLink(row: DeviceRow, stateObj?: HassEntity): TemplateResult | typeof nothing {
    const url = (stateObj?.attributes.web_ui_url as string | undefined) || row.device.configuration_url || undefined;

    if (!isLinkableUrl(url)) {
      return nothing;
    }

    return html`
      <a class="link" href=${url} target="_blank" rel="noreferrer noopener" title=${localize('common.open_link')}>
        <ha-icon icon="mdi:web"></ha-icon>
      </a>
    `;
  }

  private renderPower(row: DeviceRow): TemplateResult | typeof nothing {
    if (!row.powerEntity) {
      return nothing;
    }

    const switchObj = this.hass.states[row.powerEntity.entity_id];

    if (!switchObj) {
      return nothing;
    }

    const on = switchObj.state === 'on';
    const waiting = this.pending.has(row.powerEntity.entity_id);
    const disabled = isUnavailableState(switchObj.state) || waiting;
    const label = localize(waiting ? 'common.power_pending' : 'common.toggle_power');

    // A toggle reads as a setting that is either on or off; a guest is a thing
    // that is doing something right now. So the control is a button showing the
    // action it performs — start what is stopped, stop what is running — and,
    // while the server works on it, that the press was heard.
    return html`
      <button
        class="power-button ${waiting ? 'pending' : ''}"
        ?disabled=${disabled}
        title=${label}
        aria-label=${label}
        @click=${(ev: Event) => this.togglePower(ev, row)}
      >
        ${
          waiting
            ? html`<span class="spinner" role="progressbar"></span>`
            : html`<ha-icon icon=${on ? 'mdi:stop' : 'mdi:play'}></ha-icon>`
        }
      </button>
    `;
  }

  private togglePower(ev: Event, row: DeviceRow): void {
    ev.stopPropagation();

    if (!row.powerEntity) {
      return;
    }

    const entityId = row.powerEntity.entity_id;

    if (this.pending.has(entityId)) {
      return;
    }

    // Derived from the entity rather than from the widget, because the two
    // controls report differently: the switch has already flipped its own
    // `checked` by the time this fires, a button has no such state at all.
    const current = this.hass.states[entityId]?.state;
    const stopping = current === 'on';

    // `confirm` rather than a Home Assistant dialog: the dialog has to be
    // imported from the frontend to be opened, which a card loaded as a
    // resource cannot do. It is also what `custom-card-helpers` uses for the
    // `confirmation` option on an action, so the two read the same.
    if (stopping && this.config.confirm_stop && !confirm(localize('common.confirm_stop', '{name}', row.name))) {
      return;
    }

    this.markPending(entityId, current);

    this.hass
      .callService('switch', stopping ? 'turn_off' : 'turn_on', { entity_id: entityId })
      .catch(() => this.clearPending(entityId));
  }

  /** Start waiting on a switch, with a timeout so the wait always ends. */
  private markPending(entityId: string, state: string | undefined): void {
    this.pending = new Map(this.pending).set(entityId, state ?? '');
    this.pendingTimers.start(entityId, (id) => this.clearPending(id));
  }

  private clearPending(entityId: string): void {
    this.pendingTimers.stop(entityId);

    if (this.pending.has(entityId)) {
      const next = new Map(this.pending);
      next.delete(entityId);
      this.pending = next;
    }
  }

  /**
   * Re-arm the timeouts for waits that survived a detach.
   *
   * The clock starts over rather than resuming where it left off, which is the
   * safe direction: a wait always ends. It rarely runs out in practice, because
   * the first `hass` a reattached card is handed usually already answers the
   * request and `willUpdate` clears the wait before the timeout matters.
   */
  private resumePendingTimers(): void {
    for (const entityId of this.pending.keys()) {
      this.pendingTimers.start(entityId, (id) => this.clearPending(id));
    }
  }

  /** The action the config names for one of the three gestures. */
  private configuredAction(action: string): ActionConfig | undefined {
    if (action === 'hold') {
      return this.config?.hold_action;
    }

    if (action === 'double_tap') {
      return this.config?.double_tap_action;
    }

    return this.config?.tap_action;
  }

  /**
   * Route a row action.
   *
   * The configured actions are card-wide, but each row applies them to its own
   * state entity — so a single `tap_action: more-info` opens the dialog for
   * whichever container was tapped.
   *
   * `toggle` is the one action that cannot mean the state entity: that entity
   * is a sensor, and Home Assistant would go looking for `sensor.turn_off`.
   * What someone picking `toggle` means is the switch the row already offers as
   * its power button, so the action is pointed at that instead. A row without
   * one — a disk, a pool, the UPS — has nothing to toggle and does nothing,
   * rather than reporting an entity Home Assistant cannot act on.
   *
   * A `more-info` action may name an entity of its own instead — `[[power]]`
   * to open the row's switch rather than its sensor. `handleAction` only ever
   * opens the entity it is handed here, so that one is lifted out of the action
   * config on the way in; see `moreInfoEntity`.
   */
  private handleAction(ev: ActionHandlerEvent, row: DeviceRow): void {
    if (!this.hass || !this.config || !ev.detail?.action) {
      return;
    }

    const configured = this.configuredAction(ev.detail.action);
    const toggling = configured?.action === 'toggle';

    if (toggling && !row.powerEntity) {
      return;
    }

    const values = this.placeholderValues(row);
    const rowEntity = toggling ? row.powerEntity?.entity_id : row.stateEntity?.entity_id;

    handleAction(
      this,
      this.hass,
      {
        entity: moreInfoEntity(configured, values) ?? rowEntity,
        tap_action: fillPlaceholders(this.config.tap_action, values),
        hold_action: fillPlaceholders(this.config.hold_action, values),
        double_tap_action: fillPlaceholders(this.config.double_tap_action, values),
      },
      ev.detail.action,
    );
  }

  /**
   * What a `[[key]]` in an action config stands for on this row.
   *
   * `entity` and `power` are the same split `toggle` makes above: the first
   * only reports a state, and acting on a row means acting on the second.
   */
  private placeholderValues(row: DeviceRow): PlaceholderValues {
    return {
      entity: row.stateEntity?.entity_id,
      power: row.powerEntity?.entity_id,
      device_id: row.device.id,
      name: row.name,
      kind: row.kind,
    };
  }
  static get styles(): CSSResultGroup {
    return [
      summaryStyles,
      css`
        .card-content {
          padding: 4px 12px 12px;
          /* The column layout below asks about the card's own width, not the
           window's: the same card is wide in one dashboard column and narrow in
           three, and only a container query can tell the difference. */
          container-type: inline-size;
        }

        .notice {
          padding: 16px 0;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .server-heading {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin: 14px 4px 6px;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .separator {
          opacity: 0.6;
        }

        .part {
          white-space: nowrap;
        }

        /* The state word carries the row's tone; the measurements beside it
           stay quiet, so a running row is not a line of green numbers. Rings
           keep their own scale. */
        .state .chip {
          color: var(--secondary-text-color);
        }

        .state .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .of {
          margin: 0 1px;
          opacity: 0.6;
        }

        .kind-heading {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin: 14px 4px 6px;
          font-size: 0.75em;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--secondary-text-color);
        }

        /* Counts read as part of the heading, not as a label of their own: same
         size, no capitals, so "3/4 running" is not shouted. */
        .kind-counts {
          flex: none;
          text-transform: none;
          letter-spacing: normal;
          font-size: 1.1em;
          font-weight: 400;
        }

        .kind-updates {
          color: var(--warning-color, #ffa600);
        }

        .group {
          display: grid;
          grid-template-columns: 1fr;
          gap: 8px;
        }

        .group.cols-2 {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        /* A row needs roughly 220px before its name turns to ellipsis, so a card
         too narrow for two of them gets one rather than two unreadable ones. */
        @container (max-width: 440px) {
          .group.cols-2 {
            grid-template-columns: 1fr;
          }
        }

        /* Opens the rows the cap folded away. Sized and coloured like the kind
         headings rather than like a row, so it reads as part of the list's
         furniture and not as another device. */
        .more {
          justify-self: start;
          margin: 8px 4px 0;
          padding: 4px 8px;
          border: none;
          border-radius: 8px;
          background: none;
          cursor: pointer;
          font: inherit;
          font-size: 0.8em;
          font-weight: 500;
          color: var(--secondary-text-color);
        }

        .more:hover {
          color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }

        .more:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 1px;
        }

        /* Every row carries a tone class derived from its state; these map it onto
         the theme's own colours, so a custom theme recolours the card without
         the card knowing anything about it. */
        .row {
          --tone-color: var(--secondary-text-color);
          /* Lifted off the card by mixing the text colour into the card's own
           background: a fixed grey would sit invisibly on the card in one theme
           or the other, and this stays a step darker in light and a step lighter
           in dark without needing to know which is in use. Named so the update
           badge can cut its ring out of the same colour. */
          --row-background: color-mix(
            in srgb,
            var(--primary-text-color) 7%,
            var(--ha-card-background, var(--card-background-color))
          );
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 12px;
          min-height: 56px;
          border-radius: 14px;
          box-sizing: border-box;
          background: var(--row-background);
        }

        /* Everything shrinks together, so the row keeps its proportions and does
         not just look like a squashed version of itself. */
        .row.compact {
          gap: 8px;
          padding: 4px 8px;
          min-height: 40px;
          border-radius: 10px;
        }

        .row.compact .icon {
          width: 32px;
          height: 32px;
          padding: 5px;
          border-radius: 9px;
          --mdc-icon-size: 20px;
        }

        .row.compact .link,
        .row.compact .power-button {
          width: 28px;
          height: 28px;
          --mdc-icon-size: 16px;
        }

        .row.compact .update-badge,
        .row.compact .problem-badge {
          width: 14px;
          height: 14px;
          border-width: 1.5px;
          --mdc-icon-size: 8px;
        }

        .row.compact .spinner {
          width: 13px;
          height: 13px;
        }

        .row.tone-active {
          --tone-color: var(--success-color, var(--state-active-color, #43a047));
        }

        .row.tone-idle {
          --tone-color: var(--warning-color, #ffa726);
        }

        .row.tone-inactive {
          --tone-color: var(--state-inactive-color, var(--secondary-text-color));
        }

        .row.tone-unknown {
          --tone-color: var(--disabled-color, var(--secondary-text-color));
        }

        .row.tone-neutral {
          --tone-color: var(--state-icon-color, var(--secondary-text-color));
        }

        /* The secondary line only takes the tone colour where the tone means
         something; on a neutral row it is ordinary secondary text. */
        .row.tone-neutral .state,
        .row.tone-inactive .state,
        .row.tone-unknown .state {
          color: var(--secondary-text-color);
        }

        .row.unavailable {
          opacity: 0.6;
        }

        .row-body {
          display: flex;
          align-items: center;
          gap: 12px;
          flex: 1;
          min-width: 0;
          cursor: pointer;
          border-radius: 10px;
          outline: none;
        }

        .row-body:focus-visible {
          box-shadow: 0 0 0 2px var(--primary-color);
        }

        /* The icon well.
         A rounded square rather than a circle, because most of what lands here
         is a square app logo from the MOS template and a circle clips its
         corners. The tone is carried by a ring around the well instead of a
         wash behind the artwork, which would drain the colour out of it. */
        .icon {
          flex: 0 0 auto;
          width: 44px;
          height: 44px;
          padding: 8px;
          box-sizing: border-box;
          border-radius: 12px;
          color: var(--tone-color);
          background: color-mix(in srgb, var(--tone-color) 16%, transparent);
          --mdc-icon-size: 28px;
        }

        /* The ring is the state signal, so it is only drawn where the state is
         one — otherwise it reads as a stray border around every icon. */
        .row.tone-active .icon,
        .row.tone-idle .icon {
          box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--tone-color) 35%, transparent);
        }

        /* Holds the icon and the badge together. The icon keeps its own box, so
         nothing about its size or spacing changes when no badge is drawn. */
        .icon-wrap {
          position: relative;
          flex: 0 0 auto;
          display: inline-flex;
        }

        .update-badge,
        .problem-badge {
          position: absolute;
          right: -3px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18px;
          height: 18px;
          box-sizing: border-box;
          border-radius: 50%;
          /* The ring is the row's own background, which lifts the badge off the
           icon instead of letting it merge into the corner of a dark logo. */
          border: 2px solid var(--row-background);
          color: var(--text-primary-color, #fff);
          --mdc-icon-size: 10px;
        }

        .update-badge {
          bottom: -3px;
          background: var(--warning-color, #ffa726);
        }

        /* Opposite corner from the update badge, so a container that is both
         unhealthy and out of date shows both without them overlapping. Error
         rather than warning: this one is not a suggestion. */
        .problem-badge {
          top: -3px;
          background: var(--error-color, #db4437);
        }

        /* Artwork gets a neutral well and more room: it brings its own colours,
         and a tinted backdrop behind a logo reads as a stain. */
        .icon.picture {
          padding: 5px;
          object-fit: contain;
          background: color-mix(in srgb, var(--primary-text-color) 6%, transparent);
        }

        .text {
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex: 1;
          min-width: 0;
          gap: 1px;
        }

        .name {
          width: 100%;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
          line-height: 1.3;
          color: var(--primary-text-color);
        }

        .state {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 0.85em;
          line-height: 1.3;
          color: var(--tone-color);
        }

        /* A state on its own is a word that can be cut without losing much; a
         measurement cut in half is the one thing the reader asked for and did
         not get. So a line carrying numbers wraps instead, to at most two lines
         — which only happens on a card too narrow to hold them side by side. */
        .state.with-metrics {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          white-space: normal;
        }

        /* Controls sit in matching round wells so the row ends in a consistent
         shape whether a device has a link, a switch, both or neither. */
        .link,
        .power-button {
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 34px;
          height: 34px;
          padding: 0;
          border: none;
          border-radius: 50%;
          --mdc-icon-size: 20px;
        }

        .link {
          color: var(--secondary-text-color);
          background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
        }

        .link:hover {
          color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 18%, transparent);
        }

        .power-button {
          cursor: pointer;
          color: var(--tone-color);
          background: color-mix(in srgb, var(--tone-color) 16%, transparent);
          transition: background 0.15s ease-in-out;
        }

        .power-button:hover {
          background: color-mix(in srgb, var(--tone-color) 30%, transparent);
        }

        .power-button:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 1px;
        }

        .power-button:disabled {
          cursor: default;
          opacity: 0.5;
        }

        /* A waiting button is disabled so it cannot be pressed twice, but it is
         not dimmed like an unavailable one — it is the row's liveliest thing
         at that moment, and fading it says the opposite. */
        .power-button.pending {
          opacity: 1;
        }

        .spinner {
          width: 16px;
          height: 16px;
          box-sizing: border-box;
          border-radius: 50%;
          border: 2px solid color-mix(in srgb, var(--tone-color) 25%, transparent);
          border-top-color: var(--tone-color);
          animation: mos-spin 0.8s linear infinite;
        }

        @keyframes mos-spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* Slowed rather than stopped: a spinner that does not turn says nothing
         at all, which is the one thing this element exists to avoid. */
        @media (prefers-reduced-motion: reduce) {
          .spinner {
            animation-duration: 2.4s;
          }
        }
      `,
    ];
  }
}

void defineWhenHostReady(() => customElements, 'mos-card', MosCard);

import { LitElement, html, nothing, css } from 'lit';
import type { CSSResultGroup, PropertyValues, TemplateResult } from 'lit';
import { property, state } from 'lit/decorators.js';
import type { UnsubscribeFunc } from 'home-assistant-js-websocket';
import { handleAction } from 'custom-card-helpers';
import type { HomeAssistant, LovelaceCardEditor } from 'custom-card-helpers';

import type { LovelaceGridOptions, MosOverviewCardConfig } from './types';
import {
  KIND_INFO,
  SERVER_BOOT_TIME,
  SERVER_METRICS,
  deviceDisplayName,
  entitiesByDevice,
  findMetricEntity,
  findServerDevices,
  findServices,
  resolveMetrics,
  subscribeDeviceRegistry,
  subscribeEntityRegistry,
} from './devices';
import type {
  DeviceRegistryEntry,
  EntityRegistryEntry,
  MetricRef,
  RowMetric,
  ServerMetricRef,
  ServiceRef,
} from './devices';
import { normalizeOverviewConfig } from './config';
import { activeProblems, buildOverview } from './overview';
import type { DiskSummary, KindSummary, PoolSummary, ServerOverview, StateLookup, UpsSummary } from './overview';
import { HistoryLoader } from './history-loader';
import type { HistoryMap } from './history-loader';
import { gaugePercent, severityFor } from './gauge';
import {
  formatUpsState,
  readableState,
  renderChip,
  renderFigure,
  renderGauge,
  renderServerTile,
  renderServices,
  renderUptime,
  summaryStyles,
} from './render';
import { announceCard, defineWhenHostReady } from './register';
import type { CustomCardEntry } from './register';
import { localize, setLanguage } from './localize/localize';

const pickerWindow = window as unknown as Window & { customCards?: CustomCardEntry[] };
pickerWindow.customCards = announceCard(pickerWindow.customCards, {
  type: 'mos-overview-card',
  name: 'MOS NAS Overview',
  description: 'A MOS NAS server at a glance: load, guests, storage, UPS and services',
});

/** How a kind's memory reads as a chip. */
const MEMORY: MetricRef = { translationKey: 'memory', keySuffix: 'memory', label: 'memory', icon: 'mdi:memory' };

/** Everything one server section is drawn from, resolved against the registries. */
interface ServerSection {
  server: DeviceRegistryEntry;
  name: string;
  metrics: RowMetric<ServerMetricRef>[];
  bootTime?: EntityRegistryEntry;
  services: RowMetric<ServiceRef>[];
}

/**
 * One MOS server condensed: its load, what runs, what is stored and how the
 * power is, with no row per device. The list card is where the devices are.
 */
export class MosOverviewCard extends LitElement {
  public static async getConfigElement(): Promise<LovelaceCardEditor> {
    const { overviewEditorDefined } = await import('./overview-editor');
    await overviewEditorDefined;
    return document.createElement('mos-overview-card-editor');
  }

  public static getStubConfig(): Record<string, unknown> {
    return {};
  }

  @property({ attribute: false }) public hass!: HomeAssistant;

  @state() private config!: MosOverviewCardConfig;

  @state() private devices?: DeviceRegistryEntry[];

  @state() private entities?: EntityRegistryEntry[];

  @state() private history: HistoryMap = new Map();

  private readonly historyLoader = new HistoryLoader((history) => {
    this.history = history;
  });

  private unsubscribe: UnsubscribeFunc[] = [];

  private trackedCache?: {
    devices?: DeviceRegistryEntry[];
    entities?: EntityRegistryEntry[];
    config: MosOverviewCardConfig;
    ids: string[];
  };

  public setConfig(config: MosOverviewCardConfig): void {
    this.config = normalizeOverviewConfig(config);
  }

  public connectedCallback(): void {
    super.connectedCallback();
    this.subscribeRegistries();
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    for (const unsub of this.unsubscribe) {
      unsub();
    }
    this.unsubscribe = [];
  }

  public getCardSize(): number {
    return 6;
  }

  public getGridOptions(): LovelaceGridOptions {
    return { columns: 12, rows: 'auto', min_columns: 6 };
  }

  protected willUpdate(changedProps: PropertyValues): void {
    if (changedProps.has('hass')) {
      setLanguage(this.hass?.locale?.language);
      this.historyLoader.continue(this.hass);
    }
  }

  protected updated(changedProps: PropertyValues): void {
    if (changedProps.has('hass') && !this.unsubscribe.length) {
      this.subscribeRegistries();
    }

    if (this.config.show_history) {
      this.historyLoader.request(
        this.hass,
        this.sections().flatMap((section) =>
          section.metrics.filter((metric) => metric.ref.gauge).map((metric) => metric.entity.entity_id),
        ),
      );
    }
  }

  /** Re-render only when an entity the card shows changed; same reasoning as the list card. */
  protected shouldUpdate(changedProps: PropertyValues): boolean {
    if (!this.config) {
      return false;
    }

    if (!this.unsubscribe.length && this.isConnected) {
      return true;
    }

    if (
      changedProps.has('config') ||
      changedProps.has('devices') ||
      changedProps.has('entities') ||
      changedProps.has('history')
    ) {
      return true;
    }

    const oldHass = changedProps.get('hass') as HomeAssistant | undefined;

    if (!changedProps.has('hass') || !oldHass) {
      return changedProps.has('hass');
    }

    if (oldHass.locale !== this.hass.locale || oldHass.localize !== this.hass.localize) {
      return true;
    }

    return this.trackedEntityIds().some((entityId) => oldHass.states[entityId] !== this.hass.states[entityId]);
  }

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
  }

  /** The servers to draw, in registry order, or the one the config names. */
  private sections(): ServerSection[] {
    if (!this.devices || !this.entities) {
      return [];
    }

    const index = entitiesByDevice(this.entities);

    return findServerDevices(this.devices)
      .filter((server) => !this.config.server || server.id === this.config.server)
      .map((server) => {
        const entities = index.get(server.id) ?? [];

        return {
          server,
          name: deviceDisplayName(server),
          metrics: resolveMetrics(entities, SERVER_METRICS),
          bootTime: findMetricEntity(entities, SERVER_BOOT_TIME),
          services: this.config.show_services ? findServices(entities) : [],
        };
      });
  }

  private readonly states: StateLookup = (entityId) => this.hass?.states[entityId];

  /** Every entity the card reads, memoized on the registries and the config. */
  private trackedEntityIds(): string[] {
    const cache = this.trackedCache;

    if (cache && cache.devices === this.devices && cache.entities === this.entities && cache.config === this.config) {
      return cache.ids;
    }

    const ids: string[] = [];

    if (this.devices && this.entities) {
      for (const section of this.sections()) {
        const overview = buildOverview(this.devices, this.entities, section.server, this.states);

        ids.push(
          ...section.metrics.map((metric) => metric.entity.entity_id),
          ...section.services.map((service) => service.entity.entity_id),
          ...(section.bootTime ? [section.bootTime.entity_id] : []),
          ...overview.kinds.flatMap((kind) => kind.entityIds),
          ...(overview.disks?.entityIds ?? []),
          ...overview.pools.flatMap((pool) => pool.entityIds),
          ...overview.ups.flatMap((ups) => ups.entityIds),
        );
      }
    }

    this.trackedCache = { devices: this.devices, entities: this.entities, config: this.config, ids };

    return ids;
  }

  protected render(): TemplateResult {
    return html`
      <ha-card .header=${this.config.title}>
        <div class="card-content">${this.renderBody()}</div>
      </ha-card>
    `;
  }

  private renderBody(): TemplateResult | TemplateResult[] {
    if (!this.devices || !this.entities) {
      return html`<div class="notice">${localize('common.loading')}</div>`;
    }

    const sections = this.sections();

    if (!sections.length) {
      return html`<div class="notice">${localize('common.no_devices')}</div>`;
    }

    return sections.map((section) => this.renderServer(section));
  }

  private renderServer(section: ServerSection): TemplateResult {
    const overview = buildOverview(this.devices ?? [], this.entities ?? [], section.server, this.states);
    const tiles = section.metrics
      .map((metric) =>
        renderServerTile(
          this.hass,
          metric,
          this.config.show_history ? this.history.get(metric.entity.entity_id) : undefined,
        ),
      )
      .filter((tile): tile is TemplateResult => tile !== undefined);

    return html`
      <section class="server">
        <div class="server-heading">
          <span class="server-name"><ha-icon icon="mdi:nas"></ha-icon>${section.name}</span>
          ${renderUptime(this.hass, section.bootTime)}
        </div>
        ${tiles.length ? html`<div class="server-summary">${tiles}</div>` : nothing}
        ${this.config.show_guests ? this.renderGuests(overview) : nothing}
        ${this.config.show_storage ? this.renderStorage(overview, section.name) : nothing}
        ${this.config.show_ups ? this.renderUps(overview.ups, section.name) : nothing}
        ${renderServices(this.hass, section.services)}
      </section>
    `;
  }

  private renderGuests(overview: ServerOverview): TemplateResult | typeof nothing {
    if (!overview.kinds.length) {
      return nothing;
    }

    return html`
      <div class="heading">${localize('overview.guests')}</div>
      <div class="kinds">${overview.kinds.map((kind) => this.renderKind(kind))}</div>
    `;
  }

  /**
   * One guest kind: how many run, how many wait on an update, and what they
   * use between them. The icon is lit while any of them runs.
   */
  private renderKind(summary: KindSummary): TemplateResult {
    const { running, total, updates } = summary.counts;
    const memory = readableState(this.hass, summary.memory);
    const path = this.config.navigation_path?.replace(/\[\[kind]]/g, summary.kind);
    const cpu =
      summary.cpu === undefined
        ? nothing
        : html`<span class="chip" title=${localize('metrics.cpu')}
            >${renderGauge(gaugePercent(String(summary.cpu)) ?? 0, 'mini-gauge')}<span class="figure"
              >${this.formatNumber(summary.cpu)}<span class="unit">%</span></span
            ></span
          >`;

    return html`
      <div
        class="kind ${running ? 'running' : ''} ${path ? 'clickable' : ''}"
        role=${path ? 'link' : nothing}
        tabindex=${path ? '0' : nothing}
        @click=${() => this.navigate(path)}
        @keydown=${(ev: KeyboardEvent) => ev.key === 'Enter' && this.navigate(path)}
      >
        <div class="kind-icon"><ha-icon .icon=${KIND_INFO[summary.kind].icon}></ha-icon></div>
        <div class="kind-text">
          <span class="kind-name">${localize(`kinds.${summary.kind}`)}</span>
          <span class="kind-line">
            <span class="figure">${running}<span class="of">/</span>${total}</span>
            ${localize('overview.running')}
            ${
              updates
                ? html`<span class="updates"
                    >· ${localize(updates === 1 ? 'counts.update' : 'counts.updates', '{count}', String(updates))}</span
                  >`
                : nothing
            }
          </span>
          ${
            // Nothing running means nothing measured: what a stopped guest
            // reports is its last reading, the same rule the list card follows.
            running
              ? html`<span class="kind-line metrics">
                  ${cpu} ${memory ? renderChip(MEMORY, memory, renderFigure(this.hass, memory)) : nothing}
                </span>`
              : nothing
          }
        </div>
      </div>
    `;
  }

  private renderStorage(overview: ServerOverview, serverName: string): TemplateResult | typeof nothing {
    if (!overview.pools.length && !overview.disks) {
      return nothing;
    }

    return html`
      <div class="heading">${localize('overview.storage')}</div>
      ${overview.pools.map((pool) => this.renderPool(pool, serverName))}
      ${overview.disks ? this.renderDisks(overview.disks) : nothing}
    `;
  }

  /** A pool as a bar of how full it is, with what is left and any job it is running. */
  private renderPool(pool: PoolSummary, serverName: string): TemplateResult {
    const usage = readableState(this.hass, pool.usage);
    const percent = usage ? gaugePercent(usage.state) : undefined;
    const free = pool.free ? readableState(this.hass, pool.free.entity) : undefined;
    const total = pool.free?.over ? readableState(this.hass, pool.free.over) : undefined;
    const problems = activeProblems(this.states, pool.problems);
    const running = pool.activities.filter((activity) => this.hass.states[activity.entity.entity_id]?.state === 'on');

    return html`
      <div class="pool" @click=${() => this.moreInfo(pool.usage)}>
        <div class="pool-head">
          <span class="pool-name">
            ${problems ? html`<ha-icon class="problem" icon="mdi:alert"></ha-icon>` : nothing}
            ${deviceDisplayName(pool.device, serverName)}
          </span>
          <span class="pool-figures">
            ${usage ? renderFigure(this.hass, usage) : nothing}
            ${
              free
                ? html`<span class="pool-free" title=${localize('overview.free_of_total')}
                    >${renderFigure(this.hass, free)}
                    ${localize('overview.free')}${
                      total ? html`<span class="of">/</span>${renderFigure(this.hass, total)}` : nothing
                    }</span
                  >`
                : nothing
            }
          </span>
        </div>
        <div class="bar severity-${severityFor(percent ?? 0)}">
          <div class="bar-fill" style="width: ${percent ?? 0}%"></div>
        </div>
        ${
          running.length
            ? html`<div class="pool-jobs">
                ${running.map(
                  (activity) =>
                    html`<span class="chip activity"
                      ><ha-icon class="chip-icon" .icon=${activity.ref.icon}></ha-icon>${localize(
                        `metrics.${activity.ref.label}`,
                      )}</span
                    >`,
                )}
              </div>`
            : nothing
        }
      </div>
    `;
  }

  /** The disks as one line: how many, how many sleep, the warmest, and any with a fault. */
  private renderDisks(disks: DiskSummary): TemplateResult {
    const hottest = readableState(this.hass, disks.hottest);

    return html`
      <div class="disks">
        <ha-icon icon="mdi:harddisk"></ha-icon>
        <span>${localize('overview.disks', '{count}', String(disks.total))}</span>
        ${
          disks.standby
            ? html`<span class="part"
                ><span class="separator">·</span>
                ${localize('overview.standby', '{count}', String(disks.standby))}</span
              >`
            : nothing
        }
        ${
          hottest
            ? html`<span class="part"
                ><span class="separator">·</span>
                <span class="chip"
                  ><ha-icon class="chip-icon" icon="mdi:thermometer"></ha-icon>${localize('overview.max')}
                  ${renderFigure(this.hass, hottest)}</span
                ></span
              >`
            : nothing
        }
        ${
          disks.problems
            ? html`<span class="part problem-text"
                ><span class="separator">·</span> <ha-icon class="chip-icon" icon="mdi:alert"></ha-icon>${localize(
                  'overview.problems',
                  '{count}',
                  String(disks.problems),
                )}</span
              >`
            : nothing
        }
      </div>
    `;
  }

  private renderUps(ups: readonly UpsSummary[], serverName: string): TemplateResult | typeof nothing {
    if (!ups.length) {
      return nothing;
    }

    return html`
      <div class="heading">${localize('overview.power')}</div>
      ${ups.map((device) => {
        const status = readableState(this.hass, device.status);
        const problems = activeProblems(this.states, device.problems);
        const chips = device.metrics.flatMap((metric) => {
          const stateObj = readableState(this.hass, metric.entity);

          return stateObj ? [renderChip(metric.ref, stateObj, renderFigure(this.hass, stateObj))] : [];
        });

        return html`
          <div class="ups ${problems ? 'alert' : ''}" @click=${() => this.moreInfo(device.status)}>
            <ha-icon icon=${problems ? 'mdi:power-plug-off' : 'mdi:power-plug'}></ha-icon>
            <span class="ups-name">${deviceDisplayName(device.device, serverName)}</span>
            ${status ? html`<span class="ups-status">${formatUpsState(this.hass, status)}</span>` : nothing}
            <span class="ups-metrics">${chips}</span>
          </div>
        `;
      })}
    `;
  }

  /** A sum as Home Assistant would print a number in the user's locale. */
  private formatNumber(value: number): string {
    return new Intl.NumberFormat(this.hass?.locale?.language, { maximumFractionDigits: value < 10 ? 2 : 1 }).format(
      value,
    );
  }

  private navigate(path?: string): void {
    if (!path) {
      return;
    }

    handleAction(this, this.hass, { tap_action: { action: 'navigate', navigation_path: path } }, 'tap');
  }

  private moreInfo(entity?: EntityRegistryEntry): void {
    if (!entity) {
      return;
    }

    handleAction(this, this.hass, { entity: entity.entity_id, tap_action: { action: 'more-info' } }, 'tap');
  }

  static get styles(): CSSResultGroup {
    return [
      summaryStyles,
      css`
        .card-content {
          padding: 4px 16px 16px;
        }

        .notice {
          padding: 16px 0;
          color: var(--secondary-text-color);
          text-align: center;
        }

        .server + .server {
          margin-top: 16px;
          padding-top: 8px;
          border-top: 1px solid var(--divider-color);
        }

        .server-heading {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin: 14px 4px 8px;
        }

        .server-name {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 1.15em;
          font-weight: 500;
          color: var(--primary-text-color);
          --mdc-icon-size: 22px;
        }

        .server-name ha-icon {
          color: var(--state-icon-color, var(--primary-color));
        }

        .heading {
          margin: 14px 4px 6px;
          font-size: 0.75em;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--secondary-text-color);
        }

        /* Lifted off the card the same way the list card's rows are, so the two
           cards read as one family. */
        .kind,
        .pool,
        .disks,
        .ups {
          --tile-background: color-mix(
            in srgb,
            var(--primary-text-color) 7%,
            var(--ha-card-background, var(--card-background-color))
          );
          border-radius: 12px;
          background: var(--tile-background);
        }

        .kinds {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }

        @container (max-width: 340px) {
          .kinds {
            grid-template-columns: 1fr;
          }
        }

        .card-content {
          container-type: inline-size;
        }

        .kind {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          min-width: 0;
        }

        .kind.clickable {
          cursor: pointer;
        }

        .kind.clickable:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        .kind-icon {
          flex: none;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          color: var(--secondary-text-color);
          background: color-mix(in srgb, var(--secondary-text-color) 14%, transparent);
          --mdc-icon-size: 22px;
        }

        .kind.running .kind-icon {
          color: var(--success-color, var(--state-active-color, #43a047));
          background: color-mix(in srgb, var(--success-color, var(--state-active-color, #43a047)) 18%, transparent);
        }

        .kind-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }

        .kind-name {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .kind-line {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 2px 8px;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }

        .kind-line .figure {
          font-weight: 600;
          color: var(--primary-text-color);
        }

        .kind-line.metrics .figure {
          font-weight: 500;
        }

        .updates {
          color: var(--warning-color, #ffa600);
        }

        .of {
          margin: 0 1px;
          opacity: 0.6;
        }

        .pool {
          padding: 10px 12px;
          margin-bottom: 8px;
          cursor: pointer;
        }

        .pool-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
        }

        .pool-name {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
        }

        .pool-figures {
          display: inline-flex;
          gap: 10px;
          flex: none;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }

        .pool-figures > .figure {
          font-weight: 600;
          color: var(--primary-text-color);
        }

        .bar {
          height: 6px;
          margin-top: 8px;
          border-radius: 3px;
          overflow: hidden;
          background: var(--divider-color, rgba(127, 127, 127, 0.25));
        }

        .bar-fill {
          height: 100%;
          border-radius: 3px;
          background: var(--gauge-color);
          transition: width 0.3s ease;
        }

        .pool-jobs {
          margin-top: 6px;
          font-size: 0.85em;
        }

        .chip.activity {
          color: var(--info-color, var(--primary-color));
        }

        .disks,
        .ups {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 4px 8px;
          padding: 10px 12px;
          margin-bottom: 8px;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          --mdc-icon-size: 18px;
        }

        .ups {
          cursor: pointer;
        }

        .ups-name {
          font-weight: 500;
          color: var(--primary-text-color);
        }

        .ups-status {
          color: var(--success-color, var(--state-active-color, #43a047));
        }

        .ups.alert .ups-status,
        .ups.alert > ha-icon,
        .problem,
        .problem-text {
          color: var(--error-color, #db4437);
        }

        .ups-metrics {
          display: inline-flex;
          flex-wrap: wrap;
          gap: 4px 10px;
          margin-left: auto;
        }

        .separator {
          opacity: 0.6;
        }

        /* A part carries the separator in front of it, so a line that wraps
           breaks before a "·" and never leaves one on its own. */
        .part {
          white-space: nowrap;
        }

        @media (prefers-reduced-motion: reduce) {
          .bar-fill {
            transition: none;
          }
        }
      `,
    ];
  }
}

void defineWhenHostReady(() => customElements, 'mos-overview-card', MosOverviewCard);

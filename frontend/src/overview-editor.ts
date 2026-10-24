import { LitElement, html, css, nothing } from 'lit';
import type { CSSResultGroup, PropertyValues, TemplateResult } from 'lit';
import { property, state } from 'lit/decorators.js';
import { fireEvent } from 'custom-card-helpers';
import type { HomeAssistant, LovelaceCardEditor } from 'custom-card-helpers';
import type { UnsubscribeFunc } from 'home-assistant-js-websocket';

import type { MosOverviewCardConfig } from './types';
import { findServerDevices, subscribeDeviceRegistry } from './devices';
import type { DeviceRegistryEntry } from './devices';
import { OVERVIEW_DEFAULTS, OVERVIEW_TOGGLES } from './config';
import { localize, setLanguage } from './localize/localize';
import { defineWhenHostReady } from './register';

/** The overview card's editor: the server, a title, its sections and where a kind leads. */
export class MosOverviewCardEditor extends LitElement implements LovelaceCardEditor {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: MosOverviewCardConfig;

  @state() private _servers: DeviceRegistryEntry[] = [];

  private _unsubscribe?: UnsubscribeFunc;

  public setConfig(config: MosOverviewCardConfig): void {
    this._config = config;
  }

  public connectedCallback(): void {
    super.connectedCallback();
    this._subscribe();
  }

  public disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribe?.();
    this._unsubscribe = undefined;
  }

  protected willUpdate(changedProps: PropertyValues): void {
    if (changedProps.has('hass')) {
      setLanguage(this.hass?.locale?.language);
    }
  }

  protected updated(changedProps: PropertyValues): void {
    if (changedProps.has('hass')) {
      this._subscribe();
    }
  }

  private _subscribe(): void {
    if (this._unsubscribe || !this.isConnected || !this.hass?.connection) {
      return;
    }

    this._unsubscribe = subscribeDeviceRegistry(this.hass.connection, (devices) => {
      this._servers = findServerDevices(devices);
    });
  }

  private _schema(): Array<{ name: string; selector: Record<string, unknown> }> {
    return [
      { name: 'title', selector: { text: {} } },
      {
        name: 'server',
        selector: {
          select: {
            mode: 'dropdown',
            options: [
              { value: '', label: localize('editor.all_servers') },
              ...this._servers.map((server) => ({
                value: server.id,
                label: server.name_by_user || server.name || server.id,
              })),
            ],
          },
        },
      },
      ...OVERVIEW_TOGGLES.map((option) => ({ name: option, selector: { boolean: {} } })),
      { name: 'navigation_path', selector: { text: {} } },
    ];
  }

  private _data(config: MosOverviewCardConfig): Record<string, unknown> {
    const data: Record<string, unknown> = {
      title: config.title ?? '',
      server: config.server ?? '',
      navigation_path: config.navigation_path ?? '',
    };

    for (const option of OVERVIEW_TOGGLES) {
      const value = config[option];
      data[option] = typeof value === 'boolean' ? value : OVERVIEW_DEFAULTS[option];
    }

    return data;
  }

  protected render(): TemplateResult | typeof nothing {
    if (!this._config || !this.hass) {
      return nothing;
    }

    return html`
      <ha-form
        .hass=${this.hass}
        .data=${this._data(this._config)}
        .schema=${this._schema()}
        .computeLabel=${this._computeLabel}
        .computeHelper=${this._computeHelper}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `;
  }

  private _computeLabel = (schema: { name: string }): string => localize(`overview_editor.${schema.name}`);

  private _computeHelper = (schema: { name: string }): string =>
    schema.name === 'navigation_path' ? localize('overview_editor.navigation_path_hint') : '';

  private _valueChanged(ev: CustomEvent): void {
    if (!this._config) {
      return;
    }

    const value = ev.detail.value as Record<string, unknown>;
    const config = { ...this._config, ...value } as MosOverviewCardConfig;

    // A switch left at its default stays out of the YAML: the form hands back
    // every switch on the first change, not just the one that was flipped.
    for (const option of OVERVIEW_TOGGLES) {
      if (config[option] === OVERVIEW_DEFAULTS[option]) {
        delete config[option];
      }
    }

    // Cleared text fields come back as empty strings; dropped so the YAML stays clean.
    for (const key of ['title', 'server', 'navigation_path'] as const) {
      if (!value[key]) {
        delete config[key];
      }
    }

    fireEvent(this, 'config-changed', { config });
  }

  static get styles(): CSSResultGroup {
    return css`
      ha-form {
        display: block;
      }
    `;
  }
}

/** Settles once `mos-overview-card-editor` can be created; `getConfigElement` waits for it. */
export const overviewEditorDefined = defineWhenHostReady(
  () => customElements,
  'mos-overview-card-editor',
  MosOverviewCardEditor,
);

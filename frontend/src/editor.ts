import { LitElement, html, TemplateResult, css, CSSResultGroup, nothing, PropertyValues } from 'lit';
import { property, state } from 'lit/decorators.js';
import { HomeAssistant, LovelaceCardEditor, fireEvent } from 'custom-card-helpers';
import type { UnsubscribeFunc } from 'home-assistant-js-websocket';

import type { MosCardConfig } from './types';
import {
  DeviceRegistryEntry,
  MOS_DEVICE_KINDS,
  ROW_SORTS,
  SECONDARY_INFO_MODES,
  findServerDevices,
  subscribeDeviceRegistry,
} from './devices';
import { CARD_DEFAULTS, MAX_COLUMNS, TOGGLES, foldFilter, patternsToText } from './config';
import { localize, setLanguage } from './localize/localize';
import { defineWhenHostReady } from './register';

/**
 * The action options, paired with the action the card falls back to without them.
 *
 * The fallback is handed to the selector rather than written into the config, so
 * an untouched action stays absent from the YAML and the card's own default in
 * `setConfig` remains the single source of truth for it.
 */
const ACTIONS = [
  { name: 'tap_action', default: 'more-info' },
  { name: 'hold_action', default: 'none' },
  { name: 'double_tap_action', default: 'none' },
] as const;

/** Localization keys for the fields that need a line of explanation under them. */
const HELPERS: Readonly<Record<string, string>> = {
  kinds: 'editor.kinds_hint',
  confirm_stop: 'editor.confirm_stop_hint',
  secondary_info: 'editor.secondary_info_hint',
  show_server_summary: 'editor.show_server_summary_hint',
  show_history: 'editor.show_history_hint',
  show_services: 'editor.show_services_hint',
  show_problem: 'editor.show_problem_hint',
  filter_include: 'editor.filter_hint',
  max_rows: 'editor.max_rows_hint',
  columns: 'editor.columns_hint',
};

/** One entry of an `ha-form` schema. Home Assistant types this internally. */
interface FormSchema {
  name: string;
  /** Absent on the `constant` rows, which render text rather than an input. */
  selector?: Record<string, unknown>;
  /** `constant` renders `label: value` as static text and collects no data. */
  type?: 'constant';
  value?: string;
}

export class MosCardEditor extends LitElement implements LovelaceCardEditor {
  @property({ attribute: false }) public hass?: HomeAssistant;

  @state() private _config?: MosCardConfig;

  /**
   * The MOS servers to offer in the picker.
   *
   * Derived from the same device registry the card reads, so a server that
   * appears or goes away is reflected here without reopening the editor.
   */
  @state() private _servers: DeviceRegistryEntry[] = [];

  private _unsubscribe?: UnsubscribeFunc;

  public setConfig(config: MosCardConfig): void {
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

  /**
   * Mirror the frontend's language before anything is labelled.
   *
   * `ha-form` asks for every label and helper while it renders, so the language
   * has to be current by then. Same source as the card uses — see `setLanguage`.
   */
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

  /** Same shape, and the same `isConnected` guard, as the card's own. */
  private _subscribe(): void {
    if (this._unsubscribe || !this.isConnected || !this.hass?.connection) {
      return;
    }

    this._unsubscribe = subscribeDeviceRegistry(this.hass.connection, (devices) => {
      this._servers = findServerDevices(devices);
    });
  }

  /**
   * The form description Home Assistant renders from.
   *
   * `ha-form` is the supported way to build a card editor: Home Assistant maps
   * each selector onto whatever widget its current frontend uses, so the editor
   * follows the frontend instead of pinning itself to one generation of it.
   * Driving `ha-select` and `mwc-list-item` by hand is what broke the server
   * picker — `ha-select` was reimplemented on a different base and stopped
   * emitting the event this editor listened for, leaving a dropdown that opened,
   * listed both servers and did nothing at all when one was clicked.
   */
  private _schema(): FormSchema[] {
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
      {
        name: 'kinds',
        selector: {
          select: {
            multiple: true,
            options: MOS_DEVICE_KINDS.map((kind) => ({ value: kind, label: localize(`kinds.${kind}`) })),
          },
        },
      },
      { name: 'filter_include', selector: { text: {} } },
      { name: 'filter_exclude', selector: { text: {} } },
      { name: 'max_rows', selector: { number: { min: 1, max: 100, mode: 'box' } } },
      { name: 'columns', selector: { number: { min: 1, max: MAX_COLUMNS, mode: 'slider' } } },
      {
        name: 'sort',
        selector: {
          select: {
            mode: 'dropdown',
            options: ROW_SORTS.map((sort) => ({ value: sort, label: localize(`editor.sort_${sort}`) })),
          },
        },
      },
      {
        name: 'secondary_info',
        selector: {
          select: {
            mode: 'dropdown',
            options: SECONDARY_INFO_MODES.map((mode) => ({
              value: mode,
              label: localize(`editor.secondary_info_${mode}`),
            })),
          },
        },
      },
      ...TOGGLES.map((option) => ({ name: option, selector: { boolean: {} } })),
      // A `constant` row rather than a helper on the tap field: Home Assistant
      // renders a `ui_action` helper as a tooltip behind a "?", which hides a
      // rule that applies to all three gestures — and hides it completely on
      // touch, where there is nothing to hover. This row collects no data, so
      // the name never reaches the config.
      { name: 'actions_note', type: 'constant', value: localize('editor.actions_hint') },
      ...ACTIONS.map((action) => ({
        name: action.name,
        selector: { ui_action: { default_action: action.default } },
      })),
    ];
  }

  /**
   * The config as the form wants it: every key present, defaults filled in.
   *
   * Defaults here must match the ones the card's `setConfig` applies, or the
   * editor shows one thing while the card does another.
   */
  private _data(config: MosCardConfig): Record<string, unknown> {
    const data: Record<string, unknown> = {
      title: config.title ?? '',
      server: config.server ?? '',
      kinds: config.kinds ?? [...MOS_DEVICE_KINDS],
      sort: config.sort ?? CARD_DEFAULTS.sort,
      secondary_info: config.secondary_info ?? CARD_DEFAULTS.secondary_info,
      columns: config.columns ?? CARD_DEFAULTS.columns,
      // The filter is a list in the config and a comma-separated line in the
      // form, because a repeating text field is not something `ha-form` offers.
      filter_include: patternsToText(config.filter?.include),
      filter_exclude: patternsToText(config.filter?.exclude),
      max_rows: config.max_rows,
    };

    for (const option of TOGGLES) {
      const value = config[option];
      data[option] = typeof value === 'boolean' ? value : CARD_DEFAULTS[option];
    }

    for (const action of ACTIONS) {
      data[action.name] = config[action.name];
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

  private _computeLabel = (schema: FormSchema): string => localize(`editor.${schema.name}`);

  private _computeHelper = (schema: FormSchema): string => {
    const key = HELPERS[schema.name];

    return key ? localize(key) : '';
  };

  private _valueChanged(ev: CustomEvent): void {
    if (!this._config) {
      return;
    }

    const value = ev.detail.value as Record<string, unknown>;
    const config: MosCardConfig = { ...this._config, ...value } as MosCardConfig;

    // The two filter lines are the form's own fields, not config keys: they are
    // folded back into one `filter` object, and the object is dropped entirely
    // when both are empty so an untouched card keeps no filter at all.
    const filter = foldFilter(value.filter_include, value.filter_exclude);

    delete (config as Record<string, unknown>).filter_include;
    delete (config as Record<string, unknown>).filter_exclude;

    if (filter) {
      config.filter = filter;
    } else {
      delete config.filter;
    }

    if (!value.max_rows) {
      delete config.max_rows;
    }

    // Clearing the multi-select is a step on the way to picking something else,
    // not a request for a card showing no kinds — which is what the card
    // rejects. Dropping the key lets it fall back to all of them, rather than
    // throwing "'kinds' must not be empty" into the live preview while someone
    // is still choosing.
    if (Array.isArray(value.kinds) && !value.kinds.length) {
      delete config.kinds;
    }

    // The form has to hand back a value for every key it renders, so the two
    // optional ones arrive as empty strings when cleared. Lovelace would write
    // those into the YAML as empty keys, so they are dropped rather than stored.
    if (!value.title) {
      delete config.title;
    }
    if (!value.server) {
      delete config.server;
    }

    // Same for an action the user cleared: removing the key lets the card apply
    // its own default again, where storing an empty object would suppress it.
    for (const action of ACTIONS) {
      if (!value[action.name]) {
        delete config[action.name];
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

/** Settles once `mos-card-editor` can be created; `getConfigElement` waits for it. */
export const editorDefined = defineWhenHostReady(() => customElements, 'mos-card-editor', MosCardEditor);

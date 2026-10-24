/**
 * The pieces both cards draw the same way: states and their figures, rings,
 * sparklines, and the server's own summary tiles, uptime and services.
 *
 * Functions of `hass` rather than methods, so the list card and the overview
 * card render a server identically without one inheriting from the other.
 */
import { html, svg, nothing, css } from 'lit';
import type { TemplateResult } from 'lit';
import type { HassEntity } from 'home-assistant-js-websocket';
import { computeStateDisplay } from 'custom-card-helpers';
import type { HomeAssistant } from 'custom-card-helpers';

import { SERVER_BOOT_TIME, isUnavailableState } from './devices';
import type { EntityRegistryEntry, MetricRef, RowMetric, ServerMetricRef, ServiceRef } from './devices';
import { GAUGE_ROTATION, GAUGE_SIZE, gaugeGeometry, gaugePercent, severityFor } from './gauge';
import { sparklinePath } from './history';
import type { Sample } from './history';
import { upsFlags, uptimeSince } from './rows';
import { localize } from './localize/localize';

type FormattingHass = HomeAssistant & {
  formatEntityState?: (stateObj: HassEntity) => string;
  formatEntityStateToParts?: (stateObj: HassEntity) => Array<{ type: string; value: string }>;
};

/** The sparkline's drawing box; it is stretched to whatever width it is given. */
const SPARK_WIDTH = 100;
const SPARK_HEIGHT = 28;

/**
 * A state as the rest of Home Assistant writes it.
 *
 * `formatEntityState` is the core's own formatter: it resolves the state
 * translations an integration declares under its entity's translation_key,
 * so a Docker container reads "Stopped" here exactly as it does in the
 * more-info dialog. `computeStateDisplay` from custom-card-helpers predates
 * translation_key enums and hands back the raw `exited`, so it is only the
 * fallback for cores too old to offer the former.
 */
export function formatState(hass: HomeAssistant, stateObj?: HassEntity): string {
  if (!stateObj) {
    return localize('common.no_state_entity');
  }

  const formatting = hass as FormattingHass;

  return formatting.formatEntityState
    ? formatting.formatEntityState(stateObj)
    : computeStateDisplay(hass.localize, stateObj, hass.locale);
}

/** A UPS status in words: "OL CHRG" reads as "Online, Charging". */
export function formatUpsState(hass: HomeAssistant, stateObj?: HassEntity): string {
  const flags = stateObj && !isUnavailableState(stateObj.state) ? upsFlags(stateObj.state) : [];

  return flags.length
    ? flags.map(({ flag, known }) => (known ? localize(`ups.${flag.toUpperCase()}`) : flag)).join(', ')
    : formatState(hass, stateObj);
}

/**
 * A state split into its number and its unit, in the core's own formatting.
 *
 * `formatEntityStateToParts` is how the core's own tiles get the two apart;
 * on a core without it the unit is cut off the formatted string instead.
 */
export function stateParts(hass: HomeAssistant, stateObj: HassEntity): { value: string; unit: string } {
  const formatting = hass as FormattingHass;

  if (formatting.formatEntityStateToParts) {
    const parts = formatting.formatEntityStateToParts(stateObj);

    return {
      value: parts
        .filter((part) => part.type !== 'unit')
        .map((part) => part.value)
        .join('')
        .trim(),
      unit: parts
        .filter((part) => part.type === 'unit')
        .map((part) => part.value)
        .join(''),
    };
  }

  const text = formatState(hass, stateObj);
  const unit = stateObj.attributes.unit_of_measurement as string | undefined;

  return unit && text.endsWith(unit) ? { value: text.slice(0, -unit.length).trim(), unit } : { value: text, unit: '' };
}

/** A state as its number and a quieter unit after it. */
export function renderFigure(hass: HomeAssistant, stateObj: HassEntity): TemplateResult {
  const { value, unit } = stateParts(hass, stateObj);

  return html`<span class="figure">${value}${unit ? html`<span class="unit">${unit}</span>` : nothing}</span>`;
}

/** The state an entity has, or undefined while Home Assistant has no reading for it. */
export function readableState(hass: HomeAssistant | undefined, entity?: EntityRegistryEntry): HassEntity | undefined {
  const stateObj = entity ? hass?.states[entity.entity_id] : undefined;

  return stateObj && !isUnavailableState(stateObj.state) ? stateObj : undefined;
}

/**
 * A ring in a 40-unit box: 4 wide where it frames an icon (`gauge`), 8 where
 * it is drawn at icon size in a line of text (`mini-gauge`).
 */
export function renderGauge(percent: number, className = 'gauge', inverse = false): TemplateResult {
  const centre = GAUGE_SIZE / 2;
  const stroke = className === 'gauge' ? 4 : 8;
  const { radius, circumference, sweep } = gaugeGeometry(stroke);

  return html`
    <svg
      class="${className} severity-${severityFor(percent, inverse)}"
      viewBox="0 0 ${GAUGE_SIZE} ${GAUGE_SIZE}"
      aria-hidden="true"
    >
      ${svg`
        <g transform="rotate(${GAUGE_ROTATION} ${centre} ${centre})">
          <circle class="track" cx=${centre} cy=${centre} r=${radius} stroke-width=${stroke}
            stroke-dasharray="${sweep} ${circumference}"></circle>
          ${
            percent > 0
              ? svg`<circle class="value" cx=${centre} cy=${centre} r=${radius} stroke-width=${stroke}
                  stroke-dasharray="${(sweep * percent) / 100} ${circumference}"></circle>`
              : nothing
          }
        </g>
      `}
    </svg>
  `;
}

/** A figure with what it is in front of it: a ring for a percentage, its icon otherwise. */
export function renderChip(ref: MetricRef, stateObj: HassEntity, figure: TemplateResult): TemplateResult {
  const percent = stateObj.attributes.unit_of_measurement === '%' ? gaugePercent(stateObj.state) : undefined;

  return html`<span class="chip" title=${localize(`metrics.${ref.label}`)}
    >${
      percent === undefined
        ? html`<ha-icon class="chip-icon" .icon=${ref.icon}></ha-icon>`
        : renderGauge(percent, 'mini-gauge', ref.inverse)
    }${figure}</span
  >`;
}

/**
 * One server measurement: a ring for a percentage, the icon alone otherwise,
 * beside the figure and what it is, and its last hour where there is one.
 * Left out while the server cannot report it.
 */
export function renderServerTile(
  hass: HomeAssistant,
  metric: RowMetric<ServerMetricRef>,
  samples?: readonly Sample[],
): TemplateResult | undefined {
  const stateObj = readableState(hass, metric.entity);

  if (!stateObj) {
    return undefined;
  }

  const percent = metric.ref.gauge ? gaugePercent(stateObj.state) : undefined;
  const path = samples ? sparklinePath(samples, Date.now(), SPARK_WIDTH, SPARK_HEIGHT) : undefined;
  const severity = percent === undefined ? '' : `severity-${severityFor(percent, metric.ref.inverse)}`;

  return html`
    <div class="tile ${path ? 'with-history' : ''} ${severity}" title=${formatState(hass, stateObj)}>
      <div class="tile-icon ${percent === undefined ? 'plain' : ''}">
        ${percent === undefined ? nothing : renderGauge(percent, 'gauge', metric.ref.inverse)}
        <ha-icon .icon=${metric.ref.icon}></ha-icon>
      </div>
      <div class="tile-text">
        ${renderFigure(hass, stateObj)}
        <span class="tile-label">${localize(`metrics.${metric.ref.label}`)}</span>
      </div>
      ${
        path
          ? html`<svg
              class="spark"
              viewBox="0 0 ${SPARK_WIDTH} ${SPARK_HEIGHT}"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              ${svg`<path d=${path}></path>`}
            </svg>`
          : nothing
      }
    </div>
  `;
}

/** How long the server has been up, as its two largest units. */
export function renderUptime(hass: HomeAssistant, bootTime?: EntityRegistryEntry): TemplateResult | typeof nothing {
  const stateObj = readableState(hass, bootTime);
  const uptime = uptimeSince(stateObj?.state, Date.now());

  if (!stateObj || !uptime) {
    return nothing;
  }

  const parts: Array<[number, string]> = uptime.days
    ? [
        [uptime.days, 'd'],
        [uptime.hours, 'h'],
      ]
    : uptime.hours
      ? [
          [uptime.hours, 'h'],
          [uptime.minutes, 'min'],
        ]
      : [[uptime.minutes, 'min']];
  const duration = parts.map(([value, unit]) => `${value} ${localize(`units.${unit}`)}`).join(' ');

  return html`<span class="uptime" title=${formatState(hass, stateObj)}>
    <ha-icon .icon=${SERVER_BOOT_TIME.icon}></ha-icon>${localize('metrics.uptime_for', '{duration}', duration)}
  </span>`;
}

/** The server's services as chips, lit while on; nothing for a server that reports none. */
export function renderServices(
  hass: HomeAssistant,
  services: readonly RowMetric<ServiceRef>[],
): TemplateResult | typeof nothing {
  const chips = services.flatMap((service) => {
    const stateObj = readableState(hass, service.entity);

    if (!stateObj) {
      return [];
    }

    return [
      html`<span
        class="service ${stateObj.state === 'on' ? 'on' : 'off'}"
        title=${`${service.ref.name}: ${formatState(hass, stateObj)}`}
      >
        <ha-icon .icon=${service.ref.icon}></ha-icon>${service.ref.name}
      </span>`,
    ];
  });

  return chips.length ? html`<div class="services">${chips}</div>` : nothing;
}

/** Styles for everything above, shared by both cards. */
export const summaryStyles = css`
  .uptime {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    flex: none;
    font-size: 0.8em;
    font-weight: 400;
    color: var(--secondary-text-color);
    --mdc-icon-size: 14px;
  }

  .server-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin: 4px 4px 10px;
  }

  .tile {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .tile.with-history {
    flex: 1 1 140px;
  }

  .tile-icon {
    position: relative;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    --mdc-icon-size: 18px;
    color: var(--secondary-text-color);
  }

  /* Without a ring the icon still gets a round footprint, so a row of tiles
     keeps one rhythm — filled rather than outlined, so it does not read as a
     ring standing at zero. */
  .tile-icon.plain {
    border-radius: 50%;
    background: color-mix(in srgb, var(--secondary-text-color) 12%, transparent);
  }

  .tile-text {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
  }

  .tile .figure {
    font-size: 1.05em;
    font-weight: 600;
    color: var(--primary-text-color);
  }

  .tile-label {
    font-size: 0.68em;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--secondary-text-color);
  }

  .spark {
    flex: 1;
    min-width: 48px;
    height: 28px;
    overflow: visible;
  }

  .spark path {
    fill: none;
    stroke: var(--gauge-color, var(--primary-color));
    stroke-width: 1.5;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .gauge {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .mini-gauge {
    width: 14px;
    height: 14px;
    flex: none;
  }

  .gauge circle,
  .mini-gauge circle {
    fill: none;
  }

  .gauge .track {
    stroke: var(--divider-color, rgba(127, 127, 127, 0.25));
  }

  .mini-gauge .track {
    stroke: color-mix(in srgb, currentColor 35%, transparent);
  }

  /* A fixed scale rather than the theme's accent: a ring says how loaded or
     how full something is, which a theme has no business recolouring. */
  .gauge .value,
  .mini-gauge .value {
    stroke: var(--gauge-color);
    stroke-linecap: round;
    transition: stroke-dasharray 0.3s ease;
  }

  .severity-low {
    --gauge-color: var(--green-color, #43a047);
  }

  .severity-medium {
    --gauge-color: var(--amber-color, #ffc107);
  }

  .severity-high {
    --gauge-color: var(--orange-color, #fb8c00);
  }

  .severity-critical {
    --gauge-color: var(--red-color, #e53935);
  }

  .services {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 4px 10px;
  }

  /* Lit like a running row while the service is on, dimmed while it is off. */
  .service {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px 2px 6px;
    border-radius: 12px;
    font-size: 0.78em;
    --mdc-icon-size: 14px;
  }

  .service.on {
    color: var(--success-color, #43a047);
    background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent);
  }

  .service.off {
    color: var(--secondary-text-color);
    background: color-mix(in srgb, var(--secondary-text-color) 10%, transparent);
    opacity: 0.7;
  }

  /* A measurement in a line: what it is in front, kept together as one unit
     so the line breaks between measurements and never inside one. */
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    white-space: nowrap;
    vertical-align: bottom;
  }

  .chip-icon {
    --mdc-icon-size: 14px;
    opacity: 0.8;
  }

  /* A figure wraps as a whole: a number on one line and its unit on the next
     reads as two values. */
  .figure {
    white-space: nowrap;
  }

  .unit {
    margin-left: 0.15em;
    font-size: 0.75em;
    font-weight: 400;
    opacity: 0.8;
  }

  @media (prefers-reduced-motion: reduce) {
    .gauge .value,
    .mini-gauge .value {
      transition: none;
    }
  }
`;

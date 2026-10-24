/**
 * The ring the server heading draws its percentages as.
 *
 * A 270° arc open at the bottom, after the gauges in AzAel76's
 * ha-mos-card-addons (MIT). Drawn as plain SVG inside the card rather than as
 * an element of its own, so there is no second tag to register.
 */

/** How full a ring is, as a step of a fixed scale rather than a theme accent. */
export const SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;

export type Severity = (typeof SEVERITIES)[number];

/** The upper bound of each step but the last, in percent. */
const SEVERITY_STEPS: readonly number[] = [50, 75, 90];

export function severityFor(percent: number, inverse = false): Severity {
  if (inverse) {
    return severityFor(100 - percent);
  }

  const step = SEVERITY_STEPS.findIndex((bound) => percent <= bound);

  return SEVERITIES[step === -1 ? SEVERITIES.length - 1 : step];
}

/** A state as a percentage between 0 and 100, or undefined when it is not a number. */
export function gaugePercent(state: string | undefined): number | undefined {
  if (state === undefined || state.trim() === '') {
    return undefined;
  }

  const value = Number(state);

  return Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : undefined;
}

export const GAUGE_SIZE = 40;

const GAP_DEGREES = 90;

/** Turns the circle so its gap sits at six o'clock instead of the stroke starting at three. */
export const GAUGE_ROTATION = 90 + GAP_DEGREES / 2;

export interface GaugeGeometry {
  readonly radius: number;
  readonly circumference: number;
  /** The track's length along the circle; the value is drawn as a share of it. */
  readonly sweep: number;
}

/** The ring's measurements in a `GAUGE_SIZE` box for a given stroke width. */
export function gaugeGeometry(stroke: number): GaugeGeometry {
  const radius = (GAUGE_SIZE - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  return { radius, circumference, sweep: circumference * ((360 - GAP_DEGREES) / 360) };
}

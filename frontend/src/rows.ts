/**
 * Row-level logic: what colour a row is, what order rows come in, how many of
 * them are shown, which power buttons are still waiting, and whether a row's
 * link is one a browser should be handed.
 *
 * All of it takes plain values and returns plain values. It lives here rather
 * than on the component because none of it needs a DOM, a `hass` or a render —
 * and because on the component it could only be checked by driving the card.
 */
import type { ActionConfig } from 'custom-card-helpers';
import { KIND_INFO, isUnavailableState } from './devices';
import type { MosDeviceKind, RowSort } from './devices';

/**
 * The colour families a row can be drawn in.
 *
 * Kept to a handful of names rather than a colour per state so the palette
 * stays a theme concern: the CSS maps each tone onto a Home Assistant theme
 * variable, and a state nobody anticipated lands on the neutral one.
 *
 * The order is also the order `sort: state` lists them in, which is why there
 * is one list and not two: what reads as "up" is what sorts to the top.
 */
export const TONES = ['active', 'idle', 'neutral', 'inactive', 'unknown'] as const;

export type Tone = (typeof TONES)[number];

/** States that mean the thing is doing its job. */
const ACTIVE_STATES = new Set(['running', 'on', 'active', 'ol', 'online']);

/** States that mean it exists but is not doing its job yet. */
const IDLE_STATES = new Set(['paused', 'frozen', 'standby', 'idle', 'sleeping', 'starting']);

/**
 * The tone a row of this kind and state is drawn in.
 *
 * Only kinds whose state says something about *running* are coloured. A disk
 * reporting `active` is naming its ATA power mode and a pool reports how full
 * it is — neither is good news or bad news, and colouring them drowns out the
 * containers, which are the reason to look at the card at all.
 */
export function toneFor(kind: MosDeviceKind, state: string | undefined): Tone {
  if (isUnavailableState(state)) {
    return 'unknown';
  }

  // Named kinds rather than "everything without a power switch": the UPS has no
  // switch either, but `ol` means mains power is fine and that is worth the
  // colour. A disk reporting `active` is naming its ATA power mode and a pool
  // reports how full it is — neither is good news or bad news.
  if (kind === 'disk' || kind === 'storage_pool') {
    return 'neutral';
  }

  const value = (state as string).toLowerCase();

  if (ACTIVE_STATES.has(value)) {
    return 'active';
  }

  return IDLE_STATES.has(value) ? 'idle' : 'inactive';
}

/** What a group's heading counts: how many of its rows are up, and how many wait on an update. */
export interface GroupCounts {
  readonly running: number;
  readonly total: number;
  readonly updates: number;
}

/**
 * Count a group from its rows' states and update states.
 *
 * Counted over every row, not just the ones `max_rows` leaves visible, so the
 * heading says what the server has rather than what fits.
 */
export function countGroup(
  kind: MosDeviceKind,
  rows: ReadonlyArray<{ state: string | undefined; update: string | undefined }>,
): GroupCounts {
  return {
    running: rows.filter((row) => toneFor(kind, row.state) === 'active').length,
    total: rows.length,
    updates: rows.filter((row) => row.update === 'on').length,
  };
}

/**
 * Whether a row's measurements mean anything in its current state.
 *
 * A guest that is not running reports what it last used — a stopped LXC its
 * zeros, a stopped container the memory it had — which reads as a live figure
 * beside "Stopped". Only guests that run or are paused show theirs; kinds that
 * do not run always do.
 */
export function showsMeasurements(kind: MosDeviceKind, state: string | undefined): boolean {
  if (!KIND_INFO[kind].hasPower) {
    return true;
  }

  const tone = toneFor(kind, state);

  return tone === 'active' || tone === 'idle';
}

/** The NUT status flags a UPS reports, in the order MOS lists them. */
export const UPS_FLAGS = [
  'OL',
  'OB',
  'LB',
  'HB',
  'RB',
  'CHRG',
  'DISCHRG',
  'BYPASS',
  'CAL',
  'OFF',
  'OVER',
  'TRIM',
  'BOOST',
  'FSD',
] as const;

/**
 * A UPS status string split into its flags, each known flag marked so it can
 * be put into words. "OL CHRG" is two facts, not one code; an unknown flag
 * stays as it is rather than being dropped.
 */
export function upsFlags(state: string | undefined): Array<{ flag: string; known: boolean }> {
  return (state ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .map((flag) => ({ flag, known: (UPS_FLAGS as readonly string[]).includes(flag.toUpperCase()) }));
}

/** How long the server has been up, split into the units a heading shows. */
export interface Uptime {
  readonly days: number;
  readonly hours: number;
  readonly minutes: number;
}

/** The uptime since a boot timestamp, or undefined for one that is not a time or lies ahead. */
export function uptimeSince(bootTime: string | undefined, now: number): Uptime | undefined {
  const booted = bootTime ? Date.parse(bootTime) : NaN;

  if (!Number.isFinite(booted) || booted > now) {
    return undefined;
  }

  const minutes = Math.floor((now - booted) / 60_000);

  return { days: Math.floor(minutes / 1440), hours: Math.floor((minutes % 1440) / 60), minutes: minutes % 60 };
}

/**
 * The URL schemes a row's link button may point at.
 *
 * The same set Home Assistant's own device registry validates
 * `configuration_url` against, so a link the core would accept on the device
 * page is a link this card draws. `homeassistant:` is in it because the
 * companion app uses it for deep links.
 */
const LINK_SCHEMES: ReadonlySet<string> = new Set(['http:', 'https:', 'homeassistant:']);

/**
 * Whether a URL is one to put behind the link button.
 *
 * A row's link comes from `web_ui_url` on the state sensor, which is a plain
 * state attribute the MOS server fills in and nothing validates on the way —
 * unlike `configuration_url`, which Home Assistant checks when the device is
 * registered. A `javascript:` URL in an `href` runs in the dashboard's own
 * context the moment someone clicks it, so the scheme is checked here rather
 * than assumed. Anything else is treated as no link at all, which is what a row
 * without a web interface already renders.
 *
 * Parsed without a base, so a value that is not an absolute URL is rejected
 * too. Home Assistant requires a host for the same reason.
 */
export function isLinkableUrl(url: string | undefined): boolean {
  if (!url) {
    return false;
  }

  try {
    const parsed = new URL(url);

    return LINK_SCHEMES.has(parsed.protocol) && parsed.host !== '';
  } catch {
    return false;
  }
}

/** The minimum a row has to carry to be ordered. */
export interface OrderableRow {
  name: string;
  kind: MosDeviceKind;
}

/**
 * How two rows of the same kind are ordered.
 *
 * `state` ranks by the same tone the row is drawn in, so the sorted order and
 * the colours tell the same story, and falls back to the name so that two rows
 * in the same state keep a stable, readable order.
 */
export function compareRows<T extends OrderableRow>(
  sort: RowSort | undefined,
  stateOf: (row: T) => string | undefined,
): (left: T, right: T) => number {
  return (left, right) => {
    if (sort === 'state') {
      const rank =
        TONES.indexOf(toneFor(left.kind, stateOf(left))) - TONES.indexOf(toneFor(right.kind, stateOf(right)));

      if (rank !== 0) {
        return rank;
      }
    }

    return left.name.localeCompare(right.name);
  };
}

/**
 * The rows a group shows, and how many it is holding back.
 *
 * An absent cap, an opened group, or fewer rows than the cap all mean the same
 * thing: show everything and hide nothing. Only a cap that actually bites
 * reports a count, so the caller can tell "nothing hidden" from "nothing left".
 */
export function capRows<T>(
  rows: readonly T[],
  max: number | undefined,
  expanded: boolean,
): { rows: T[]; hidden: number } {
  if (max === undefined || expanded || rows.length <= max) {
    return { rows: [...rows], hidden: 0 };
  }

  return { rows: rows.slice(0, max), hidden: rows.length - max };
}

/**
 * Which waiting power buttons the incoming states have answered.
 *
 * The recorded value is the state the switch had when the button was pressed,
 * so anything else means the request landed — including a switch that has gone
 * unavailable, which is an answer of a kind and better than spinning until the
 * timeout.
 */
export function settledPending(
  pending: ReadonlyMap<string, string>,
  stateOf: (entityId: string) => string | undefined,
): string[] {
  const settled: string[] = [];

  for (const [entityId, before] of pending) {
    if ((stateOf(entityId) ?? '') !== before) {
      settled.push(entityId);
    }
  }

  return settled;
}

/**
 * The timeouts that end a wait nobody answered.
 *
 * Split from the map of waiting switches because the two fail differently: the
 * map is state Lit has to see change, while these are side effects that have to
 * be cancelled — on an answer, and on the card being torn down, which happens
 * on every dashboard edit. A leaked timeout fires against a detached element.
 */
export class PendingTimers {
  private readonly timers = new Map<string, ReturnType<typeof setTimeout>>();

  constructor(private readonly timeoutMs: number) {}

  /** How many waits are still armed. Exposed for tests and assertions. */
  get size(): number {
    return this.timers.size;
  }

  /**
   * Arm a timeout for one switch, replacing any it already had.
   *
   * Replacing rather than stacking: two timeouts for one switch would fire
   * twice, and the second would end a wait the caller had already restarted.
   */
  start(entityId: string, onExpire: (entityId: string) => void): void {
    this.stop(entityId);
    this.timers.set(
      entityId,
      setTimeout(() => {
        this.timers.delete(entityId);
        onExpire(entityId);
      }, this.timeoutMs),
    );
  }

  /** Cancel one wait. Silent when there is none, so callers need not check. */
  stop(entityId: string): void {
    const timer = this.timers.get(entityId);

    if (timer !== undefined) {
      clearTimeout(timer);
      this.timers.delete(entityId);
    }
  }

  /** Cancel everything. The teardown path, and safe to call twice. */
  stopAll(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }

    this.timers.clear();
  }
}

/**
 * What a placeholder in an action config stands for on one row.
 *
 * A key missing from this map is left in place rather than emptied, so a typo
 * shows up as `[[entty]]` in the dialog it opened instead of silently opening
 * an empty one. A key that is present but has no value on this row — the power
 * switch of a disk, which has none — substitutes to nothing.
 */
export type PlaceholderValues = Readonly<Record<string, string | undefined>>;

/**
 * `[[key]]`, the spelling decluttering-card established for plain substitution.
 *
 * Deliberately not `{{ }}`: in Home Assistant those are Jinja, rendered in the
 * backend, and someone who reads them here would reasonably expect
 * `{{ states('sensor.x') }}` to work. Nothing here evaluates anything.
 */
const PLACEHOLDER = /\[\[(\w+)\]\]/g;

/**
 * Put the row's own values into an action config written once for every row.
 *
 * The card renders its rows itself rather than as Home Assistant entity rows,
 * so the usual templating cards have no per-row element to hang a template on
 * and a `fire-dom-event` popup would open on the same entity from whichever row
 * was tapped. Substituting on the way to the action handler is what gives that
 * one config a row.
 *
 * Walks strings, arrays and plain objects, and returns everything else — the
 * numbers and booleans of an action config — untouched. Values stay strings: a
 * placeholder is text substitution, not a typed lookup.
 */
export function fillPlaceholders<T>(value: T, values: PlaceholderValues): T {
  if (typeof value === 'string') {
    return value.replace(PLACEHOLDER, (placeholder, key: string) =>
      Object.hasOwn(values, key) ? (values[key] ?? '') : placeholder,
    ) as T;
  }

  if (Array.isArray(value)) {
    return value.map((item) => fillPlaceholders(item, values)) as T;
  }

  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, fillPlaceholders(item, values)])) as T;
  }

  return value;
}

/**
 * The entity a `more-info` action wants opened, if it names one of its own.
 *
 * `handleAction` reads the entity for `more-info` off the object the card hands
 * it, never off the action config, so an `entity` written inside the action
 * would otherwise be dropped in silence — with or without a placeholder in it.
 * Lifting it out here is what lets `entity: '[[power]]'` open the row's switch
 * instead of its state entity. Home Assistant's own frontend resolves the same
 * way round, `actionConfig.entity || config.entity`.
 *
 * Returns `undefined` for every other action, so a `fire-dom-event` payload
 * that happens to carry an `entity` stays the payload's own, and for a
 * placeholder the row has no value for — `[[power]]` on a disk — so that a tap
 * opens the row's usual dialog rather than none at all.
 */
export function moreInfoEntity(action: ActionConfig | undefined, values: PlaceholderValues): string | undefined {
  if (action?.action !== 'more-info' || !action.entity) {
    return undefined;
  }

  return fillPlaceholders(action.entity, values) || undefined;
}

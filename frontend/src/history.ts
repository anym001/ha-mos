/**
 * The recent course of the server's load, for the sparklines in its heading.
 *
 * Loaded once from the recorder when the card appears and continued from the
 * states the card is handed anyway, so it costs one query per card and nothing
 * per update. After the approach in AzAel76's ha-mos-card-addons (MIT).
 */

/** How far back a sparkline reaches. */
export const HISTORY_WINDOW_MS = 60 * 60 * 1000;

/** One reading: when, in epoch milliseconds, and the value. */
export type Sample = readonly [time: number, value: number];

/** One state as `history/history_during_period` sends it with `minimal_response`. */
interface CompressedState {
  s: string;
  /** Last updated, in epoch seconds. */
  lu: number;
}

export type HistoryResponse = Record<string, readonly CompressedState[] | undefined>;

/** The numeric readings of one entity, oldest first; a reading that is not a number is dropped. */
export function parseHistory(response: HistoryResponse, entityId: string): Sample[] {
  const samples: Sample[] = [];

  for (const state of response[entityId] ?? []) {
    const value = Number(state.s);

    if (state.s !== '' && Number.isFinite(value)) {
      samples.push([state.lu * 1000, value]);
    }
  }

  return samples.sort((a, b) => a[0] - b[0]);
}

/**
 * The series with a new reading added and anything older than the window dropped.
 *
 * Returns the same array when the reading adds nothing — not a number, or not
 * newer than the last one — so a caller can compare by identity.
 */
export function appendSample(samples: readonly Sample[], time: number, state: string, now: number): readonly Sample[] {
  const value = Number(state);
  const last = samples[samples.length - 1];

  if (state === '' || !Number.isFinite(value) || (last && last[0] >= time)) {
    return samples;
  }

  return [...samples.filter(([at]) => at >= now - HISTORY_WINDOW_MS), [time, value]];
}

/**
 * An SVG path through the readings, scaled to a 0–100 range and the window.
 *
 * The last reading is carried on to `now`, because a value holds until it
 * changes: a flat stretch at the end is the server reporting the same load,
 * not a gap. Undefined with fewer than two points to draw a line between.
 */
export function sparklinePath(
  samples: readonly Sample[],
  now: number,
  width: number,
  height: number,
): string | undefined {
  const start = now - HISTORY_WINDOW_MS;
  const visible = samples.filter(([at]) => at >= start);
  const before = samples.filter(([at]) => at < start).pop();
  const points: Sample[] = before ? [[start, before[1]], ...visible] : [...visible];
  const last = points[points.length - 1];

  if (last && last[0] < now) {
    points.push([now, last[1]]);
  }

  if (points.length < 2) {
    return undefined;
  }

  const x = (time: number): number => ((time - start) / HISTORY_WINDOW_MS) * width;
  const y = (value: number): number => height - (Math.min(100, Math.max(0, value)) / 100) * height;

  return points
    .map(([time, value], index) => `${index ? 'L' : 'M'}${x(time).toFixed(1)},${y(value).toFixed(1)}`)
    .join('');
}

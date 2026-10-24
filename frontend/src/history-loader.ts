/**
 * Keeps the last hour of a set of entities for a card's sparklines.
 *
 * One `history/history_during_period` query per entity, the first time a card
 * asks for it, then continued from the states `hass` brings anyway — no
 * polling and no history subscription. The readings are handed to the card
 * through `onChange`, so it can keep them in reactive state of its own.
 */
import type { HomeAssistant } from 'custom-card-helpers';

import { HISTORY_WINDOW_MS, appendSample, parseHistory } from './history';
import type { HistoryResponse, Sample } from './history';

export type HistoryMap = ReadonlyMap<string, readonly Sample[]>;

export class HistoryLoader {
  private samples: HistoryMap = new Map();

  /** Entities whose history has been asked for, so a slow answer is not asked for twice. */
  private readonly requested = new Set<string>();

  public constructor(private readonly onChange: (samples: HistoryMap) => void) {}

  /**
   * Ask the recorder for the last hour of each entity not yet asked for.
   *
   * Best effort: without the recorder there is no history, and the card keeps
   * its rings and figures and simply draws no line.
   */
  public request(hass: HomeAssistant | undefined, entityIds: readonly string[]): void {
    const ids = entityIds.filter((id) => !this.requested.has(id));

    if (!ids.length || !hass?.callWS) {
      return;
    }

    for (const id of ids) {
      this.requested.add(id);
    }

    // The current reading starts the line at once; the recorder's answer fills
    // in what came before it.
    this.continue(hass);

    hass
      .callWS<HistoryResponse>({
        type: 'history/history_during_period',
        start_time: new Date(Date.now() - HISTORY_WINDOW_MS).toISOString(),
        entity_ids: ids,
        minimal_response: true,
        no_attributes: true,
      })
      .then((response) => {
        const samples = new Map(this.samples);

        for (const id of ids) {
          // Readings that arrived while the query was out are newer than its answer.
          const live = samples.get(id) ?? [];
          const recorded = parseHistory(response, id);
          const last = recorded[recorded.length - 1];

          samples.set(id, [...recorded, ...live.filter(([at]) => !last || at > last[0])]);
        }

        this.update(samples);
      })
      .catch(() => undefined);
  }

  /** Carry each series on with the state `hass` now holds for it. */
  public continue(hass: HomeAssistant | undefined): void {
    if (!this.requested.size || !hass) {
      return;
    }

    let samples: Map<string, readonly Sample[]> | undefined;
    const now = Date.now();

    for (const id of this.requested) {
      const stateObj = hass.states[id];
      const series = this.samples.get(id) ?? [];

      if (!stateObj) {
        continue;
      }

      const next = appendSample(series, Date.parse(stateObj.last_updated) || now, stateObj.state, now);

      if (next !== series) {
        samples ??= new Map(this.samples);
        samples.set(id, next);
      }
    }

    if (samples) {
      this.update(samples);
    }
  }

  private update(samples: HistoryMap): void {
    this.samples = samples;
    this.onChange(samples);
  }
}

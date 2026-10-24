import { ActionConfig, LovelaceCardConfig, LovelaceCardEditor } from 'custom-card-helpers';

import type { MosDeviceKind, NameFilter, RowSort, SecondaryInfo } from './devices';

declare global {
  interface HTMLElementTagNameMap {
    'mos-card-editor': LovelaceCardEditor;
    'mos-overview-card-editor': LovelaceCardEditor;
  }
}

export interface MosCardConfig extends LovelaceCardConfig {
  type: string;

  /** Card heading. Omit for no heading. */
  title?: string;

  /**
   * Device id of the MOS server whose devices to show.
   *
   * Omit to show every MOS server Home Assistant knows about, grouped by
   * server. With a single server configured — the common case — omitting this
   * and setting it are equivalent.
   */
  server?: string;

  /**
   * Which device kinds to render, matched against the device's `model_id`.
   *
   * Defaults to all seven. Kinds with no devices render nothing, so the default
   * shows whatever the server actually has.
   */
  kinds?: MosDeviceKind[];

  /** Group rows under a heading per kind. Default true. */
  group_by_kind?: boolean;

  /**
   * Narrow the list by name. Default: everything the kinds allow.
   *
   * `include` and `exclude` each take a pattern or a list of them, matched
   * case-insensitively against the name shown on the row. `*` and `?` are
   * wildcards; a pattern with neither matches anywhere in the name, so
   * `arr` finds Sonarr and Radarr. `exclude` is applied last and wins.
   */
  filter?: NameFilter;

  /**
   * Cap how many rows each group lists. Default: no cap.
   *
   * The rest are folded behind a line that says how many there are and opens
   * them in place. A group is one kind on one server, and `group_by_kind` only
   * hides the heading rather than merging the groups — so the cap applies per
   * kind under both, and each kind folds and opens on its own.
   */
  max_rows?: number;

  /**
   * Lay each group out in one or two columns. Default 1.
   *
   * Two is the ceiling because Home Assistant gives a card about 500 px, which
   * is two readable rows across and wants `compact` with them. A card too
   * narrow for two falls back to one, so a dashboard that is wide on a desktop
   * and narrow on a phone needs no second card.
   */
  columns?: number;

  /** Draw shorter rows with smaller controls. Default false. */
  compact?: boolean;

  /**
   * The order rows are listed in within a group. Default `name`.
   *
   * `state` puts what is running first, then what is paused, then what is
   * stopped, alphabetically within each — the order that answers "what is up
   * right now" without reading every row. Kinds whose state says nothing about
   * running, disks and pools, stay alphabetical under both.
   */
  sort?: RowSort;

  /**
   * A measurement to show beside each row's state. Default `none`.
   *
   * `auto` picks per kind: CPU and memory for a container or a VM, the running
   * count of a Compose stack's containers, temperature for a disk, free space
   * for a pool, load for the UPS. `cpu` and `memory` ask for one specific
   * number and resolve to nothing on the kinds that have no such thing. A measurement the server cannot currently report is left out rather
   * than printed as unknown.
   */
  secondary_info?: SecondaryInfo;

  /**
   * Show what the MOS server itself reports under its name. Default false.
   *
   * Turning this on also shows the server heading for a single server, which
   * the card otherwise omits as noise — there would be nowhere to put the line.
   */
  show_server_summary?: boolean;

  /**
   * Draw the last hour of the server's CPU load and memory usage beside their
   * rings. Default false. Needs `show_server_summary` and the recorder.
   */
  show_history?: boolean;

  /** Show the server's SSH, Samba, NFS, Tailscale and NetBird status as chips. Default false. */
  show_services?: boolean;

  /** Show the state entity's icon or MOS template picture. Default true. */
  show_icon?: boolean;

  /** Show the state value on each row. Default true. */
  show_state?: boolean;

  /**
   * Show a link button for rows that have one — the container's `web_ui_url`,
   * falling back to the device's configuration URL. Default true.
   */
  show_link?: boolean;

  /** Show the start/stop switch on guest rows. Default true. */
  show_power?: boolean;

  /**
   * Ask before stopping a running guest. Default false.
   *
   * Only the stop direction asks. Starting something is cheap and undone by a
   * second click; stopping a VM someone is working in is neither, and the
   * button sits right next to the link button.
   */
  confirm_stop?: boolean;

  /**
   * Badge rows whose device reports a fault. Default true.
   *
   * A fault is whatever the integration marks with Home Assistant's `problem`
   * device class — a SMART warning on a disk, an unhealthy container, a
   * degraded pool, a UPS on bypass or overloaded. The badge sits on the row's
   * icon, so it needs `show_icon` as well.
   *
   * On by default because a failing disk outranks the waiting update that is
   * already badged by default. Turning it off is one key.
   */
  show_problem?: boolean;

  /**
   * Show a badge on rows whose device reports a waiting update. Default true.
   *
   * The badge sits on the row's icon, so it needs `show_icon` as well. Only
   * Docker containers and Compose stacks report updates at all.
   */
  show_update?: boolean;

  /**
   * Hide rows whose state is unavailable or unknown. Default false.
   *
   * Off by default on purpose: a device behind a failing MOS endpoint keeps its
   * registry entry and only reports unavailable, and that is worth seeing.
   */
  hide_unavailable?: boolean;

  /**
   * Action for a tap on the row body. Default `more-info` on the state entity.
   *
   * One config serves every row, so anywhere inside it a `[[key]]` placeholder
   * stands for the row that was tapped — `entity`, `power`, `device_id`, `name`
   * and `kind`. Text substitution only, nothing is evaluated.
   */
  tap_action?: ActionConfig;
  hold_action?: ActionConfig;
  double_tap_action?: ActionConfig;
}

/**
 * What a card tells the sections view about the space it wants.
 *
 * Declared here rather than imported: `custom-card-helpers` predates the
 * sections layout and types nothing for it, so this follows the frontend's own
 * shape. `'full'` spans the section's twelve columns and `'auto'` lets the card
 * take the height its content needs.
 */
export interface LovelaceGridOptions {
  columns?: number | 'full';
  rows?: number | 'auto';
  min_columns?: number;
  min_rows?: number;
  max_columns?: number;
  max_rows?: number;
}

/** The overview card: one MOS server condensed, with no row per device. */
export interface MosOverviewCardConfig extends LovelaceCardConfig {
  type: string;

  /** Card heading. Omit for none; the server's name heads each server anyway. */
  title?: string;

  /** Device id of the MOS server to show. Omit for every server, one after another. */
  server?: string;

  /** Draw the last hour of CPU load and memory beside their rings. Default true. */
  show_history?: boolean;

  /** One summary per guest kind: what runs, what waits on an update, CPU and memory. Default true. */
  show_guests?: boolean;

  /** The pools and a line for the disks. Default true. */
  show_storage?: boolean;

  /** The UPS: status, battery, runtime and load. Default true. */
  show_ups?: boolean;

  /** SSH, Samba, NFS, Tailscale and NetBird as chips. Default true. */
  show_services?: boolean;

  /**
   * Where a tap on a guest kind leads, for a dashboard with the full list.
   * `[[kind]]` is replaced with the kind's `model_id`. Omit for no tap.
   */
  navigation_path?: string;
}

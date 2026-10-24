/**
 * Registering the card's elements and its picker entry, tolerating a second copy.
 *
 * The bundle can reach a page twice: once from the integration, which ships it,
 * and once from a leftover dashboard resource of an older install. Lit's
 * `@customElement` calls `customElements.define` unconditionally, and a second
 * `define` for the same tag throws — which aborts the second bundle halfway
 * through its top level. Whichever copy loads first keeps the tag.
 *
 * The integration loads the bundle alongside Home Assistant's own entry point,
 * which installs `@webcomponents/scoped-custom-element-registry` and replaces
 * `window.customElements` with it. An element defined before that swap lands in
 * the native registry, which the replacement never consults, so the dashboard
 * reports it as missing. Defining only once Home Assistant's root element exists
 * puts the definition in whichever registry is in charge by then.
 *
 * The registries and the picker list are parameters so this runs without a DOM.
 */

/** The part of `CustomElementRegistry` registration needs. */
export type ElementRegistry = Pick<CustomElementRegistry, 'get' | 'define' | 'whenDefined'>;

/** Defined by Home Assistant's entry point right after it installs its registry. */
export const HOST_ELEMENT = 'home-assistant';

/** One entry in Home Assistant's card picker. */
export interface CustomCardEntry {
  type: string;
  name: string;
  description: string;
}

/** Define `tag` unless some copy already did; true if this call defined it. */
export function defineOnce(registry: ElementRegistry, tag: string, element: CustomElementConstructor): boolean {
  if (registry.get(tag)) {
    return false;
  }
  registry.define(tag, element);
  return true;
}

/**
 * Define `tag` once Home Assistant's root element is defined, on the registry
 * `currentRegistry` returns at that moment; true if this call defined it.
 */
export async function defineWhenHostReady(
  currentRegistry: () => ElementRegistry,
  tag: string,
  element: CustomElementConstructor,
): Promise<boolean> {
  await currentRegistry().whenDefined(HOST_ELEMENT);
  return defineOnce(currentRegistry(), tag, element);
}

/** Add `entry` to the picker list unless a card of the same type is listed. */
export function announceCard(list: CustomCardEntry[] | undefined, entry: CustomCardEntry): CustomCardEntry[] {
  const cards = list ?? [];
  if (!cards.some((card) => card.type === entry.type)) {
    cards.push(entry);
  }
  return cards;
}

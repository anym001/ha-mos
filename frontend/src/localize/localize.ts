import * as de from './languages/de.json';
import * as en from './languages/en.json';

// Same two languages the MOS integration ships, so the card and the integration
// speak with one voice. German follows the integration's own wording: Docker-
// Container, LXC-Container, VMs, Festplatten, Speicherpools, USV.
const languages: Record<string, Record<string, unknown>> = {
  de: de,
  en: en,
};

const FALLBACK_LANGUAGE = 'en';

/**
 * The language the card renders in, mirrored from `hass.locale.language`.
 *
 * Module level rather than per component: every card and editor in one frontend
 * shows the same `hass`, so there is one answer, and `localize` stays a plain
 * function that the pure config helpers can call without a `hass` to hand.
 */
let currentLanguage: string | undefined;

/**
 * Point the card's own strings at Home Assistant's language.
 *
 * `hass.locale.language` is the frontend's effective language and the only
 * source that is always right. The `selectedLanguage` key this used to read on
 * its own is written only once someone picks a language in their profile:
 * Home Assistant initialises it to `null`, so an instance running German by
 * browser detection left the card in English while the states beside it — which
 * come from `hass.formatEntityState` — were German. Reading `hass` first cannot
 * contradict an explicit choice, because Home Assistant writes that same value
 * into both places.
 */
export function setLanguage(language: string | undefined): void {
  currentLanguage = language || undefined;
}

/**
 * The dictionaries to try, most specific first.
 *
 * A regional code falls back to its base language — `de-DE` is German, and
 * dropping it on the floor because the card ships `de.json` and not `de_DE.json`
 * is the same bug as not looking at `hass` at all. English is the last resort,
 * which is also what a language the card does not ship resolves to.
 */
function candidatesFor(language: string | undefined): string[] {
  const normalized = (language ?? '').replace(/['"]+/g, '').replace('_', '-').toLowerCase();
  const base = normalized.split('-')[0];

  return [normalized, base, FALLBACK_LANGUAGE].filter(Boolean);
}

function storedLanguage(): string | undefined {
  // Guarded rather than read directly: this module is imported by the config
  // helpers, which are pure and are exercised outside a browser. Reaching for a
  // browser global at call time would make them untestable for no benefit.
  if (typeof localStorage === 'undefined') {
    return undefined;
  }

  // Home Assistant stores this as JSON, so an unset language arrives as the
  // string "null" rather than as an absent key. It needs no special case — no
  // dictionary is named that, so it resolves to English like any other unknown
  // language — but it is why this key alone cannot be trusted to say what
  // language the frontend is in.
  return localStorage.getItem('selectedLanguage')?.replace(/['"]+/g, '') || undefined;
}

function resolveTranslation(path: string, dictionary: Record<string, unknown>): string | undefined {
  const value = path.split('.').reduce<unknown>((acc, key) => {
    if (acc && typeof acc === 'object' && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }

    return undefined;
  }, dictionary);

  return typeof value === 'string' ? value : undefined;
}

export function localize(string: string, search = '', replace = ''): string {
  let translated: string | undefined;

  for (const candidate of candidatesFor(currentLanguage ?? storedLanguage())) {
    const dictionary = languages[candidate];

    if (dictionary) {
      translated = resolveTranslation(string, dictionary);
    }

    if (translated !== undefined) {
      break;
    }
  }

  if (translated === undefined) {
    translated = string;
  }

  if (search !== '') {
    // A function replacer rather than a string one: `String.replace` reads `$&`,
    // `$'` and friends in a string replacement as patterns, and the value here
    // is a device name someone else chose.
    translated = translated.replace(search, () => replace);
  }

  return translated;
}

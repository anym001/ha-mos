import { afterEach, describe, expect, it } from 'vitest';

import { localize, setLanguage } from '../src/localize/localize';

/**
 * The language the card renders in, and the one substitution it performs.
 *
 * Both are pure once `setLanguage` has been called, which is what the card does
 * from `hass.locale.language` on every `hass` change. The stored-language path
 * is exercised through a stub, because the module reads `localStorage` only
 * when it is defined — these tests run without a DOM.
 */

const withStoredLanguage = (value: string | null, run: () => void): void => {
  const store = { getItem: (key: string) => (key === 'selectedLanguage' ? value : null) };

  Object.defineProperty(globalThis, 'localStorage', { value: store, configurable: true, writable: true });

  try {
    run();
  } finally {
    Reflect.deleteProperty(globalThis, 'localStorage');
  }
};

afterEach(() => {
  setLanguage(undefined);
});

describe('language selection', () => {
  it('renders German when Home Assistant is in German', () => {
    setLanguage('de');

    expect(localize('kinds.docker_container')).toBe('Docker-Container');
  });

  it('renders English when Home Assistant is in English', () => {
    setLanguage('en');

    expect(localize('kinds.docker_container')).toBe('Docker containers');
  });

  it('falls back to the base language for a regional code', () => {
    setLanguage('de-DE');

    expect(localize('kinds.docker_container')).toBe('Docker-Container');
  });

  it('accepts the underscore spelling of a regional code', () => {
    setLanguage('de_DE');

    expect(localize('kinds.docker_container')).toBe('Docker-Container');
  });

  it('falls back to English for a language the card does not ship', () => {
    setLanguage('fr');

    expect(localize('kinds.docker_container')).toBe('Docker containers');
  });

  it('follows Home Assistant rather than the stored language', () => {
    withStoredLanguage('"en"', () => {
      setLanguage('de');

      expect(localize('kinds.docker_container')).toBe('Docker-Container');
    });
  });

  it('uses the stored language when Home Assistant has not been seen yet', () => {
    withStoredLanguage('"de"', () => {
      expect(localize('kinds.docker_container')).toBe('Docker-Container');
    });
  });

  it('treats the "null" Home Assistant stores for an unset language as unset', () => {
    withStoredLanguage('null', () => {
      expect(localize('kinds.docker_container')).toBe('Docker containers');
    });
  });

  it('falls back to English when nothing names a language at all', () => {
    expect(localize('kinds.docker_container')).toBe('Docker containers');
  });

  it('falls back to English for a key one language is missing', () => {
    setLanguage('de');

    expect(localize('common.made_up_key')).toBe('common.made_up_key');
  });
});

describe('substitution', () => {
  it('replaces the placeholder', () => {
    setLanguage('en');

    expect(localize('common.confirm_stop', '{name}', 'PushBits')).toBe('Stop PushBits?');
  });

  it('does not read a device name as a replacement pattern', () => {
    setLanguage('en');

    // `$&` in a string replacement means "the matched text" — here that would
    // put `{name}` back into the sentence it was meant to leave.
    expect(localize('common.confirm_stop', '{name}', 'Foo$&Bar')).toBe('Stop Foo$&Bar?');
    expect(localize('common.confirm_stop', '{name}', "A$'B")).toBe("Stop A$'B?");
  });

  it('substitutes an empty value rather than leaving the placeholder', () => {
    setLanguage('en');

    expect(localize('common.confirm_stop', '{name}', '')).toBe('Stop ?');
  });

  it('leaves the string alone when nothing is to be replaced', () => {
    setLanguage('en');

    expect(localize('common.loading')).toBe(localize('common.loading'));
    expect(localize('common.loading')).not.toContain('{');
  });
});

/**
 * Name filtering.
 *
 * The one place the card matches on a name, so it is worth pinning down what
 * "matches" means — particularly the two decisions a user would otherwise have
 * to discover by trial: a pattern without a wildcard is a substring, and
 * `exclude` beats `include`.
 */
import { describe, expect, it } from 'vitest';

import { matchesPattern, passesFilter } from '../src/devices';

describe('matchesPattern', () => {
  it.each([
    ['Sonarr', 'arr'],
    ['Radarr', 'arr'],
    ['Sonarr', 'Sonarr'],
    ['FileBrowser', 'browse'],
  ])('matches %s against the bare word %s anywhere in the name', (name, pattern) => {
    expect(matchesPattern(name, pattern)).toBe(true);
  });

  it.each([
    ['Sonarr', '*arr', true],
    ['Sonarr', 'son*', true],
    ['Sonarr', 'arr*', false],
    ['Sonarr', '*o*a*', true],
    ['test-1', 'test-?', true],
    ['test-12', 'test-?', false],
    ['x', '*', true],
    ['', '*', true],
  ])('anchors %s against the glob %s', (name, pattern, expected) => {
    expect(matchesPattern(name, pattern)).toBe(expected);
  });

  it.each([
    ['SONARR', '*arr'],
    ['sonarr', '*ARR'],
    ['PushBits', 'pushbits'],
  ])('ignores case comparing %s with %s', (name, pattern) => {
    expect(matchesPattern(name, pattern)).toBe(true);
  });

  it('treats a dot as a dot rather than as a regex wildcard', () => {
    expect(matchesPattern('a.b', 'a.b')).toBe(true);
    expect(matchesPattern('axb', 'a.b')).toBe(false);
    expect(matchesPattern('axb', 'a.*')).toBe(false);
    expect(matchesPattern('a.something', 'a.*')).toBe(true);
  });

  it('survives a name full of regex metacharacters', () => {
    expect(matchesPattern('C++ (build)', 'c++ (build)')).toBe(true);
    expect(matchesPattern('C++ (build)', 'c++*')).toBe(true);
    expect(() => matchesPattern('anything', '[')).not.toThrow();
    expect(matchesPattern('a[b', 'a[*')).toBe(true);
  });
});

describe('passesFilter', () => {
  it('lets everything through without a filter', () => {
    expect(passesFilter('anything', undefined)).toBe(true);
    expect(passesFilter('anything', {})).toBe(true);
  });

  it('keeps only what include names', () => {
    expect(passesFilter('Sonarr', { include: ['*arr'] })).toBe(true);
    expect(passesFilter('Plex', { include: ['*arr'] })).toBe(false);
  });

  it('accepts a bare string as well as a list', () => {
    expect(passesFilter('Sonarr', { include: 'arr' })).toBe(true);
    expect(passesFilter('Plex', { include: 'arr' })).toBe(false);
  });

  it('lets everything through when include is present but empty', () => {
    expect(passesFilter('Plex', { include: [] })).toBe(true);
    expect(passesFilter('Plex', { include: '  ' })).toBe(true);
  });

  it('applies exclude last, so it wins over include', () => {
    const filter = { include: ['*arr'], exclude: ['sonarr'] };

    expect(passesFilter('Radarr', filter)).toBe(true);
    expect(passesFilter('Sonarr', filter)).toBe(false);
  });

  it('excludes without needing include to name everything kept', () => {
    expect(passesFilter('anything', { exclude: ['test'] })).toBe(true);
    expect(passesFilter('a test box', { exclude: ['test'] })).toBe(false);
  });

  it('ignores blank patterns and surrounding whitespace', () => {
    expect(passesFilter('Sonarr', { include: [' *arr ', ''] })).toBe(true);
  });

  it('matches any one of several include patterns', () => {
    const filter = { include: ['*arr', 'plex'] };

    expect(passesFilter('Plex', filter)).toBe(true);
    expect(passesFilter('Radarr', filter)).toBe(true);
    expect(passesFilter('Homepage', filter)).toBe(false);
  });
});

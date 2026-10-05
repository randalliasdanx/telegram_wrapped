/**
 * localStorage wrappers that never throw (private mode, disabled storage, SSR).
 */

export const SESSION_KEY = "tw_session";
export const GUESS_KEY = "tw_archetype_guess";

export function storageGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function storageSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export function storageRemove(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

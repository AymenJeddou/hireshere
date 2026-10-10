// Light profile kept in this browser only. Boards use it as their default filters.
export interface Profile {
  country: string;
  f: string;
  s: string;
  e: string;
  langs: string[];
}
const KEY = "hh_profile";

export function loadProfile(): Profile | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Profile) : null;
  } catch {
    return null;
  }
}

export function saveProfile(p: Profile): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    // Storage blocked: the profile simply is not remembered.
  }
}

export function clearProfile(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Nothing to clear.
  }
}

/** A job fits the languages someone works in when every required language is one of them. */
export function languagesFit(required: string[], spoken: string[]): boolean {
  return !spoken.length || required.every((l) => spoken.includes(l));
}

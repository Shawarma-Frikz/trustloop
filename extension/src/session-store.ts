import { createPageSalt } from "./adapters/amazon.js";

/** Per-document memory only. Review text and fingerprints are never persisted. */
export class PageSessionStore {
  readonly salt = createPageSalt();
  private readonly seen = new Set<string>();

  markSeen(reviewKey: string): boolean {
    if (this.seen.has(reviewKey)) return false;
    this.seen.add(reviewKey);
    return true;
  }

  get size(): number {
    return this.seen.size;
  }
}

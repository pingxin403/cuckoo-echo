import { createStore, get, set, del, keys, entries } from 'idb-keyval';
import type { CacheConfig, CachedThread, ThreadMeta, Message } from '@/types';

// Custom idb-keyval store with dedicated database
const cacheStore = createStore('cuckoo-echo-cache', 'threads');

// Default cache configuration
const defaultConfig: CacheConfig = {
  maxSizeBytes: 10 * 1024 * 1024, // 10MB
  maxMessages: 50,
  maxThreads: 20,
  ttlDays: 7,
};

let config: CacheConfig = { ...defaultConfig };

/** Override default cache config (useful for testing) */
export function setCacheConfig(overrides: Partial<CacheConfig>): void {
  config = { ...defaultConfig, ...overrides };
}

/** Get current cache config */
export function getCacheConfig(): CacheConfig {
  return { ...config };
}

/** Save a thread's metadata and messages to the cache */
export async function saveThread(
  threadId: string,
  meta: ThreadMeta,
  messages: Message[],
): Promise<void> {
  // Trim messages to the most recent maxMessages
  const trimmed = messages.slice(-config.maxMessages);
  const serialized = JSON.stringify({ meta, messages: trimmed });
  const sizeBytes = serialized.length;

  const cached: CachedThread = {
    id: threadId,
    meta,
    messages: trimmed,
    cachedAt: Date.now(),
    sizeBytes,
  };

  await set(threadId, cached, cacheStore);
  await evictIfNeeded();
}

/** Load a cached thread, returning null if missing or expired */
export async function loadThread(
  threadId: string,
): Promise<CachedThread | null> {
  const cached = await get<CachedThread>(threadId, cacheStore);
  if (!cached) return null;

  // Check TTL
  const ttlMs = config.ttlDays * 24 * 60 * 60 * 1000;
  if (cached.cachedAt + ttlMs < Date.now()) {
    await del(threadId, cacheStore);
    return null;
  }

  return cached;
}

/** Evict oldest threads until total size is within maxSizeBytes */
export async function evictIfNeeded(): Promise<void> {
  const allEntries = await entries<string, CachedThread>(cacheStore);
  let totalSize = allEntries.reduce(
    (sum, [, thread]) => sum + thread.sizeBytes,
    0,
  );

  if (totalSize <= config.maxSizeBytes) return;

  // Sort by cachedAt ascending (oldest first)
  const sorted = [...allEntries].sort(
    (a, b) => a[1].cachedAt - b[1].cachedAt,
  );

  for (const [key, thread] of sorted) {
    if (totalSize <= config.maxSizeBytes) break;
    await del(key, cacheStore);
    totalSize -= thread.sizeBytes;
  }
}

/** Remove all entries whose TTL has expired */
export async function clearExpired(): Promise<void> {
  const ttlMs = config.ttlDays * 24 * 60 * 60 * 1000;
  const now = Date.now();
  const allEntries = await entries<string, CachedThread>(cacheStore);

  for (const [key, thread] of allEntries) {
    if (thread.cachedAt + ttlMs < now) {
      await del(key, cacheStore);
    }
  }
}

/** List all cached thread keys */
export async function listCachedThreadIds(): Promise<string[]> {
  return (await keys<string>(cacheStore)) as string[];
}

/** Delete a specific cached thread */
export async function deleteThread(threadId: string): Promise<void> {
  await del(threadId, cacheStore);
}

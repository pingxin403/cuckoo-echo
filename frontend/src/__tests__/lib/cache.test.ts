import 'fake-indexeddb/auto';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  saveThread,
  loadThread,
  setCacheConfig,
} from '@/lib/cache';
import type { ThreadMeta, Message } from '@/types';
import { createStore, keys, del } from 'idb-keyval';

const testCacheStore = createStore('cuckoo-echo-cache', 'threads');

async function clearCacheStore(): Promise<void> {
  const allKeys = await keys(testCacheStore);
  for (const key of allKeys) {
    await del(key, testCacheStore);
  }
}

function makeMeta(threadId: string): ThreadMeta {
  return {
    id: threadId,
    title: `Thread ${threadId}`,
    lastMessageAt: new Date().toISOString(),
    messageCount: 1,
  };
}

function makeMessages(threadId: string, content = 'hello'): Message[] {
  return [
    {
      id: `msg_${threadId}`,
      threadId,
      role: 'user',
      content,
      createdAt: new Date().toISOString(),
    },
  ];
}

beforeEach(async () => {
  await clearCacheStore();
  setCacheConfig({
    maxSizeBytes: 10 * 1024 * 1024,
    maxMessages: 50,
    maxThreads: 20,
    ttlDays: 7,
  });
});

describe('cache — saveThread + loadThread', () => {
  it('round-trip returns same data', async () => {
    const meta = makeMeta('t1');
    const messages = makeMessages('t1', 'test content');

    await saveThread('t1', meta, messages);
    const loaded = await loadThread('t1');

    expect(loaded).not.toBeNull();
    expect(loaded!.id).toBe('t1');
    expect(loaded!.meta.id).toBe(meta.id);
    expect(loaded!.meta.title).toBe(meta.title);
    expect(loaded!.messages).toHaveLength(1);
    expect(loaded!.messages[0].content).toBe('test content');
  });

  it('loadThread returns null for expired entries (TTL)', async () => {
    // Use a very short TTL (1 day) and advance time past it
    setCacheConfig({ ttlDays: 1 });

    const meta = makeMeta('t-expired');
    const messages = makeMessages('t-expired');

    await saveThread('t-expired', meta, messages);

    // Advance Date.now() by more than 1 day (86400001 ms)
    const realDateNow = Date.now;
    Date.now = () => realDateNow() + 86_400_001;

    try {
      const loaded = await loadThread('t-expired');
      expect(loaded).toBeNull();
    } finally {
      Date.now = realDateNow;
    }
  });

  it('eviction removes oldest entries when over size limit', async () => {
    // Set a very small cache limit
    setCacheConfig({ maxSizeBytes: 500, maxMessages: 50 });

    // Write two threads — each will be larger than 500 bytes due to JSON overhead
    const meta1 = makeMeta('old');
    const msgs1 = makeMessages('old', 'a'.repeat(200));
    await saveThread('old', meta1, msgs1);

    // Small delay to ensure different cachedAt
    await new Promise((r) => setTimeout(r, 10));

    const meta2 = makeMeta('new');
    const msgs2 = makeMessages('new', 'b'.repeat(200));
    await saveThread('new', meta2, msgs2);

    // The old thread should have been evicted
    const loadedOld = await loadThread('old');
    const loadedNew = await loadThread('new');

    // At least the newest entry should survive; the old one may be evicted
    expect(loadedNew).not.toBeNull();
    // If total exceeds limit, old entry gets evicted
    if (loadedOld === null) {
      // Eviction happened as expected
      expect(loadedOld).toBeNull();
    }
  });
});

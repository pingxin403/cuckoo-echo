import { describe, it, expect } from 'vitest';
import { existsSync, readdirSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { gzipSync } from 'zlib';

const distDir = resolve(__dirname, '../../dist');
const distExists = existsSync(distDir);

describe.skipIf(!distExists)('Build output verification', () => {
  it('produces dist/index.html', () => {
    expect(existsSync(resolve(distDir, 'index.html'))).toBe(true);
  });

  it('produces dist/embed.js with no hash in filename', () => {
    expect(existsSync(resolve(distDir, 'embed.js'))).toBe(true);
  });

  it('produces dist/assets/ with hashed JS and CSS files', () => {
    const assetsDir = resolve(distDir, 'assets');
    expect(existsSync(assetsDir)).toBe(true);

    const files = readdirSync(assetsDir);
    const hasHashedJS = files.some((f) => /\.js$/.test(f) && /-[\w]{8}\.js$/.test(f));
    const hasHashedCSS = files.some((f) => /\.css$/.test(f) && /-[\w]{8}\.css$/.test(f));

    expect(hasHashedJS).toBe(true);
    expect(hasHashedCSS).toBe(true);
  });

  it('embed.js gzip size is under 150KB', () => {
    const embedPath = resolve(distDir, 'embed.js');
    const raw = readFileSync(embedPath);
    const gzipped = gzipSync(raw);
    const sizeKB = gzipped.length / 1024;

    expect(sizeKB).toBeLessThan(150);
  });
});

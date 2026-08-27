import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../showcase/index.html', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../showcase/showcase.css', import.meta.url), 'utf8');
const js = fs.readFileSync(new URL('../showcase/showcase.js', import.meta.url), 'utf8');

test('showcase exposes only the selected presentation rooms', () => {
  for (const room of ['sanctuary', 'crossroads', 'write', 'music', 'images', 'explore', 'video']) {
    assert.match(html, new RegExp(`data-room="${room}"`));
  }
  assert.doesNotMatch(html, /data-room="(?:work|control|import|settings|modules|new-idea)"/);
  assert.match(html, /SHOWCASE MODE/);
  assert.match(html, /VIEW ONLY/);
  assert.match(html, /showcase-icon\.svg/);
  assert.doesNotMatch(html, /<form\b|<input\b|<textarea\b|<select\b/);
  assert.doesNotMatch(js, /fetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|document\.cookie/);
});

test('showcase navigation and accessibility remain lightweight', () => {
  assert.match(js, /closest\('\[data-open\]'\)/);
  assert.match(js, /event\.key === 'Escape'/);
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /button:focus-visible/);
  assert.match(css, /@media\(max-width:720px\)/);
  assert.doesNotMatch(css, /backdrop-filter|url\(https?:/);
});

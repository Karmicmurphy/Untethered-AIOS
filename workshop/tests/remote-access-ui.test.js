import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../app/index.html', import.meta.url), 'utf8');
const client = fs.readFileSync(new URL('../app/assets/remote-access.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../app/assets/remote-access.css', import.meta.url), 'utf8');

test('remote roles are projected from the origin session, never browser role input', () => {
  assert.match(html, /assets\/remote-access\.js/);
  assert.match(client, /request\('\/api\/session'\)/);
  assert.doesNotMatch(client, /URLSearchParams[\s\S]*role|localStorage[\s\S]*role/);
});

test('Visitor Bench exposes only bounded Write and Music guest submission', () => {
  assert.match(client, /new Set\(\['sanctuary','crossroads','write','music','work'\]\)/);
  assert.match(client, /\/api\/visitor-bench\/submissions/);
  assert.match(client, /Saved as an inactive Visitor’s Bench draft/);
  assert.match(client, /Copy into owner My Work/);
});

test('remote interface remains mobile bounded and does not expose old Worker URL settings', () => {
  assert.match(css, /@media\(max-width:500px\)/);
  assert.doesNotMatch(html, /id="cloudflareUrl"|id="saveCloudflare"/);
  assert.match(html, /origin-side Access JWT validation/);
});

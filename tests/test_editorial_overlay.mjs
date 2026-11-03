import test from 'node:test';
import assert from 'node:assert/strict';
import {
  citationWindow, evidenceDeskLayout, isDeskMaterial, markerDraw, springTowardOne, steppedElementFrame,
} from '../assets/editorial-overlay/timing.ts';

test('marker appears at full opacity while the stroke is still undrawn', () => {
  const held = markerDraw(0, 24, 12);
  assert.equal(held.opacity, 1);
  assert.equal(held.draw, 0);
  assert.equal(markerDraw(1, 24, 12).draw, held.draw);
  assert.deepEqual(markerDraw(1, 24, 12), held);
  assert.ok(markerDraw(2, 24, 12).draw > held.draw);
});

test('before the word the mark is absent, and a late frame has finished the stroke', () => {
  assert.deepEqual(markerDraw(-1, 24), {opacity: 0, draw: 0, scale: 1});
  const late = markerDraw(48, 24, 12);
  assert.equal(late.opacity, 1);
  assert.ok(late.draw > 0.999);
  assert.ok(Math.abs(late.scale - 1) < 0.02);
  assert.ok(Math.abs(springTowardOne(48, 24) - 1) < 0.02);
});

test('element frames hold for two camera frames and reject a finer clock', () => {
  assert.equal(steppedElementFrame(0, 24, 12), 0);
  assert.equal(steppedElementFrame(1, 24, 12), 0);
  assert.equal(steppedElementFrame(2, 24, 12), 2);
  assert.equal(steppedElementFrame(3, 24, 12), 2);
  assert.throws(() => steppedElementFrame(0, 24, 30));
  assert.throws(() => markerDraw(0, 0));
});

test('a citation starts on the spoken word', () => {
  const words = [{id: 'era', start: 1.2, end: 1.8}];
  assert.deepEqual(citationWindow(words, 'era', 3), {start: 1.2, end: 4.2});
  assert.throws(() => citationWindow(words, 'missing', 1));
});

test('the desk offsets the red stroke and refuses the painting as a material', () => {
  const layout = evidenceDeskLayout(1080, 1920);
  assert.ok(layout.marker.x < layout.cutout.x);
  assert.ok(layout.marker.y > layout.cutout.y);
  assert.ok(layout.occlusion.y + layout.occlusion.height < 1920);
  assert.equal(isDeskMaterial('document'), true);
  assert.equal(isDeskMaterial('painting'), false);
  assert.throws(() => evidenceDeskLayout(0, 1920));
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {longScrollLayout} from '../assets/long-scroll/layout.ts';

const base = {sourceWidth: 1000, sourceHeight: 200, viewportWidth: 400,
  viewportHeight: 160, durationInFrames: 121};

test('reveals right, middle, then left without uncovered viewport pixels', () => {
  assert.equal(longScrollLayout({...base, frame: 0}).left, -400);
  assert.ok(Math.abs(longScrollLayout({...base, frame: 60}).left + 200) < 1e-9);
  assert.ok(longScrollLayout({...base, frame: 120}).left === 0);
  let previous = -Infinity;
  for (let frame = 0; frame < 121; frame++) {
    const g = longScrollLayout({...base, frame});
    assert.ok(g.left >= previous);
    assert.ok(g.left <= 0 && g.left + g.width >= base.viewportWidth);
    assert.equal(g.width / g.height, base.sourceWidth / base.sourceHeight);
    previous = g.left;
  }
});

test('reverse direction, premount and held tail keep the correct endpoints', () => {
  assert.equal(longScrollLayout({...base, frame: -24}).left, -400);
  assert.ok(longScrollLayout({...base, frame: 200}).left === 0);
  assert.ok(longScrollLayout({...base, frame: 0, direction: 'left-to-right'}).left === 0);
  assert.equal(longScrollLayout({...base, frame: 120, direction: 'left-to-right'}).left, -400);
});

test('rejects dimensions that would leave gaps or produce an invalid camera', () => {
  for (const patch of [{sourceHeight: 0}, {sourceWidth: 100}, {frame: NaN},
    {durationInFrames: 1}, {durationInFrames: 2.5}, {viewportWidth: Infinity}, {direction: 'up'}]) {
    assert.throws(() => longScrollLayout({...base, frame: 0, ...patch}));
  }
});

export type ScrollDirection = 'right-to-left' | 'left-to-right';

export function longScrollLayout({
  sourceWidth, sourceHeight, viewportWidth, viewportHeight,
  frame, durationInFrames, direction = 'right-to-left',
}: {
  sourceWidth: number; sourceHeight: number;
  viewportWidth: number; viewportHeight: number;
  frame: number; durationInFrames: number; direction?: ScrollDirection;
}) {
  for (const n of [sourceWidth, sourceHeight, viewportWidth, viewportHeight]) {
    if (!Number.isFinite(n) || n <= 0) throw new Error('Image and viewport dimensions must be positive');
  }
  if (!Number.isFinite(frame) || !Number.isInteger(durationInFrames) || durationInFrames < 2) {
    throw new Error('Use a finite local frame and at least two integer frames');
  }
  if (direction !== 'right-to-left' && direction !== 'left-to-right') throw new Error('Invalid direction');
  const height = viewportHeight;
  const width = sourceWidth * height / sourceHeight;
  const travel = width - viewportWidth;
  if (!Number.isFinite(width) || travel < 0) throw new Error('Source must fill the viewport at uniform height scale');
  const progress = Math.max(0, Math.min(1, frame / (durationInFrames - 1)));
  const eased = (1 - Math.cos(Math.PI * progress)) / 2;
  const left = direction === 'right-to-left' ? -travel * (1 - eased) : -travel * eased;
  return {left, width, height};
}

import React from 'react';
import {Img, useCurrentFrame} from 'remotion';
import {longScrollLayout, type ScrollDirection} from './layout';

export type LongScrollPanProps = {
  src: string;
  sourceWidth: number;
  sourceHeight: number;
  viewport: {left: number; top: number; width: number; height: number};
  durationInFrames: number;
  direction?: ScrollDirection;
};

/** Original-image camera movement only. Supply a resolved URL and verified pixels.
 * Place inside a Sequence; keep captions, chapter bars and source labels outside.
 */
export const LongScrollPan: React.FC<LongScrollPanProps> = ({
  src, sourceWidth, sourceHeight, viewport, durationInFrames, direction,
}) => {
  const frame = useCurrentFrame();
  if (!Number.isFinite(viewport.left) || !Number.isFinite(viewport.top)) {
    throw new Error('Viewport position must be finite');
  }
  const image = longScrollLayout({
    sourceWidth, sourceHeight, viewportWidth: viewport.width,
    viewportHeight: viewport.height, frame, durationInFrames, direction,
  });
  return <div style={{position: 'absolute', ...viewport, overflow: 'hidden'}}>
    <Img src={src} style={{position: 'absolute', ...image, top: 0, maxWidth: 'none'}} />
  </div>;
};

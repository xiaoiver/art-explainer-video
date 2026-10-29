import React from 'react';

export type Chapter = {
  id: string;
  label: string;
  start: number;
  end: number;
};

// Seconds use the same Math.round(seconds * fps) boundaries as the picture edit.
// End frames are exclusive. Never derive state from a Sequence-local frame.
export function activeChapterAtFrame(
  chapters: readonly Chapter[], frame: number, fps: number,
): number {
  if (!Number.isFinite(frame) || !Number.isFinite(fps) || fps <= 0) {
    throw new Error('frame must be finite and fps must be positive');
  }
  return chapters.findIndex(c =>
    frame >= Math.round(c.start * fps) && frame < Math.round(c.end * fps));
}

type Props = {
  chapters: readonly Chapter[];
  frame: number;
  fps: number;
  canvasWidth?: number;
  canvasHeight?: number;
  top?: number;
  side?: number;
  gap?: number;
  fontSize?: number;
  fontFamily?: string;
  activeColor?: string;
  mutedColor?: string;
  activeLineColor?: string;
  mutedLineColor?: string;
  inactiveOpacity?: number;
};

/** A persistent chapter strip, independent of shot opacity and camera motion.
 * Geometry below is based on a 1080x1920 portrait canvas; all overrides are px.
 * Landscape layouts should explicitly set top, side, fontSize and gap.
 */
export const ChapterNavigation: React.FC<Props> = ({
  chapters, frame, fps, canvasWidth = 1080, canvasHeight = 1920,
  top = canvasHeight * 139 / 1920,
  side = canvasWidth * 68 / 1080,
  gap = canvasWidth * 23.5 / 1080,
  fontSize = canvasWidth * 24 / 1080,
  fontFamily = '"Songti SC", "STSong", serif',
  activeColor = '#EEE8D5', mutedColor = '#B5B59E',
  activeLineColor = '#B6A77F', mutedLineColor = '#59604F',
  inactiveOpacity = 0.36,
}) => {
  if (chapters.length === 0) return null;
  const active = activeChapterAtFrame(chapters, frame, fps);
  return <div style={{
    position: 'absolute', top, left: side, right: side,
    display: 'grid', gridTemplateColumns: `repeat(${chapters.length}, minmax(0, 1fr))`,
    gap, fontFamily, fontSize, lineHeight: 1.4, pointerEvents: 'none', zIndex: 20,
  }}>
    {chapters.map((chapter, i) => <div key={chapter.id} style={{
      minWidth: 0, whiteSpace: 'nowrap',
      opacity: active === i ? 1 : inactiveOpacity,
      color: active === i ? activeColor : mutedColor,
      borderTop: `1px solid ${active === i ? activeLineColor : mutedLineColor}`,
      paddingTop: fontSize / 2,
    }}>{i + 1}　{chapter.label}</div>)}
  </div>;
};

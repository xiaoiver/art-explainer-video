import React from 'react';
import {isAnnotationKind, markerDraw, type AnnotationKind} from './timing';

type Props = {
  text: string;
  kind: AnnotationKind;
  /** Frames relative to the spoken word. Negative frames render nothing. */
  frame: number;
  fps: number;
  elementFps?: number;
  color?: string;
  fontFamily?: string;
  fontSize?: number;
};

/** Hand-drawn citation mark. Seed stays fixed so the stroke does not shimmer.
 * Copy into an existing Remotion project. Pass the composition frame minus the
 * word's start frame. To use @remotion/rough-notation instead, see the craft note.
 */
export const CitationMark: React.FC<Props> = ({
  text, kind, frame, fps, elementFps = 12,
  color = '#c23b32',
  fontFamily = '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", sans-serif',
  fontSize = 42,
}) => {
  if (!isAnnotationKind(kind)) throw new Error('unsupported citation mark');
  if (!text.trim()) throw new Error('citation text is empty');
  const mark = markerDraw(frame, fps, elementFps);
  if (mark.opacity === 0) return null;
  const stroke = {
    fill: 'none' as const,
    stroke: color,
    strokeWidth: kind === 'highlight' ? 0 : 3,
    strokeLinecap: 'round' as const,
    pathLength: 1,
    strokeDasharray: 1,
    strokeDashoffset: 1 - mark.draw,
  };
  return <span style={{
    position: 'relative', display: 'inline-block', color: '#1c1915',
    fontFamily, fontSize, lineHeight: 1.25, whiteSpace: 'nowrap',
  }}>
    {kind === 'highlight' ? <span aria-hidden style={{
      position: 'absolute', left: '-0.08em', top: '0.12em', bottom: '0.08em',
      width: `${mark.draw * 100}%`, background: 'rgba(218, 196, 70, 0.72)',
      transform: `scaleY(${mark.scale})`, transformOrigin: '0 50%', zIndex: 0,
    }} /> : null}
    <span style={{position: 'relative', zIndex: 1}}>{text}</span>
    {kind === 'highlight' ? null : <svg aria-hidden viewBox="0 0 100 36" style={{
      position: 'absolute', inset: kind === 'underline' ? 'auto -4% -18% -4%' : '-16% -8%',
      width: kind === 'underline' ? '108%' : '116%',
      height: kind === 'underline' ? '42%' : '132%',
      overflow: 'visible', pointerEvents: 'none',
      transform: `scale(${mark.scale})`, transformOrigin: '0 50%',
    }}>
      {kind === 'underline' ? <path {...stroke} d="M4 20 Q 50 28 96 16" /> : null}
      {kind === 'circle' ? <path {...stroke} d="M18 8 C 4 10 6 30 22 32 C 70 36 98 24 90 10 C 78 2 28 2 18 8" /> : null}
      {kind === 'bracket' ? <>
        <path {...stroke} d="M16 4 H 8 V 32 H 16" />
        <path {...stroke} d="M84 4 H 92 V 32 H 84" />
      </> : null}
    </svg>}
  </span>;
};

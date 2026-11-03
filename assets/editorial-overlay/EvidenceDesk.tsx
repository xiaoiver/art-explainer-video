import React from 'react';
import {evidenceDeskLayout, isDeskMaterial, markerDraw, type DeskMaterial} from './timing';

type Props = {
  material: DeskMaterial;
  /** Local frame. The scan is fully visible at frame 0; only the red stroke draws on. */
  frame: number;
  fps: number;
  width: number;
  height: number;
  cutoutSrc: string;
  label: string;
  deskSrc?: string;
  occlusionSrc?: string;
  elementFps?: number;
  halftone?: boolean;
};

const PAPER = '#efe6d6';
const MARKER = '#c23b32';

/** Three slots for a map, letter, photo or document. Do not pass the painting. */
export const EvidenceDesk: React.FC<Props> = ({
  material, frame, fps, width, height, cutoutSrc, label,
  deskSrc, occlusionSrc, elementFps = 12, halftone = true,
}) => {
  if (!isDeskMaterial(material)) {
    throw new Error('evidence desk accepts a map, letter, photo or document');
  }
  if (!cutoutSrc.trim() || !label.trim()) throw new Error('desk needs a scan and a label');
  if (frame < 0) return null;
  const boxes = evidenceDeskLayout(width, height);
  const mark = markerDraw(frame, fps, elementFps);
  const box = (slot: {x: number; y: number; width: number; height: number}): React.CSSProperties => ({
    position: 'absolute', left: slot.x, top: slot.y, width: slot.width, height: slot.height,
  });
  return <div style={{position: 'absolute', inset: 0, background: PAPER, overflow: 'hidden'}}>
    <div style={{...box(boxes.desk), background: deskSrc ? undefined : PAPER, zIndex: 0}}>
      {deskSrc ? <img alt="" src={deskSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
    </div>
    <div aria-hidden style={{
      ...box(boxes.marker), zIndex: 1, border: `3px solid ${MARKER}`, borderRadius: 2,
      transform: 'rotate(-0.4deg)', clipPath: `inset(0 ${(1 - mark.draw) * 100}% 0 0)`,
    }} />
    <div style={{...box(boxes.cutout), zIndex: 2, background: '#f7f1e6', overflow: 'hidden'}}>
      <img alt={label} src={cutoutSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      {halftone ? <div style={{
        position: 'absolute', inset: 0, mixBlendMode: 'multiply', opacity: 0.28,
        backgroundImage: 'radial-gradient(circle, rgba(28,22,16,0.85) 0.55px, transparent 0.7px)',
        backgroundSize: '4px 4px',
      }} /> : null}
    </div>
    <div style={{...box(boxes.occlusion), zIndex: 3, overflow: 'hidden'}}>
      {occlusionSrc
        ? <img alt="" src={occlusionSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        : <div style={{
          width: '100%', height: '100%', background: '#f6f0e4',
          clipPath: 'polygon(22% 0, 100% 0, 100% 100%, 0 100%)',
          boxShadow: '0 10px 18px rgba(40, 30, 20, 0.16)',
        }} />}
    </div>
    <div style={{
      position: 'absolute', left: boxes.cutout.x, top: Math.max(8, boxes.cutout.y - height * 0.055),
      zIndex: 4, color: '#1c1915',
      fontFamily: '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", sans-serif',
      fontSize: Math.max(18, width * 0.028), letterSpacing: 0.4,
    }}>{label}</div>
  </div>;
};

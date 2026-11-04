import React from 'react';
import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame} from 'remotion';

// Two-second environment check, not an episode design or an artwork example.
const Check = ({totalFrames}: {totalFrames: number}) => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, Math.max(1, totalFrames - 1)], [20, 252]);
  return <AbsoluteFill style={{backgroundColor: '#DFD1B8'}}>
    <div style={{position: 'absolute', top: 64, left: x, width: 48, height: 48,
      backgroundColor: '#783D32'}} />
  </AbsoluteFill>;
};

registerRoot(() => <Composition id="RenderCheck" component={Check}
  width={320} height={180} fps={24} durationInFrames={48}
  defaultProps={{totalFrames: 48}}
  calculateMetadata={({props}) => ({durationInFrames: props.totalFrames})} />);

import React from 'react';
import {AbsoluteFill,Audio,Composition,OffthreadVideo,registerRoot,staticFile,useCurrentFrame,spring,interpolate,delayRender,continueRender,cancelRender} from 'remotion';
// Art direction: an intimate charcoal miniature theatre; gilded oil portraits misbehave,
// then collect above a warm serif wordmark. All animation is driven by frame number.
type Tile={src:string;width:number;height:number;subjectHeight:number};
type Props={tiles:Tile[];short?:boolean;audio?:boolean};
const clamp={extrapolateLeft:'clamp' as const,extrapolateRight:'clamp' as const};
const ease=(x:number)=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x)};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const Stage:React.FC=()=> <AbsoluteFill style={{backgroundColor:'#171611',backgroundImage:'radial-gradient(ellipse at 50% 42%,rgba(155,119,65,.17),transparent 69%),linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.27))'}}><svg width="1920" height="1080" style={{position:'absolute',opacity:.12}}><path d="M160 948 H1760" stroke="#9C7E4E" strokeWidth="1"/><path d="M160 960 H1760" stroke="#5B482F" strokeWidth="1"/></svg></AbsoluteFill>;
const Portrait:React.FC<{tile:Tile;index:number;short:boolean}>=({tile,index,short})=>{
 const f=useCurrentFrame(),entry=[0,18,34][index],progress=spring({fps:24,frame:Math.max(0,f-entry),config:{damping:15,stiffness:260,mass:.58}});
 const gathering=short?1:ease((f-(45+[0,1,8][index]))/19);
 const desiredH=short?310:mix(670,310,gathering),sc=desiredH/tile.subjectHeight;
 const bigX=index===0?mix(620,430,ease((f-11)/15)):index===1?960:1490;
 let x=short?[690,960,1230][index]:mix(bigX,[690,960,1230][index],gathering);
 let y=short?315:mix(530,315,gathering);
 let angle=0;
 if(short){y+=interpolate(f,[0,8],[14,0],clamp);angle=interpolate(f,[0,8],[index===0?-1.2:index===2?1.2:0,0],clamp);}
 else{
  if(index===0){y+=mix(-340,0,progress);angle=mix(-6,0,progress);}
  if(index===1){y+=mix(650,0,progress);angle=mix(5,0,progress);}
  if(index===2){x+=mix(740,0,progress);angle=mix(-7,0,progress);if(f>67&&f<80)angle+=Math.sin((f-67)/13*Math.PI*2)*2.1;}
 }
 const opacity=short?1:index===0?interpolate(f,[0,3],[.7,1],clamp):f<entry?0:interpolate(f,[entry,entry+3],[0,1],clamp);
 return <div style={{position:'absolute',left:x-tile.width*sc/2,top:y-tile.height*sc/2,width:tile.width*sc,height:tile.height*sc,transform:`rotate(${angle}deg)`,transformOrigin:'50% 50%',opacity}}>
  <OffthreadVideo transparent muted src={staticFile(tile.src)} startFrom={short?60:0} style={{width:'100%',height:'100%'}}/>
 </div>;
};
const Wordmark:React.FC<{short:boolean}>=({short})=>{
 const [fontHandle]=React.useState(()=>delayRender('Load Source Han Serif SemiBold'));
 React.useEffect(()=>{
  const face=new FontFace('Minghua Source Han Serif',`url("${staticFile('fonts/SourceHanSerifCN-SemiBold.otf')}")`,{weight:'600'});
  face.load().then(font=>{document.fonts.add(font);continueRender(fontHandle)}).catch(cancelRender);
 },[fontHandle]);
 const f=useCurrentFrame(),letters=[...'名画开小差'],starts=short?[0,0,1,1,3]:[58,62,66,70,77];
 const frameOpacity=short?ease(f/7):ease((f-66)/10);
 return <>
  <svg width="1920" height="1080" style={{position:'absolute',opacity:frameOpacity*.64}}>
   <g fill="none" stroke="#B4935C" strokeWidth="2.5"><path d="M477 612 V580 H515 M1405 580 H1443 V612 M477 800 V832 H515"/><path d="M1405 832 H1443 V800" transform={`translate(0 ${short?0:Math.sin(Math.max(0,Math.min(1,(f-75)/10))*Math.PI)*7})`}/></g>
  </svg>
  <div style={{position:'absolute',top:603,left:518,width:884,height:218,display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'"Minghua Source Han Serif",serif',fontSize:170,fontWeight:600,lineHeight:1,color:'#F4E9D3'}}>
   {letters.map((c,i)=>{const d=f-starts[i],p=spring({fps:24,frame:Math.max(0,d),config:{damping:i===4?10:19,stiffness:250,mass:.46}});const alpha=interpolate(d,[0,3],[0,1],clamp);return <span key={c} style={{position:'absolute',left:[0,184,376,542,706][i],top:0,width:178,height:218,display:'flex',alignItems:'center',justifyContent:'center',opacity:alpha,transform:`translateY(${mix(i===4?-42:30,0,p)}px) rotate(${i===4?mix(-9,-2.2,p):0}deg)`,color:i===4?'#CEAE73':'#F4E9D3'}}>{c}</span>})}
  </div>
 </>;
};
const Intro:React.FC<Props>=({tiles,short=false,audio=true})=><AbsoluteFill><Stage/>{tiles.map((tile,i)=><Portrait key={i} tile={tile} index={i} short={short}/>)}<Wordmark short={short}/>{audio&&<Audio src={staticFile(short?'mix-short.wav':'mix.wav')}/>}<div style={{position:'absolute',right:48,bottom:25,color:'#877D69',fontFamily:'"Hiragino Sans GB",sans-serif',fontSize:17,letterSpacing:1}}>AI 趣味演绎</div></AbsoluteFill>;
const defaults:Props={tiles:[],audio:true};
registerRoot(()=> <><Composition id="MinghuaIntro" component={Intro} width={1920} height={1080} fps={24} durationInFrames={96} defaultProps={defaults}/><Composition id="MinghuaIntroShort" component={Intro} width={1920} height={1080} fps={24} durationInFrames={36} defaultProps={{...defaults,short:true}}/></>);

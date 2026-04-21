import { useState, useRef, useEffect } from "react";
import { fe } from "./formatValue.js";
import { fftRealRadix2, computeViewportMeasurements } from "./dsp.js";

/** DSO-style interactive chart */
export default function DsoScope(props) {
  var series=props.series||[],title=props.title,xLabel=props.xLabel;
  var logX=!!props.logX;
  var explicitW = typeof props.w === "number" && isFinite(props.w);
  var _mw = useState(700);
  var measuredW = _mw[0], setMeasuredW = _mw[1];
  var outerRef = useRef(null);
  var w = explicitW ? props.w : measuredW;
  var h = typeof props.h === "number" && isFinite(props.h) ? props.h : 280;
  var allowFft=!logX;
  var CL=['#00FF7F','#FF5555','#40C8FF','#FFB000','#FF40FF','#FFFF40'];
  var canRef=useRef(null),fftCanRef=useRef(null);
  var wrapRef=useRef(null),geomRef=useRef(null);
  var dragRef=useRef(null),curDragRef=useRef(null),wheelHRef=useRef(null);
  var _vp=useState(null);var viewport=_vp[0],setViewport=_vp[1];
  var _cu=useState({mode:'none',x1:null,x2:null,y1:null,y2:null});
  var cursors=_cu[0],setCursors=_cu[1];
  var _chv=useState({});var chanVisible=_chv[0],setChanVisible=_chv[1];
  var _cho=useState({});var chanOffset=_cho[0],setChanOffset=_cho[1];
  var _sm=useState(true);var showMeas=_sm[0],setShowMeas=_sm[1];
  var _sf=useState(false);var showFft=_sf[0],setShowFft=_sf[1];
  var _hi=useState(null);var hoverIdx=_hi[0],setHoverIdx=_hi[1];

  /* reset viewport when series count changes (new simulation type) */
  useEffect(function(){setViewport(null);setHoverIdx(null);},[series.length]);

  useEffect(
    function () {
      if (explicitW) return;
      var el = outerRef.current;
      if (!el || typeof ResizeObserver === "undefined") return;
      var ro = new ResizeObserver(function (entries) {
        var cr = entries[0] && entries[0].contentRect;
        if (!cr) return;
        var raw = Math.floor(cr.width);
        if (!isFinite(raw) || raw < 1) return;
        var nw = Math.max(120, raw);
        setMeasuredW(function (prev) {
          return prev === nw ? prev : nw;
        });
      });
      ro.observe(el);
      return function () {
        ro.disconnect();
      };
    },
    [explicitW],
  );

  /* geometry helpers */
  function autoFit(){
    var x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
    series.forEach(function(s){
      if(chanVisible[s.label]===false)return;
      var off=chanOffset[s.label]||0;
      for(var i=0;i<s.x.length;i++){
        var xv=logX?Math.log10(Math.max(s.x[i],1e-30)):s.x[i];
        var yv=s.y[i]+off;
        if(isFinite(xv)){x0=Math.min(x0,xv);x1=Math.max(x1,xv);}
        if(isFinite(yv)){y0=Math.min(y0,yv);y1=Math.max(y1,yv);}
      }
    });
    if(!isFinite(x0)){x0=0;x1=1;}if(!isFinite(y0)){y0=-1;y1=1;}
    if(x0===x1){x0-=1;x1+=1;}if(y0===y1){y0-=0.1;y1+=0.1;}
    var yp=(y1-y0)*0.1;
    if(logX)return{xMin:Math.pow(10,x0),xMax:Math.pow(10,x1),yMin:y0-yp,yMax:y1+yp};
    return{xMin:x0,xMax:x1,yMin:y0-yp,yMax:y1+yp};
  }

  function mkGeom(vp){
    var P={t:32,r:20,b:38,l:66},W2=w-P.l-P.r,H2=h-P.t-P.b;
    var lx0=logX?Math.log10(Math.max(vp.xMin,1e-30)):vp.xMin;
    var lx1=logX?Math.log10(Math.max(vp.xMax,1e-30)):vp.xMax;
    if(lx0===lx1)lx1=lx0+1;
    function tcx(v){var u=logX?Math.log10(Math.max(v,1e-30)):v;return P.l+(u-lx0)/(lx1-lx0)*W2;}
    function tcy(v){var yr=vp.yMax-vp.yMin||1;return P.t+H2-(v-vp.yMin)/yr*H2;}
    function tdx(cx){var u=lx0+(cx-P.l)/W2*(lx1-lx0);return logX?Math.pow(10,u):u;}
    function tdy(cy){var yr=vp.yMax-vp.yMin||1;return vp.yMin+(P.t+H2-cy)/H2*yr;}
    return{P:P,W2:W2,H2:H2,xMin:vp.xMin,xMax:vp.xMax,yMin:vp.yMin,yMax:vp.yMax,
           lx0:lx0,lx1:lx1,tcx:tcx,tcy:tcy,tdx:tdx,tdy:tdy};
  }

  /* main canvas draw */
  useEffect(function(){
    var can=canRef.current;if(!can)return;
    var ctx=can.getContext('2d'),dpr=window.devicePixelRatio||1;
    can.width=w*dpr;can.height=h*dpr;ctx.scale(dpr,dpr);
    can.style.width=w+'px';can.style.height=h+'px';
    var vp=viewport||autoFit(),g=mkGeom(vp);
    geomRef.current=g;
    var P=g.P,W2=g.W2,H2=g.H2,NX=10,NY=8;
    var xR=vp.xMax-vp.xMin,yR=vp.yMax-vp.yMin||1;

    /* dark background */
    ctx.fillStyle='#080810';ctx.fillRect(0,0,w,h);

    /* major grid — DSO green tint */
    ctx.strokeStyle='rgba(0,210,90,0.15)';ctx.lineWidth=1;
    for(var gi=0;gi<=NX;gi++){var gx=P.l+W2*gi/NX;ctx.beginPath();ctx.moveTo(gx,P.t);ctx.lineTo(gx,P.t+H2);ctx.stroke();}
    for(var gj=0;gj<=NY;gj++){var gy=P.t+H2*gj/NY;ctx.beginPath();ctx.moveTo(P.l,gy);ctx.lineTo(P.l+W2,gy);ctx.stroke();}

    /* minor grid (5 subdivisions per division) */
    ctx.strokeStyle='rgba(0,210,90,0.05)';ctx.lineWidth=0.5;
    for(var gi=0;gi<NX;gi++)for(var sub=1;sub<5;sub++){var gx2=P.l+W2*(gi+sub/5)/NX;ctx.beginPath();ctx.moveTo(gx2,P.t);ctx.lineTo(gx2,P.t+H2);ctx.stroke();}
    for(var gj=0;gj<NY;gj++)for(var sub=1;sub<5;sub++){var gy2=P.t+H2*(gj+sub/5)/NY;ctx.beginPath();ctx.moveTo(P.l,gy2);ctx.lineTo(P.l+W2,gy2);ctx.stroke();}

    /* border */
    ctx.strokeStyle='rgba(0,210,90,0.55)';ctx.lineWidth=1;ctx.strokeRect(P.l,P.t,W2,H2);

    /* X-axis labels */
    ctx.fillStyle='#7CFC00';ctx.font='10px Consolas,monospace';ctx.textAlign='center';
    for(var gi=0;gi<=NX;gi++){
      var xv=logX?Math.pow(10,g.lx0+(g.lx1-g.lx0)*gi/NX):vp.xMin+xR*gi/NX;
      ctx.fillText(fe(xv),P.l+W2*gi/NX,P.t+H2+16);
    }

    /* Y-axis labels */
    ctx.textAlign='right';
    for(var gj=0;gj<=NY;gj++)ctx.fillText(fe(vp.yMax-yR*gj/NY),P.l-5,P.t+H2*gj/NY+4);

    /* T/div and V/div scale info */
    ctx.fillStyle='#3A4A3A';ctx.font='9px Consolas,monospace';
    var tdivVal=logX?(Math.pow(10,g.lx0+(g.lx1-g.lx0)/NX)-Math.pow(10,g.lx0)):xR/NX;
    ctx.textAlign='left';ctx.fillText((logX?'Hz':'T')+'/div '+fe(tdivVal),P.l,h-3);
    ctx.textAlign='right';ctx.fillText('V/div '+fe(yR/NY),w-3,h-3);

    /* title */
    if(title){ctx.fillStyle='#7CFC00';ctx.font='bold 11px "Segoe UI",sans-serif';ctx.textAlign='center';ctx.fillText(title,P.l+W2/2,P.t-13);}

    /* clipped plot area */
    ctx.save();ctx.beginPath();ctx.rect(P.l,P.t,W2,H2);ctx.clip();

    /* series traces */
    series.forEach(function(s,si){
      if(chanVisible[s.label]===false)return;
      var off=chanOffset[s.label]||0,col=s.color||CL[si%CL.length];
      ctx.strokeStyle=col;ctx.lineWidth=1.5;ctx.beginPath();
      var started=false;
      for(var i=0;i<s.x.length;i++){
        var px=g.tcx(s.x[i]),py=g.tcy(s.y[i]+off);
        if(!isFinite(px)||!isFinite(py)){started=false;continue;}
        if(!started){ctx.moveTo(px,py);started=true;}else ctx.lineTo(px,py);
      }
      ctx.stroke();
    });

    /* hover crosshair */
    var hi=hoverIdx;
    if(hi!=null&&hi>=0&&series[0]&&hi<series[0].x.length){
      var hcx=g.tcx(series[0].x[hi]);
      if(isFinite(hcx)){
        ctx.strokeStyle='rgba(255,255,255,0.3)';ctx.lineWidth=1;ctx.setLineDash([3,3]);
        ctx.beginPath();ctx.moveTo(hcx,P.t);ctx.lineTo(hcx,P.t+H2);ctx.stroke();ctx.setLineDash([]);
        series.forEach(function(s,si){
          if(chanVisible[s.label]===false||hi>=s.y.length)return;
          var off=chanOffset[s.label]||0,py=g.tcy(s.y[hi]+off);
          if(!isFinite(py))return;
          ctx.fillStyle=s.color||CL[si%CL.length];
          ctx.beginPath();ctx.arc(hcx,py,4,0,2*Math.PI);ctx.fill();
        });
      }
    }

    /* cursor lines */
    var cm=cursors.mode;ctx.font='10px Consolas,monospace';
    if((cm==='x'||cm==='xy')&&cursors.x1!=null){
      var cx1=g.tcx(cursors.x1);ctx.strokeStyle='#FFD700';ctx.lineWidth=1.5;ctx.setLineDash([7,3]);
      ctx.beginPath();ctx.moveTo(cx1,P.t);ctx.lineTo(cx1,P.t+H2);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#FFD700';ctx.textAlign='left';ctx.fillText('X1',cx1+3,P.t+14);
    }
    if((cm==='x'||cm==='xy')&&cursors.x2!=null){
      var cx2=g.tcx(cursors.x2);ctx.strokeStyle='#FFA500';ctx.lineWidth=1.5;ctx.setLineDash([7,3]);
      ctx.beginPath();ctx.moveTo(cx2,P.t);ctx.lineTo(cx2,P.t+H2);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#FFA500';ctx.textAlign='right';ctx.fillText('X2',cx2-3,P.t+14);
    }
    if((cm==='y'||cm==='xy')&&cursors.y1!=null){
      var cy1=g.tcy(cursors.y1);ctx.strokeStyle='#00CFFF';ctx.lineWidth=1.5;ctx.setLineDash([7,3]);
      ctx.beginPath();ctx.moveTo(P.l,cy1);ctx.lineTo(P.l+W2,cy1);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#00CFFF';ctx.textAlign='right';ctx.fillText('Y1',P.l+W2-4,cy1-5);
    }
    if((cm==='y'||cm==='xy')&&cursors.y2!=null){
      var cy2=g.tcy(cursors.y2);ctx.strokeStyle='#1E90FF';ctx.lineWidth=1.5;ctx.setLineDash([7,3]);
      ctx.beginPath();ctx.moveTo(P.l,cy2);ctx.lineTo(P.l+W2,cy2);ctx.stroke();ctx.setLineDash([]);
      ctx.fillStyle='#1E90FF';ctx.textAlign='right';ctx.fillText('Y2',P.l+W2-4,cy2+13);
    }

    ctx.restore();

    /* legend (above plot) */
    var lleg=P.l+6;ctx.font='10px Consolas,monospace';
    series.forEach(function(s,si){
      if(chanVisible[s.label]===false)return;
      var col=s.color||CL[si%CL.length];
      ctx.strokeStyle=col;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(lleg,P.t-12);ctx.lineTo(lleg+14,P.t-12);ctx.stroke();
      ctx.fillStyle=col;ctx.textAlign='left';ctx.fillText(s.label,lleg+18,P.t-8);
      lleg+=ctx.measureText(s.label).width+36;
    });
  },[series,viewport,cursors,hoverIdx,chanVisible,chanOffset,title,logX,w,h]);

  /* FFT sub-canvas */
  var fftH=Math.round(h*0.4);
  useEffect(function(){
    var can=fftCanRef.current;if(!can)return;
    if(!showFft||!allowFft||!series.length){can.width=0;can.height=0;return;}
    var s0=series[0],ctx=can.getContext('2d'),dpr=window.devicePixelRatio||1;
    can.width=w*dpr;can.height=fftH*dpr;ctx.scale(dpr,dpr);
    can.style.width=w+'px';can.style.height=fftH+'px';
    ctx.fillStyle='#080810';ctx.fillRect(0,0,w,fftH);
    var P2={t:6,r:20,b:26,l:66},W3=w-P2.l-P2.r,H3=fftH-P2.t-P2.b;
    var vp=viewport,xA=vp?vp.xMin:s0.x[0],xB=vp?vp.xMax:s0.x[s0.x.length-1];
    var visY=[];
    for(var i=0;i<s0.x.length;i++)if(s0.x[i]>=xA&&s0.x[i]<=xB)visY.push(s0.y[i]);
    if(visY.length<8){
      ctx.fillStyle='#555';ctx.font='10px Consolas,monospace';ctx.textAlign='center';
      ctx.fillText('FFT: need 8+ visible samples',w/2,fftH/2);return;
    }
    var fR=fftRealRadix2(visY);
    var dt=(s0.x[s0.x.length-1]-s0.x[0])/Math.max(s0.x.length-1,1);
    var fs=1/Math.max(Math.abs(dt),1e-30),bins=Math.floor(fR.n/2)+1,fNyq=fs/2;
    var dbArr=new Array(bins);
    for(var i=0;i<bins;i++){
      var mag=Math.sqrt(fR.re[i]*fR.re[i]+fR.im[i]*fR.im[i])/Math.max(fR.n/2,1);
      dbArr[i]=20*Math.log10(Math.max(mag,1e-30));
    }
    var dbMin=Infinity,dbMax=-Infinity;
    for(var i=1;i<bins;i++){if(dbArr[i]<dbMin)dbMin=dbArr[i];if(dbArr[i]>dbMax)dbMax=dbArr[i];}
    if(!isFinite(dbMin)||dbMin>=dbMax)dbMin=dbMax-60;
    var dpd=(dbMax-dbMin)*0.08;dbMin-=dpd;dbMax+=dpd;
    /* grid */
    ctx.strokeStyle='rgba(255,64,255,0.15)';ctx.lineWidth=1;
    for(var i=0;i<=5;i++){var gx3=P2.l+W3*i/5;ctx.beginPath();ctx.moveTo(gx3,P2.t);ctx.lineTo(gx3,P2.t+H3);ctx.stroke();}
    for(var j=0;j<=4;j++){var gy3=P2.t+H3*j/4;ctx.beginPath();ctx.moveTo(P2.l,gy3);ctx.lineTo(P2.l+W3,gy3);ctx.stroke();}
    ctx.strokeStyle='rgba(255,64,255,0.45)';ctx.lineWidth=1;ctx.strokeRect(P2.l,P2.t,W3,H3);
    /* labels */
    ctx.fillStyle='#FF80FF';ctx.font='9px Consolas,monospace';ctx.textAlign='center';
    for(var i=0;i<=5;i++)ctx.fillText(fe(fNyq*i/5),P2.l+W3*i/5,P2.t+H3+14);
    ctx.textAlign='right';
    for(var j=0;j<=4;j++){var dvv=dbMax-(dbMax-dbMin)*j/4;ctx.fillText(dvv.toFixed(0)+'dB',P2.l-4,P2.t+H3*j/4+4);}
    ctx.fillStyle='#888';ctx.font='9px Consolas,monospace';ctx.textAlign='left';
    ctx.fillText('FFT (Hann) \u2014 '+s0.label,P2.l+4,P2.t+H3-3);
    ctx.textAlign='right';ctx.fillStyle='#FF80FF';ctx.fillText('Hz',P2.l+W3,P2.t+H3+14);
    /* trace */
    ctx.save();ctx.beginPath();ctx.rect(P2.l,P2.t,W3,H3);ctx.clip();
    ctx.strokeStyle='#FF40FF';ctx.lineWidth=1.5;ctx.beginPath();
    var stf=false;
    for(var i=1;i<bins;i++){
      var pxf=P2.l+((i-1)/Math.max(bins-2,1))*W3;
      var pyf=P2.t+H3-(dbArr[i]-dbMin)/Math.max(dbMax-dbMin,1)*H3;
      if(!isFinite(pyf)){stf=false;continue;}
      if(!stf){ctx.moveTo(pxf,pyf);stf=true;}else ctx.lineTo(pxf,pyf);
    }
    ctx.stroke();ctx.restore();
  },[showFft,series,viewport,allowFft,w,fftH]);

  /* non-passive wheel (zoom) */
  wheelHRef.current=function(e){
    e.preventDefault();
    var g=geomRef.current;if(!g||!wrapRef.current)return;
    var rect=wrapRef.current.getBoundingClientRect();
    var cx=e.clientX-rect.left,cy=e.clientY-rect.top;
    var factor=e.deltaY>0?1.25:0.8,vp=viewport||autoFit();
    if(e.shiftKey){
      var yd=g.tdy(cy);
      setViewport(Object.assign({},vp,{yMin:yd-(yd-vp.yMin)*factor,yMax:yd+(vp.yMax-yd)*factor}));
    }else if(logX){
      var lxa=g.lx0,lxb=g.lx1,lxd=lxa+(cx-g.P.l)/g.W2*(lxb-lxa);
      setViewport(Object.assign({},vp,{xMin:Math.pow(10,lxd-(lxd-lxa)*factor),xMax:Math.pow(10,lxd+(lxb-lxd)*factor)}));
    }else{
      var xd=g.tdx(cx);
      setViewport(Object.assign({},vp,{xMin:xd-(xd-vp.xMin)*factor,xMax:xd+(vp.xMax-xd)*factor}));
    }
  };
  useEffect(function(){
    var el=wrapRef.current;if(!el)return;
    function wh(e){if(wheelHRef.current)wheelHRef.current(e);}
    el.addEventListener('wheel',wh,{passive:false});
    return function(){el.removeEventListener('wheel',wh);};
  },[]);

  /* mouse helpers */
  function getPos(e){var r=wrapRef.current.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
  function inPlot(p){var g=geomRef.current;return g&&p.x>=g.P.l&&p.x<=g.P.l+g.W2&&p.y>=g.P.t&&p.y<=g.P.t+g.H2;}
  function nearCursor(p){
    var g=geomRef.current;if(!g)return null;
    var hits=[];
    function chkX(k,v){var px=g.tcx(v);if(Math.abs(p.x-px)<9&&p.y>=g.P.t&&p.y<=g.P.t+g.H2)hits.push({t:k,d:Math.abs(p.x-px)});}
    function chkY(k,v){var py=g.tcy(v);if(Math.abs(p.y-py)<9&&p.x>=g.P.l&&p.x<=g.P.l+g.W2)hits.push({t:k,d:Math.abs(p.y-py)});}
    if((cursors.mode==='x'||cursors.mode==='xy')&&cursors.x1!=null)chkX('x1',cursors.x1);
    if((cursors.mode==='x'||cursors.mode==='xy')&&cursors.x2!=null)chkX('x2',cursors.x2);
    if((cursors.mode==='y'||cursors.mode==='xy')&&cursors.y1!=null)chkY('y1',cursors.y1);
    if((cursors.mode==='y'||cursors.mode==='xy')&&cursors.y2!=null)chkY('y2',cursors.y2);
    if(!hits.length)return null;
    hits.sort(function(a,b){return a.d-b.d;});return hits[0].t;
  }
  function pickIdx(xd,xs){
    var lo=0,hi=xs.length-1;
    while(lo<hi){var m=(lo+hi)>>1;if(xs[m]<xd)lo=m+1;else hi=m;}
    if(lo>0&&Math.abs(xs[lo-1]-xd)<Math.abs(xs[lo]-xd))lo--;return lo;
  }
  function onMouseDown(e){
    var p=getPos(e),g=geomRef.current;if(!g)return;
    var hit=nearCursor(p);
    if(hit){curDragRef.current=hit;dragRef.current={type:'cursor'};return;}
    if(!inPlot(p))return;
    var m=cursors.mode;
    if((m==='x'||m==='xy')&&cursors.x1==null){setCursors(function(c){return Object.assign({},c,{x1:g.tdx(p.x)});});return;}
    if((m==='x'||m==='xy')&&cursors.x2==null){setCursors(function(c){return Object.assign({},c,{x2:g.tdx(p.x)});});return;}
    if((m==='y'||m==='xy')&&cursors.y1==null){setCursors(function(c){return Object.assign({},c,{y1:g.tdy(p.y)});});return;}
    if((m==='y'||m==='xy')&&cursors.y2==null){setCursors(function(c){return Object.assign({},c,{y2:g.tdy(p.y)});});return;}
    dragRef.current={type:'pan',ox:p.x,oy:p.y,vp0:viewport||autoFit()};
  }
  function onMouseMove(e){
    var p=getPos(e),g=geomRef.current;if(!g)return;
    if(curDragRef.current&&dragRef.current&&dragRef.current.type==='cursor'){
      var t=curDragRef.current;
      if(t==='x1'||t==='x2')setCursors(function(c){var u=Object.assign({},c);u[t]=g.tdx(p.x);return u;});
      else setCursors(function(c){var u=Object.assign({},c);u[t]=g.tdy(p.y);return u;});
      return;
    }
    if(dragRef.current&&dragRef.current.type==='pan'){
      var d=dragRef.current,vp=d.vp0,xR=vp.xMax-vp.xMin,yR=vp.yMax-vp.yMin;
      setViewport({xMin:vp.xMin-(p.x-d.ox)/g.W2*xR,xMax:vp.xMax-(p.x-d.ox)/g.W2*xR,
                   yMin:vp.yMin+(p.y-d.oy)/g.H2*yR,yMax:vp.yMax+(p.y-d.oy)/g.H2*yR});
      return;
    }
    if(!inPlot(p)){setHoverIdx(null);return;}
    if(!series.length||!series[0].x.length)return;
    var idx=pickIdx(g.tdx(p.x),series[0].x);
    setHoverIdx(function(prev){return prev===idx?prev:idx;});
  }
  function onMouseUp(){dragRef.current=null;curDragRef.current=null;}
  function onLeave(){setHoverIdx(null);dragRef.current=null;curDragRef.current=null;}
  function onDblClick(){setViewport(null);}

  /* derived UI data */
  var cm=cursors.mode,cLines=[];
  if(cm!=='none'){
    if((cm==='x'||cm==='xy')&&cursors.x1!=null&&cursors.x2!=null){
      var xdel=cursors.x2-cursors.x1;
      cLines.push('X1: '+fe(cursors.x1));cLines.push('X2: '+fe(cursors.x2));
      cLines.push('\u0394X: '+fe(xdel));
      if(!logX&&Math.abs(xdel)>0)cLines.push('1/\u0394X: '+fe(1/xdel));
    }else if((cm==='x'||cm==='xy')&&cursors.x1!=null)cLines.push('X1: '+fe(cursors.x1));
    if((cm==='y'||cm==='xy')&&cursors.y1!=null&&cursors.y2!=null){
      cLines.push('Y1: '+fe(cursors.y1));cLines.push('Y2: '+fe(cursors.y2));
      cLines.push('\u0394Y: '+fe(cursors.y2-cursors.y1));
    }else if((cm==='y'||cm==='xy')&&cursors.y1!=null)cLines.push('Y1: '+fe(cursors.y1));
  }

  var hLines=[];
  if(hoverIdx!=null&&series[0]&&hoverIdx>=0&&hoverIdx<series[0].x.length){
    hLines.push(fe(series[0].x[hoverIdx]));
    series.forEach(function(s){
      if(chanVisible[s.label]!==false&&hoverIdx<s.y.length)hLines.push(s.label+': '+fe(s.y[hoverIdx]));
    });
  }

  var mItems=null;
  if(showMeas&&!logX&&series.length>0){
    var mvp=viewport||autoFit();
    var mm=computeViewportMeasurements(series[0].x,series[0].y,mvp.xMin,mvp.xMax);
    if(mm)mItems=[
      ['Vmax',fe(mm.vmax,'V')],['Vmin',fe(mm.vmin,'V')],['Vpp',fe(mm.vpp,'V')],
      ['Vrms',fe(mm.vrms,'V')],['Mean',fe(mm.mean,'V')],
      mm.freq!=null?['Freq',fe(mm.freq,'Hz')]:null,
      mm.period!=null?['Period',fe(mm.period,'s')]:null,
      mm.riseT!=null?['Rise',fe(mm.riseT,'s')]:null,
      mm.fallT!=null?['Fall',fe(mm.fallT,'s')]:null,
      ['Duty',mm.duty.toFixed(1)+'%'],
    ].filter(Boolean);
  }

  /* toolbar */
  var sepSt={display:'inline-block',width:1,height:14,background:'rgba(0,210,90,0.18)',margin:'0 4px',verticalAlign:'middle'};
  var chanBtns=series.map(function(s,si){
    var vis=chanVisible[s.label]!==false,col=s.color||CL[si%CL.length];
    return <button key={s.label} type="button"
      onClick={function(){setChanVisible(function(cv){var u=Object.assign({},cv);u[s.label]=!vis;return u;});}}
      style={{fontSize:9,padding:'2px 7px',borderRadius:3,border:'1px solid '+col,
        background:vis?col+'28':'transparent',color:vis?col:'#444',
        cursor:'pointer',fontFamily:'Consolas,monospace',fontWeight:700}}>{s.label}</button>;
  });
  var curBtns=[{k:'none',l:'CUR\u00a0OFF'},{k:'x',l:'X'},{k:'y',l:'Y'},{k:'xy',l:'XY'}].map(function(mb){
    var act=cursors.mode===mb.k;
    return <button key={mb.k} type="button"
      onClick={function(){setCursors({mode:mb.k,x1:null,x2:null,y1:null,y2:null});}}
      style={{fontSize:9,padding:'2px 6px',borderRadius:3,
        border:'1px solid '+(act?'#FFD700':'#252525'),
        background:act?'rgba(255,215,0,0.12)':'transparent',
        color:act?'#FFD700':'#4A4A4A',cursor:'pointer',fontFamily:'Consolas,monospace'}}>{mb.l}</button>;
  });

  var outerBox = {
    display: explicitW ? "inline-block" : "block",
    verticalAlign: "top",
    userSelect: "none",
    width: explicitW ? undefined : "100%",
    maxWidth: "100%",
    boxSizing: "border-box",
    background: "#080810",
    border: "1px solid rgba(0,210,90,0.3)",
    borderRadius: 5,
    overflow: "hidden",
  };

  return (
    <div ref={outerRef} style={outerBox}>
      {/* toolbar */}
      <div style={{display:'flex',alignItems:'center',gap:3,padding:'3px 6px',
        background:'#0C0C1A',borderBottom:'1px solid rgba(0,210,90,0.12)',flexWrap:'wrap'}}>
        {chanBtns}
        <span style={sepSt}/>
        {curBtns}
        <span style={sepSt}/>
        {allowFft&&<button type="button" onClick={function(){setShowFft(function(v){return !v;});}}
          style={{fontSize:9,padding:'2px 6px',borderRadius:3,border:'1px solid '+(showFft?'#FF40FF':'#252525'),
            background:showFft?'rgba(255,64,255,0.12)':'transparent',color:showFft?'#FF40FF':'#4A4A4A',
            cursor:'pointer',fontFamily:'Consolas,monospace'}}>FFT</button>}
        <button type="button" onClick={function(){setShowMeas(function(v){return !v;});}}
          style={{fontSize:9,padding:'2px 6px',borderRadius:3,border:'1px solid '+(showMeas?'#00BFFF':'#252525'),
            background:showMeas?'rgba(0,191,255,0.1)':'transparent',color:showMeas?'#00BFFF':'#4A4A4A',
            cursor:'pointer',fontFamily:'Consolas,monospace'}}>MEAS</button>
        <button type="button" onClick={onDblClick} title="Reset to auto-fit (or double-click plot)"
          style={{fontSize:9,padding:'2px 6px',borderRadius:3,border:'1px solid #252525',
            background:'transparent',color:'#4A4A4A',cursor:'pointer',fontFamily:'Consolas,monospace'}}>FIT</button>
        <span style={{flex:1}}/>
        <span style={{fontSize:8,color:'#2A3A2A',fontFamily:'Consolas,monospace',paddingRight:2}}>scroll=zoom shift+scroll=Vy drag=pan dbl=fit</span>
      </div>
      {/* plot canvas */}
      <div ref={wrapRef} style={{position:'relative',lineHeight:0,cursor:'crosshair'}}
        onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp}
        onMouseLeave={onLeave} onDoubleClick={onDblClick}>
        <canvas ref={canRef} style={{display:'block'}}/>
        {hLines.length>0&&<div style={{position:'absolute',left:6,top:4,padding:'5px 8px',
          fontSize:10,fontFamily:'Consolas,monospace',lineHeight:1.55,
          background:'rgba(8,8,16,0.9)',border:'1px solid rgba(0,210,90,0.45)',
          borderRadius:4,color:'#7CFC00',pointerEvents:'none',zIndex:10,whiteSpace:'pre'}}>
          {hLines.join('\n')}
        </div>}
        {cLines.length>0&&<div style={{position:'absolute',right:4,top:4,padding:'5px 8px',
          fontSize:10,fontFamily:'Consolas,monospace',lineHeight:1.55,
          background:'rgba(8,8,16,0.9)',border:'1px solid rgba(255,215,0,0.55)',
          borderRadius:4,color:'#FFD700',pointerEvents:'none',zIndex:10,whiteSpace:'pre'}}>
          {cLines.join('\n')}
        </div>}
      </div>
      {/* FFT sub-canvas */}
      {showFft&&allowFft&&<div style={{borderTop:'1px solid rgba(255,64,255,0.2)'}}>
        <canvas ref={fftCanRef} style={{display:'block'}}/>
      </div>}
      {/* measurements panel */}
      {mItems&&mItems.length>0&&<div style={{display:'flex',flexWrap:'wrap',gap:'3px 12px',
        padding:'4px 8px',background:'#0C0C1A',borderTop:'1px solid rgba(0,210,90,0.12)',
        fontSize:10,fontFamily:'Consolas,monospace'}}>
        {mItems.map(function(it,midx){return <span key={midx}><span style={{color:'#2A3A2A'}}>{it[0]}: </span><span style={{color:'#7CFC00'}}>{it[1]}</span></span>;})}
      </div>}
    </div>
  );
}

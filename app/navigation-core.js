/* Pure navigation rules shared by GPS, camera and smoke tests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.RelasNavigation=api})(typeof globalThis!=='undefined'?globalThis:this,function(){
  const angularDelta=(from,to)=>((to-from+540)%360)-180;
  function smoothHeading(previous,next,weight=.3){if(!Number.isFinite(next))return previous;if(!Number.isFinite(previous))return(next+360)%360;return(previous+angularDelta(previous,next)*weight+360)%360}
  function validFix(coords,timestamp,now=Date.now()){
    if(!coords||!Number.isFinite(coords.longitude)||!Number.isFinite(coords.latitude)||Math.abs(coords.longitude)>180||Math.abs(coords.latitude)>90)return{ok:false,reason:'Localização inválida'};
    if(!Number.isFinite(coords.accuracy)||coords.accuracy>100)return{ok:false,reason:'GPS impreciso · procure um local aberto'};
    if(!Number.isFinite(timestamp)||now-timestamp>15000||timestamp>now+5000)return{ok:false,reason:'GPS desatualizado · aguardando sinal'};
    return{ok:true};
  }
  // Speedcam convention: 0/unknown = conservative, 1 = one direction, 2 = both.
  // Preserve the raw source: an unknown vehicle heading never excludes a point.
  function directionMatches(point,heading,tolerance=55){const rule=Number(point.direction_type),direction=Number(point.direction);if(![1,2].includes(rule)||point.direction==null||point.direction===''||!Number.isFinite(direction)||!Number.isFinite(heading))return true;const delta=Math.abs(angularDelta(direction,heading));return delta<=tolerance||(rule===2&&Math.abs(delta-180)<=tolerance)}
  function smoothPosition(previous,next,weight=.6){if(!previous)return next.slice();return previous.map((v,i)=>v+(next[i]-v)*weight)}
  function cameraZoom(speed){return speed>22?15.9:speed>8?16.5:17}
  function geoDistance(a,b){return Math.hypot((b[0]-a[0])*111320*Math.cos(a[1]*Math.PI/180),(b[1]-a[1])*110540)}
  function geoBearing(a,b){const p=a[1]*Math.PI/180,q=b[1]*Math.PI/180,d=(b[0]-a[0])*Math.PI/180;return(Math.atan2(Math.sin(d)*Math.cos(q),Math.cos(p)*Math.sin(q)-Math.sin(p)*Math.cos(q)*Math.cos(d))*180/Math.PI+360)%360}
  function projectSegment(p,s){const k=Math.cos(p[1]*Math.PI/180),dx=(s.b[0]-s.a[0])*k,dy=s.b[1]-s.a[1],t=Math.max(0,Math.min(1,((p[0]-s.a[0])*k*dx+(p[1]-s.a[1])*dy)/(dx*dx+dy*dy||1))),point=[s.a[0]+(s.b[0]-s.a[0])*t,s.a[1]+(s.b[1]-s.a[1])*t];return{longitude:point[0],latitude:point[1],along:s.start+t*s.len,segmentIndex:s.index,roadBearing:s.bearing??geoBearing(s.a,s.b),distanceToRoute:geoDistance(p,point)}}
  function projectSegments(p,segments){let best=null;for(let i=0;i<segments.length;i++){const c=projectSegment(p,segments[i]);if(!best||c.distanceToRoute<best.distanceToRoute)best={...c,segmentIndex:i}}return best}

  // Arrival is deliberately conservative: route progress alone cannot prove arrival at a house number.
  class ArrivalTracker {
    constructor(){this.reset()}
    reset(){this.state='EN_ROUTE';this.confirmations=0;this.lastAt=0}
    update({remainingMetres,endpointDistanceMetres,routeDistanceMetres,accuracyMetres,speedMetresPerSecond,positionPredicted=false,locationLost=false,precision='unknown',now=Date.now()}){
      const precise=['rooftop','entrance','exact'].includes(precision);
      const eligible=Number.isFinite(remainingMetres)&&remainingMetres<=35&&Number.isFinite(endpointDistanceMetres)&&endpointDistanceMetres<=30&&Number.isFinite(routeDistanceMetres)&&routeDistanceMetres<=25&&Number.isFinite(accuracyMetres)&&accuracyMetres<=25&&Number.isFinite(speedMetresPerSecond)&&speedMetresPerSecond<=3&& !positionPredicted&&!locationLost;
      if(!eligible){this.confirmations=0;if(this.state!=='EN_ROUTE')this.state=Number.isFinite(remainingMetres)&&remainingMetres<=180?'APPROACHING':'EN_ROUTE';return{state:this.state,confirmed:false,precise,reason:!precise?'ADDRESS_NOT_PRECISE':'POSITION_NOT_CONFIRMED'}}
      if(!this.lastAt||now-this.lastAt>=500){this.confirmations++;this.lastAt=now}
      this.state=this.confirmations>=2?(precise?'ARRIVED_CONFIRMED':'ARRIVAL_APPROXIMATE'):'ARRIVAL_CANDIDATE';
      return{state:this.state,confirmed:this.state==='ARRIVED_CONFIRMED',precise,reason:precise?'LOCATION_CONFIRMED':'ADDRESS_NOT_PRECISE'}
    }
  }
  return{ArrivalTracker,geoDistance,geoBearing,projectSegment,projectSegments,angularDelta,smoothHeading,validFix,directionMatches,smoothPosition,cameraZoom};
});

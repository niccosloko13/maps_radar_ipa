const assert=require('node:assert/strict');
const {ArrivalTracker}=require('../app/navigation-core.js');
const base={remainingMetres:12,endpointDistanceMetres:9,routeDistanceMetres:5,accuracyMetres:8,speedMetresPerSecond:1,precision:'rooftop'};
function check(name,fn){fn();process.stdout.write('PASS '+name+'\n')}
check('exact destination needs two separate fixes',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,now:1000}).confirmed,false);assert.equal(a.update({...base,now:1600}).confirmed,true)});
check('street-only address never exact',()=>{const a=new ArrivalTracker();a.update({...base,precision:'street',now:1000});const v=a.update({...base,precision:'street',now:1600});assert.equal(v.confirmed,false);assert.equal(v.state,'ARRIVAL_APPROXIMATE')});
check('off-route position never confirms',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,routeDistanceMetres:65,now:1000}).state,'EN_ROUTE')});
check('predicted position never confirms',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,positionPredicted:true,now:1000}).confirmed,false)});
check('bad GPS accuracy never confirms',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,accuracyMetres:65,now:1000}).confirmed,false)});
check('moving fast never confirms',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,speedMetresPerSecond:18,now:1000}).confirmed,false)});
check('lost location never confirms',()=>{const a=new ArrivalTracker();assert.equal(a.update({...base,locationLost:true,now:1000}).confirmed,false)});

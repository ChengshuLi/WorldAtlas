export function wheelTiming(data) {
  const gaps=data.frames.slice(1).map((time,i)=>time-data.frames[i]);
  const sorted=[...gaps].sort((a,b)=>a-b),first=data.events[0]?.time;
  const base=data.transforms.findLast(frame=>frame.time<=first)??data.transforms[0];
  const changed=first===undefined?null:data.transforms.find(frame=>frame.time>=first&&(
    frame.transform!==base?.transform||frame.pane!==base?.pane||frame.frame!==base?.frame));
  return {
    first_observed_transform_ms:changed?changed.time-first:null,
    raf_p50_ms:sorted[Math.floor(sorted.length*.5)]??null,
    raf_p95_ms:sorted[Math.floor(sorted.length*.95)]??null,
    frames_over_34ms:gaps.filter(gap=>gap>34).length,
    frames:gaps.length
  };
}

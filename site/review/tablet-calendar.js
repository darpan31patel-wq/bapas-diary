// live since 28 Oct 18:2x UTC; rerun shows the live page as "before"
// Mockup only: the Calendar's sizes with all seven days across the screen on an upright tablet (tablet check, 28 Oct 2026).
// website-tablet-mockup.yml swaps OLD for NEW inside the test browser; nothing on the site changes.
module.exports = {
  OLD: `const h=(track.clientHeight-14)*Z, g=Math.max(3,Math.min(10,innerHeight*.009)*Z), bh=0;
  const rh=(h-26*Z-5*g)/5, cw=Math.max(30,Math.round(rh*1.08));`,
  NEW: `let h=(track.clientHeight-14)*Z; const g=Math.max(3,Math.min(10,innerHeight*.009)*Z), bh=0;
  let rh=(h-26*Z-5*g)/5, cw=Math.max(30,Math.round(rh*1.08));
  /* an upright tablet: all seven days across the screen, the days a little taller than wide (tablet check, 28 Oct 2026) */
  const fitW=Math.floor((track.clientWidth*.97-6*g)/7);
  if(cw>fitW){cw=Math.max(30,fitW); rh=Math.min(rh,cw*1.3); h=26*Z+5*rh+5*g}`,
};

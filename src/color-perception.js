// OKLab (Björn Ottosson, 2020): https://bottosson.github.io/posts/oklab/
// Full-severity Machado et al. (2009) matrices operate on linear sRGB:
// https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
// These are modeled color differences, not a physical color-vision certificate.
const matrices = {
  protanopia: [[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
  deuteranopia: [[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]],
  tritanopia: [[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]]
};
export const visionModels = ['normal', ...Object.keys(matrices)];
const clamp = value => Math.max(0, Math.min(1, value));
export function cssRGB(color) {
  if (/^#[a-f\d]{6}$/i.test(color)) return [1,3,5].map(i => parseInt(color.slice(i,i+2),16));
  const match = /^hsl\((\d+(?:\.\d+)?) (\d+(?:\.\d+)?)% (\d+(?:\.\d+)?)%\)$/.exec(color);
  if (!match) throw Error('Use a six-digit RGB hex or generated HSL color');
  const [h,s,l] = match.slice(1).map(Number), saturation = s/100, light = l/100;
  if (h > 360 || s > 100 || l > 100) throw Error('Color is outside sRGB bounds');
  const a = saturation * Math.min(light,1-light);
  return [0,8,4].map(n => { const k = (n+h/30)%12; return Math.round(255*(light-a*Math.max(-1,Math.min(k-3,9-k,1)))); });
}
export function colorLab(color, model = 'normal') {
  let rgb = cssRGB(color).map(v => { const x = v/255; return x <= 0.04045 ? x/12.92 : ((x+0.055)/1.055)**2.4; });
  if (model !== 'normal') {
    if (!matrices[model]) throw Error('Unknown color-vision model');
    rgb = matrices[model].map(row => clamp(row.reduce((sum,c,i) => sum+c*rgb[i],0)));
  }
  const [r,g,b] = rgb;
  const l = Math.cbrt(0.4122214708*r+0.5363325363*g+0.0514459929*b);
  const m = Math.cbrt(0.2119034982*r+0.6806995451*g+0.1073969566*b);
  const s = Math.cbrt(0.0883024619*r+0.2817188376*g+0.6299787005*b);
  return [0.2104542553*l+0.793617785*m-0.0040720468*s,1.9779984951*l-2.428592205*m+0.4505937099*s,0.0259040371*l+0.7827717662*m-0.808675766*s];
}
export function labDistance(a,b) { return 100*Math.hypot(...a.map((v,i) => v-b[i])); }
export function colorDifferences(a,b) { return Object.fromEntries(visionModels.map(model => [model,labDistance(colorLab(a,model),colorLab(b,model))])); }
// Presentation keys retain the original record identity. A source-supplied name
// distinguishes visibly different owners sharing an upstream entity identifier.
// It never becomes a replacement historical/geographic identity or source fact.
export function displayCategoryKey(identity, name = null) {
  if (identity == null) return null;
  return name == null ? String(identity) : JSON.stringify([String(identity),String(name).normalize('NFC').trim()]);
}

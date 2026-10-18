export function resolve(specifier,context,nextResolve) {
  if(specifier==='../../../scripts/check-effective-geographic-regression.mjs')
    return {url:new URL('./sle-observation-stock-stub.mjs',import.meta.url).href,shortCircuit:true};
  return nextResolve(specifier,context);
}

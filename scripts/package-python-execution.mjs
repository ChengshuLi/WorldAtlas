// One explicit startup policy for package production and selected consumers.
// Site hooks, user/PYTHONPATH imports and ambient bytecode cannot run before
// the package's declared Python source and installed runtime have been admitted.
import {fileURLToPath} from 'node:url';
const helper=fileURLToPath(new URL('./package-python-runtime.py',import.meta.url));
export function packagePythonArgs(args){
  if(!Array.isArray(args)||!args.length||args.some(value=>typeof value!=='string'))throw Error('Explicit Python package arguments required');
  if(args[0]==='-c'){
    if(args.length<2)throw Error('Explicit Python source required');
    return ['-I','-S','-B',helper,'--run-code',...args.slice(1)];
  }
  if(args[0].startsWith('-'))throw Error('Package Python execution requires an explicit source script or -c');
  return ['-I','-S','-B',helper,'--run-script',...args];
}
export function packagePythonProbeArgs(rows){
  return ['-I','-S','-B',helper,'--probe-imports',JSON.stringify(rows)];
}

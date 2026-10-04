import atlas from './worker.js';
import {protectedWorker} from './cloudflare-access.js';

export default protectedWorker(atlas);

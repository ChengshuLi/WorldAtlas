// Cooperative mistake prevention, not authentication. Review agents may inherit
// their parent's CODEX_THREAD_ID, so only author operations use this check.
export function assertAuthorWorkerIdentity(worker, threadID = process.env.CODEX_THREAD_ID) {
  if (threadID && worker !== threadID) {
    throw Error('Worker identity mismatch: new author work must use this chat’s CODEX_THREAD_ID (' + threadID + '). Never copy a worker ID from another chat, claim or checkout. Finish legacy claims with their recorded identity before migrating.');
  }
}

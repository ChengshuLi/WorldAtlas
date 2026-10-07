# Actions quota correction

Refs #1249. This implementation reduces evidence blob REST requests using exact
OID Git transfer, observes actual repository capacity rather than generic
capacity, adds phase/endpoint HTTP accounting, bounded read waits, scheduler
refusal without consuming an attempt, and durable quota retry timestamps.

Executed controls cover ordinary 403, explicit primary and secondary limits,
shared phase deadlines, concurrent probe responses, uncertain writes, complete
and corrupt/missing batch objects, credential isolation, mutable authority
freshness, original integration, review and FIFO protections.

The real transfer probe used the frozen #1231 manifest at merge 8b6835d, with
candidate transport implementation recorded in this PR, not code from that
historical commit. It compared each complete downloaded file against pinned Git
bytes. Its measurements describe that input vintage, not hosted Actions API
validation or production. The temporary 265 MB object store was removed.

Remaining #1249 acceptance after merge: instrument actual registration,
admission, preparation and final validation on trusted main; inspect hosted
accounting and recovery, and reconcile any residual obligation before closing.
The historical 306-call blob inventory was a bound, not actual measured HTTP.
Shared capacity remains finite. No publication, import or geography approval.

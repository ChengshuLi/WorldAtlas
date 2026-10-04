# Database-only production compaction

The user is moving hosting from Sites to Cloudflare while continuing to use Neon. Keep the existing Site read-only; deploying its saved compatible worker and restoring publishing are postponed.

Actual native run37243029988 restored original schema/data but failed at the separate database ACL helper. Use the same exported helper in production and the pinned native fixture: transfer its bounded ACL TOC list through container stdin into writable tmpfs instead of Docker archive copy. Preserve the archive, original ACL statement and all factual bytes.

An explicit `database_only` operation scope and window permits retirement only after original native backup/recipient custody and actual application-login read proof. Compare the unchanged Site24 geographic release/page/cursor/parent/archived/profile/change functions against the retained original heap, then repeat reads after retirement inside the locked owner transaction. Application reads use a separate, genuinely read-only login after the switch commits; they cannot inspect uncommitted view DDL. Global native digest and EXCEPT ALL remain the raw TEXT preservation proofs.

Function modules and their relevant validation/adapter dependencies are pinned to primary c5fce09842a0af2ae05cf6c611f012b6a71befff. The imported attributes resolver changed later, but these selected profile functions do not invoke it; attribute/map endpoints are outside this proof.

This proves live database/API-function compatibility, not deployed HTTP routing/authentication. Old Site24 strict V2 export/catalog pins become incompatible; V4 served routes require the compatible worker on the future hosting deployment. Never set served API parity merely from this proof. Keep the 800000000-byte final capacity gate, strict catalog/runtime guards and full row preservation. No provider branch, plan upgrade, scientific edit or restored-write claim.

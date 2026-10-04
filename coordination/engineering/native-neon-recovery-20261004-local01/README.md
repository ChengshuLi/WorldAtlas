# Actual Neon native restore setup correction

Original production run37240144463 captured an encrypted22,510,251byte native dump and confirmed source/target cleanup, but failed isolated restoration. Private recipient decryption preserved the original archive outside Git; metadata retains GRANT on database neondb and default ACLs for cloud_admin/neon_superuser. Prior synthetic target omitted those actual names.

Create only an isolated neondb database and inert NOLOGIN provider-role placeholders, restore original owner/ACL statements as isolated postgres, and verify unchanged factual/owner catalog readback. Provider credentials/memberships remain excluded. Add native fixture database/default ACL roundtrip to prevent repeating this gap. No production source SQL/data/catalog/pin change. Actual successful production native restore remains required after merge; captured original is not yet a recovery certificate.

Source failed-run proof https://github.com/ChengshuLi/WorldAtlas/actions/runs/37240144463; source failure settlement is preserved on original issue51. No new benchmark/scientific or capacity metric is claimed by this repair.

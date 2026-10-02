# Research media without application changes

Use the generic media uploader for licensed images, audio, video, documents and lawful source archives. Luna supplies data files and runs existing commands; it does not change application code, the schema, geographic identities or map assets. Media bytes go to the existing content-addressed object store. Research claims contain stable `media_id` links, never embedded bytes or base64 files.

The service must support provenance-preserving uploads and `GET /api/media/{id}?metadata=1` with `X-Atlas-Media-Metadata-Version: 1`. The uploader refuses older deployments before its first write so immutable objects cannot accidentally lose their supplied provenance. A missing capability is an engineering deployment task, not a reason to remove the evidence fields.

## Prepare dependencies and original files

First import the needed source identities using the generic [research content workflow](RESEARCH_IMPORT_WORKFLOW.md). Existing sources can be reused after inspecting `GET /api/catalog/sources`. Keep exact source IDs, names, URLs, licenses, vintage and status; the uploader compares these six fields against the hosted source before uploading anything. Preserve `url: null` when an existing source has no URL; do not invent one. The media provenance still needs a lawful reference URL. Source records are evidence dependencies, not substitutes for the media object's own license and attribution.

Preserve each original file and establish its exact size and SHA-256 with standard shell commands:

```sh
sha256sum campaign-media/audio/instrument.wav
stat --format=%s campaign-media/audio/instrument.wav
```

Use a JSON manifest beside the files. Paths are relative to its directory; parent traversal, absolute paths and symlinks escaping that directory are rejected. Each file must be nonempty and at most **20 MiB**. A campaign supports at most 1,000 objects and a 1 MiB manifest; divide larger collections into separate campaigns. Files are read and uploaded one at a time, without aggregating all media bytes in memory.

This is a template, not historical evidence. Replace every placeholder with inspected source information and the actual file proof; no default license, attribution or historical date is inferred:

```json
{
  "version": 1,
  "kind": "research-media",
  "campaign_id": "<stable campaign ID>",
  "sources": [
    {
      "id": "<existing source ID>",
      "name": "<exact hosted source name>",
      "url": "<exact hosted source URL>",
      "license": "<exact hosted source license>",
      "vintage": "<exact hosted source vintage>",
      "status": "<historical, reference, estimate or example>"
    }
  ],
  "objects": [
    {
      "id": "<stable media ID>",
      "path": "audio/instrument.wav",
      "sha256": "<64 lowercase hexadecimal SHA-256 characters>",
      "bytes": 123,
      "mime": "audio/wav",
      "name": "<recognizable media title>",
      "license": "<verified media license>",
      "attribution": "<required author and attribution>",
      "source_id": "<existing source ID>",
      "redistribution_permitted": true,
      "provenance": {
        "source_url": "<lawful original media or evidence URL>",
        "retrieved_at": "<actual YYYY-MM-DD retrieval date>",
        "reference": "<publication/version/object reference and research context>"
      }
    }
  ]
}
```

`redistribution_permitted: true` is the researcher's explicit rights assertion. The program validates its presence and retains the provided license and attribution; it does not verify copyright or invent permission. Unknown or restricted redistribution does not qualify for this upload workflow. Preserve lawful references and research notes instead of uploading restricted bytes.

`retrieved_at` records source retrieval, not the artifact's historical date. It accepts a valid `YYYY-MM-DD` or UTC ISO timestamp. A separate sourced media link may have a supported historical interval. Do not turn an observation/retrieval date into a claimed event date. Provenance is a JSON object limited to 4,096 UTF-8 bytes; oversized descriptive material belongs in a separately preserved lawful source document.

Optionally add `source_archive` inside `provenance`:

```json
{"url":"<lawful source archive URL>","sha256":"<archive SHA-256>","media_id":"<already registered archive media ID>"}
```

The `media_id` is optional. When present, its existing metadata must match the supplied archive digest; upload and verify the archive in an earlier campaign first. The uploader does not fetch external archive URLs or independently verify externally referenced archive bytes. New uploaded objects receive full byte verification; an archive pointer alone is not that proof. Restricted archives may use lawful references rather than an uploaded object.

## Validate, upload and resume

Preflight checks every original file and manifest without network requests or credentials:

```sh
node scripts/upload-research-media.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ campaign-media/media.json --dry-run
```

Upload using the private **Site service credential**, through hidden terminal input:

```sh
node --use-env-proxy scripts/upload-research-media.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ campaign-media/media.json
```

Paste the existing Site credential JSON into the hidden prompt. No database-owner credential or model API key is needed. Never place credentials in arguments, environment dumps, files, receipts or Git. The target must be the confirmed HTTPS Site origin; all authenticated requests stay there. Redirects are refused, including upload redirects. The current audience remains unchanged.

The CLI verifies source dependencies and API capability before uploading. Each new object uses the exact supplied metadata and `media/{sha256}` storage key. A reused digest has one registered identity; reuse that identity for more links instead of manufacturing a duplicate object ID. Existing IDs with different metadata stop the operation. The tool never rewrites an earlier object, claim, source or license.

After each object, it rereads immutable metadata and verifies the entire remote object's length, MIME and SHA-256. Only then does it write a verified receipt. `media-upload-receipts.json` is fsynced, atomically replaced and hashed after each result. It contains nonsensitive manifest/object proofs and verification receipts, without credentials or media bytes. A failed campaign preserves earlier verified objects and an explicit error code.

Rerun the identical command to resume. Completed objects are reread and checked without another POST. A lost or truncated upload response triggers a direct identity reread before retrying; a successful commit is verified rather than uploaded again. Transient retries are bounded. Changed source expectations, files, provenance, claims or receipt hashes stop the campaign; preserve the old campaign and create a reviewed new one. Source/metadata conflicts require investigation, not deletion or silent edits to original evidence. Service capacity or missing API capability errors should be handed to the technical maintainer with the retained checkpoint.

## Link media to historical subjects

Once objects are verified, add `media_links` through the existing research compiler/importer. Each link supplies a stable link ID, existing `media_id`, existing entity ID, role, caption if supported, source ID and provenance metadata. A complete supported `[valid_from, valid_to)` interval is optional; leave both dates absent when historical dating is unknown. Examples require explicit `is_example: 1` and remain opt-in. Different sourced interpretations, captions and historical roles use separate immutable links without changing the media bytes.

The order is **source-only research campaign → media upload campaign → media-link research campaign**. Entity/type dependencies for links can be prepared in the normal content campaign. The uploader never injects binary content into `/api/records/import` and does not require redeploying the website for a factual media addition.

## Preserve the handoff

Commit the manifest, original licensed files that fit repository limits or a lawful restoration manifest, license/attribution research, source campaign receipts, upload receipts, media-link bundles and read-back results. Larger media should stay in approved licensed object storage with restorable source URLs and byte proofs, rather than exceeding the repository's per-file limits. Record completed scope and open source/rights/date questions in `docs/HANDOFF_STATUS.md`, then push branch `work` so a fresh Luna chat can resume from Git. These receipts establish accepted immutable bytes and metadata, not exhaustive historical truth or unlimited storage capacity.

Engineering verification:

```sh
node --test test/research-media-upload.test.mjs
```

The tests use the actual hosted Worker and `registerMedia` with disposable D1/R2 fixtures. They cover retained provenance, checksums, identical resume, partial checkpoints, source and metadata mismatches, altered bytes, tampered receipts, ambiguous responses, source-archive pointers, older API rejection, URL/path bounds and credential-safe redirects. They create no production records or historical facts.

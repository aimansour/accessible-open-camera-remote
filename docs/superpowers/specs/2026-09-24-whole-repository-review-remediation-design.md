# Whole-repository review remediation design

Date: 2026-09-24. The user asked to fix the whole-repository GPT-6 Astra High review findings. This work stays in the current repository, is implemented by the current agent, and is not published until the user's NVDA acceptance.

## Intended behavior

The page must only act on the exact phone files and folder that it presented when the user selected them. Camera success must describe the latest command and an actual new finalized recording. Stopping verification must finish the active check before the user handles the phone. Previously verified completed videos remain copyable when verification is off. Transfer messages must state only what was proved, and a healthy large copy must not be killed solely for taking five minutes.

## Selection and file identity

Keep the last loaded catalog folder separately from the editable folder input. Changing the input clears the displayed catalog and selection immediately, hides its file actions and confirmation, and invalidates in-flight catalog responses. A new catalog response binds its rows to the returned folder. Every browser file request includes the selected entries' name, size, and modified time. The server compares supplied identity fields with a fresh listing before any mutation; mismatch rejects the operation. Existing non-browser API callers may omit these fields for compatibility, but the browser always sends them. Running transfer/delete jobs include their source folder; completion only removes rows or clears selection when that folder matches the currently displayed catalog. This also covers switching folders while an operation is running.

## Camera command and verification lifecycle

The final Stop verifier checks command generation and verification enablement after every awaited ADB operation, including the baseline refresh, before it writes state, baseline, tone, or settlement. A newer command therefore cannot be completed by an older verifier. Manual `start_verification` is serialized and owned by a cancellable task/lifecycle generation; `stop_verification` cancels and awaits it. No ADB reads or state writes from that request continue after Stop verification returns.

The camera baseline is reconciled after verified phone file changes in its recording folder. A rename contributes its new entry to the baseline even if a recording command has started meanwhile; deletion and move remove stale entries. The server also refreshes the baseline from its verified listing before file operations, so a fixture or external addition seen by the server cannot be mistaken for a new recording. A failed refresh leaves recording finalization uncertain instead of declaring success. Camera key dispatch remains independent of the file lock.

## Copy, move, and transport truth

Copy remains available while verification is off only for entries from a catalog loaded during verified idle; the server's cached catalog and `copy_one` size/hash checks remain authoritative. Rename, move, and delete remain unavailable without confirmed idle. An uncertain move result identifies whether the PC copy was verified; an exception before a verified destination is reported without that claim. The browser uses that distinction in Arabic and English.

ADB pull uses a configurable transfer timeout rather than a fixed five-minute ceiling. The default permits large recordings and is documented. A timed-out or failed transfer still removes its partial file and never publishes it as verified.

## Validation and boundaries

For each reviewed defect, write a failing regression test or executable browser probe, observe the expected failure, implement one focused fix, and rerun it plus the complete suite. Use only random test-created phone files for device mutation tests. Rebuild the Windows package locally, verify its bundled assets and page in a browser, and retain it for the user's NVDA acceptance. Do not push, tag, publish, or touch personal recordings.

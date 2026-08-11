# Stability and Diagnostics

This document defines the v0.0.04 Early Preview failure policy. It does not
introduce a new project format or production feature.

## Severity and response

- P0: data loss, project corruption, incorrect save, or a valid project that cannot load.
- P1: crash, startup failure, save/export failure, or invalid data created by Undo/Redo.
- P2: incorrect rendering, selection/timeline state, or stale cache output.
- P3: localization, DPI, focus, clipping, or disabled-state UI errors.
- P4: avoidable work, unbounded memory, and workflow friction.

P0 and P1 take precedence over performance work. Silent repair is not used for
damaged v8 pixel payloads, missing frame-layer payloads, duplicate identities,
dangling resource references, non-finite JSON numbers, or future formats.

## Runtime log

At startup, `QStandardPaths.AppLocalDataLocation/logs` is used. The normal file
is `pixel_effect_maker.log`; each file is limited to approximately 2 MiB with
at most three backups. If the directory or handler cannot be created, startup
continues and a short message is attempted on stderr.

The log includes application/build/format/runtime metadata, operation outcomes,
exception type/message/traceback, and selected performance events. It must not
dump RGBA arrays, Base64 payloads, full project JSON, clipboard contents, all
settings, or asset contents. Operation paths are normally reduced to a filename.

`Help > Copy Diagnostic Information` copies version, build channel, format,
optional build commit, OS, Python, PySide6/Qt, and log location. It does not copy
the current project, its pixel data, or its asset contents.

## Corruption and future formats

Load fully parses and validates a candidate before replacing the current model.
Invalid JSON, non-finite numbers, malformed compact payload metadata/Base64/zlib/
checksum, duplicate IDs, missing v8 layer payloads, invalid enums, and dangling
references reject the whole candidate. Formats newer than 8 receive a distinct
safe-rejection message and are never rewritten by this version. v1-v7 retain
their existing in-memory migration and are written as v8 only after an explicit
successful save.

## Save and Dirty policy

Save serializes before opening the target-side temporary file, then writes,
flushes, fsyncs, closes, and atomically replaces the destination. Any failure
removes the temporary file where possible and preserves the previous destination,
project path, and Dirty state. A successful save marks Clean only when no newer
edit revision appeared during the save.

A Dirty close presents Save, Discard, and Cancel. Save failure or Save As cancel
keeps the window open. Discard closes without writing. Cancel changes nothing.

## Bug reports and known environment limits

Report reproduction steps, the diagnostic text, and the bounded log. Do not send
private project files unless intentionally requested. Automated tests use an
explicit `C:\Dev` pytest base directory because the default Windows Temp ACL can
be environment-specific; ACL ownership is not changed.

Offscreen Qt tests cover model and widget state but are not a substitute for
manual Windows checks at 100%, 125%, and 150% DPI. Python `tracemalloc` cannot
measure all Qt-native QImage/QPixmap memory. The preview PyInstaller spec remains
console-enabled and no installer, signature, recovery, or auto-save is provided.

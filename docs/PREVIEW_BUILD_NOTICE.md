# Early Preview Build Notice

`PREVIEW_BUILD`, `PREVIEW_LABEL`, and `PREVIEW_NOTICE_REVISION` live in `app/version.py`. They describe the distribution channel without changing `Pixel Effect Maker v0.0.04` or project `FORMAT_VERSION = 8`.

## Display policy

Normal launches and launches with an explicit `.peffect.json` path show the notice before the Startup dialog or project loading. `--version`, `--check`, and tests that instantiate UI components directly bypass the modal startup flow. Reject, window close, and Escape stop startup; only **I Understand — Start** continues.

The startup checkbox stores acceptance in QSettings under:

```text
preview_notice/accepted/0.0.04-format8-revision1
```

The key includes app version, project format, and notice revision. A future revision therefore appears again. Read failures default to showing the notice. Acceptance is never part of project JSON.

## Manual access

**Help > Project Overview and Development Status…** always opens the same localized content, regardless of prior acceptance. Manual mode has only a Close button and does not show or modify the acceptance checkbox.

## UI and localization

The dedicated QDialog uses a scrollable, word-wrapped layout with selectable text, no horizontal scrollbar, keyboard focus, Enter confirmation, and Escape rejection. Korean and English content is stored in the central `LocalizationService` catalog.

## Disabling for a production build

Set `PREVIEW_BUILD = False` in `app/version.py`. Do not alter the public version or project format merely to change the distribution channel. The Help overview remains available while the automatic startup notice is disabled.
# Diagnostics after acceptance

The notice acceptance remains revision-scoped in QSettings. Failure to read or
write that preference is logged but does not block startup; read failure safely
shows the notice again. Users can reopen the overview and copy privacy-limited
diagnostic information from Help.

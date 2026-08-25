"""Central application version information."""

APP_NAME = "Pixel Effect Maker"
__version__ = "0.0.12"
VERSION_LABEL = f"v{__version__}"

# Distribution channel metadata is intentionally independent from the public
# application version and the project file format.
PREVIEW_BUILD = True
PREVIEW_LABEL = "Early Preview Build"
PREVIEW_NOTICE_REVISION = 1
BUILD_COMMIT: str | None = None


def get_display_name() -> str:
    """Return the application name with its user-facing version label."""
    return f"{APP_NAME} {VERSION_LABEL}"

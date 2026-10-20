"""Optional project-local settings; explicit process environment always wins."""
from pathlib import Path
from dotenv import load_dotenv
from runtime_paths import configure_runtime, is_frozen, resource_dir


def load_settings(directory=None):
    paths = configure_runtime()
    # Source checkouts retain the familiar root .env. Packaged builds keep
    # mutable settings beside user data rather than inside a signed app bundle.
    if directory:
        root = Path(directory)
    elif is_frozen():
        root = paths['config']
    else:
        root = resource_dir()
    load_dotenv(root / '.env', override=False, encoding='utf-8-sig', interpolate=False)

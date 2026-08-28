"""Distribution identity for installed and source-checkout execution."""
import re
from importlib import metadata
from pathlib import Path


_PROJECT_SECTION = re.compile(r"^\[project\][ \t]*(?:#.*)?$")
_SECTION = re.compile(r"^\[[^]]+\][ \t]*(?:#.*)?$")
_VERSION = re.compile(r'^version[ \t]*=[ \t]*"([^"\r\n]+)"[ \t]*(?:#.*)?$')


def _source_version() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    in_project = False
    versions = []
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if _PROJECT_SECTION.fullmatch(stripped):
            in_project = True
            continue
        if _SECTION.fullmatch(stripped):
            in_project = False
            continue
        if in_project:
            match = _VERSION.fullmatch(stripped)
            if match:
                versions.append(match.group(1))
    if len(versions) != 1:
        raise RuntimeError("expected exactly one project.version in %s" % pyproject)
    return versions[0]


def distribution_version() -> str:
    """Return installed metadata identity, with a source-checkout fallback."""
    try:
        return metadata.version("codex-worker")
    except metadata.PackageNotFoundError:
        return _source_version()

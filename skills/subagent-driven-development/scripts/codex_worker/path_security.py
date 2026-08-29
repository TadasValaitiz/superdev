"""Shared owner/sticky-ancestor policy for worker-controlled filesystem paths."""
import os
import stat
from pathlib import Path
from typing import Optional


def unsafe_ancestor(path: Path) -> Optional[Path]:
    """Accept owner-safe ancestors and root-owned sticky temp roots, never unsafe links."""
    absolute = Path(os.path.abspath(str(path)))
    current = Path(absolute.anchor)
    controlled = False
    shared_sticky = False
    for component in absolute.parts[1:]:
        current = current / component
        try:
            data = os.lstat(current)
        except OSError:
            return current
        if stat.S_ISLNK(data.st_mode):
            if current.parent != Path(absolute.anchor) or data.st_uid != 0:
                return current
            try:
                data = os.stat(current)
            except OSError:
                return current
        mode = stat.S_IMODE(data.st_mode)
        sticky = bool(mode & stat.S_ISVTX)
        shared = sticky and bool(mode & 0o022)
        if (not stat.S_ISDIR(data.st_mode)
                or mode & 0o022 and not sticky):
            return current
        if data.st_uid == os.getuid():
            controlled = True
        elif shared:
            shared_sticky = True
            controlled = False
        elif data.st_uid != 0 or controlled or shared_sticky:
            return current
    return None

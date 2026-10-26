from __future__ import annotations

import platform
import threading
from pathlib import Path

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from devmate.context.indexers.code_parser import ALL_EXTENSIONS
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

# Debounce delay: Wait this long after the last event before acting.
# Editors often emit multiple events per save (write, flush, rename).
_DEBOUNCE_SECONDS = 1.5


def _get_observer() -> Observer:
    """Return the best available watchdog observer for current OS.
    Windows uses PollingObserver to avoid edge cases under heavy load.
    """
    if platform.system() == "Windows":
        return PollingObserver(timeout=2)
    return Observer()


class _CodebaseEventHandler(FileSystemEventHandler):
    """Translates raw filesystem events into debounced indexer calls."""

    def __init__(self, on_change=None) -> None:
        self._timers: dict[str, threading.Timer] = {}
        self._on_change = on_change

    def _is_indexable(self, path: str) -> bool:
        """True if the file extension is one the indexer knows how to parse."""
        return Path(path).suffix.lower() in ALL_EXTENSIONS

    def _schedule(self, action: str, filepath: str) -> None:
        """Schedule a debounced indexer call for filepath."""
        existing = self._timers.pop(filepath, None)
        if existing:
            existing.cancel()

        timer = threading.Timer(_DEBOUNCE_SECONDS, self._run, args=(action, filepath))
        timer.daemon = True
        timer.start()
        self._timers[filepath] = timer

    def _run(self, action: str, filepath: str) -> None:
        """Executed after the debounce window expires."""
        self._timers.pop(filepath, None)
        from devmate.context.indexers.semantic_chroma import (
            index_single_file,
            remove_file_from_index,
        )
        if action == "delete":
            remove_file_from_index(filepath)
        else:
            index_single_file(filepath)
        if self._on_change is not None:
            self._on_change()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_indexable(event.src_path):
            self._schedule("upsert", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_indexable(event.src_path):
            self._schedule("upsert", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_indexable(event.src_path):
            self._schedule("delete", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            if self._is_indexable(event.src_path):
                self._schedule("delete", event.src_path)
            if self._is_indexable(event.dest_path):
                self._schedule("upsert", event.dest_path)


def start_watcher(repo_path: str, on_change=None) -> Observer:
    """Start a background filesystem observer on repo_path."""
    handler = _CodebaseEventHandler(on_change=on_change)
    observer = _get_observer()
    observer.schedule(handler, repo_path, recursive=True)
    observer.daemon = True
    observer.start()
    logger.info(f"Devmate Watchdog started on {repo_path} (backend: {type(observer).__name__})")
    return observer


def stop_watcher(observer: Observer) -> None:
    """Cleanly stop the observer and wait for its thread to finish."""
    observer.stop()
    observer.join()
    logger.info("Devmate Watchdog stopped")

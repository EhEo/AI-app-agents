# 에이전트 로그 파일 감시 — append-only log.md 실시간 읽기
from __future__ import annotations

import queue
import threading
from pathlib import Path

# log.md 표준 태그 6종 (Reference Code 기반)
LOG_TAGS = ("DECISION", "WORKER_CALL", "VERIFICATION", "ERROR", "APPROVAL", "COMPLETE")


class LogWatcher:
    """tasks/<task>/log.md를 tail하여 queue에 라인을 쌓는다."""

    def __init__(self, log_path: Path, out_queue: queue.Queue[str]) -> None:
        self._path = log_path
        self._queue = out_queue
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        self._stop.set()

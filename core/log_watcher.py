# 에이전트 로그 파일 감시 — 에이전트 응답 로그 + tasks/log.md 통합 감시
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import TypedDict

# log.md 표준 태그 6종 (Reference Code 기반)
LOG_TAGS = ("DECISION", "WORKER_CALL", "VERIFICATION", "ERROR", "APPROVAL", "COMPLETE")

# 에이전트 응답 로그 파일 접두어 → 에이전트 키 매핑
_AGENT_PREFIXES: dict[str, str] = {
    "gemini":  "gemini-main",
    "codex":   "codex-main",
    "critic":  "codex-critic",
    "claude":  "claude-main",
}


class LogEvent(TypedDict):
    """우측 패널로 전달하는 이벤트 단위."""
    source: str       # "agent_response" | "task_log"
    agent: str        # 에이전트 키 (빈 문자열이면 시스템 메시지)
    tag: str          # log.md 태그 또는 빈 문자열
    query: str        # 에이전트 응답 로그의 쿼리 부분 (없으면 빈 문자열)
    text: str         # 표시할 본문


class LogWatcher:
    """두 가지 로그 소스를 통합 감시해 queue에 LogEvent를 쌓는다.

    1. <project>/.agents-dev/log/*.log  — 에이전트 응답 완성 감지 (v1 방식)
    2. <project>/tasks/<task>/log.md    — append-only 태스크 로그 신규 라인 감지
    """

    def __init__(self, out_queue: queue.Queue[LogEvent]) -> None:
        self._queue = out_queue
        self._project: Path | None = None
        self._current_task: str | None = None

        # .agents-dev/log/ 감시 상태
        self._seen_logs: set[str] = set()
        self._log_mtimes: dict[str, float] = {}
        self._skip_until: dict[str, float] = {}

        # tasks/*/log.md 감시 상태 (파일 포지션 추적)
        self._task_log_pos: dict[Path, int] = {}

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ── 공개 인터페이스 ─────────────────────────────────────────────────────

    def set_project(self, project: Path) -> None:
        """감시 대상 프로젝트 폴더를 변경한다."""
        self._project = project
        log_dir = project / ".agents-dev" / "log"
        self._seen_logs = {p.name for p in log_dir.glob("*.log")} if log_dir.exists() else set()
        self._log_mtimes.clear()
        self._task_log_pos.clear()

    def set_current_task(self, task_name: str | None) -> None:
        """현재 활성 태스크를 설정해 해당 log.md를 감시한다."""
        self._current_task = task_name

    def skip_next(self, agent_prefix: str, duration: float = 60.0) -> None:
        """에이전트 직접 전송 직후 호출 — 중복 표시 방지용 스킵 타이머."""
        self._skip_until[agent_prefix] = time.monotonic() + duration

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def poll(self) -> None:
        """메인 스레드 폴링 루프에서 호출 (스레드 미사용 시 대안)."""
        self._poll_agent_logs()
        self._poll_task_log()

    # ── 내부 구현 ───────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._poll_agent_logs()
            self._poll_task_log()
            time.sleep(0.08)  # 80ms 폴링

    def _poll_agent_logs(self) -> None:
        """에이전트 응답 로그 파일이 완성되면 이벤트를 큐에 넣는다."""
        if not self._project:
            return
        log_dir = self._project / ".agents-dev" / "log"
        if not log_dir.exists():
            return

        for path in log_dir.glob("*.log"):
            if path.name in self._seen_logs:
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            mtime = st.st_mtime
            if self._log_mtimes.get(path.name) != mtime:
                self._log_mtimes[path.name] = mtime
                continue  # 아직 변경 중
            # 파일 끝 64바이트로 완성 여부 확인
            try:
                with open(path, "rb") as f:
                    f.seek(max(0, st.st_size - 64))
                    tail = f.read().decode("utf-8", errors="replace")
            except OSError:
                continue
            if "=== END" not in tail:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            self._seen_logs.add(path.name)
            self._log_mtimes.pop(path.name, None)
            self._emit_agent_response(path.name, text)

    def _emit_agent_response(self, filename: str, text: str) -> None:
        agent_key = ""
        for prefix, key in _AGENT_PREFIXES.items():
            if filename.startswith(prefix):
                until = self._skip_until.get(prefix, 0.0)
                if time.monotonic() < until:
                    self._skip_until.pop(prefix, None)
                    return
                agent_key = key
                break
        query = _section(text, "=== QUERY ===", "=== RESPONSE ===").strip()
        response = _section(text, "=== RESPONSE ===", "=== END").strip()
        if not response:
            return
        self._queue.put(LogEvent(
            source="agent_response",
            agent=agent_key,
            tag="",
            query=query,
            text=response,
        ))

    def _poll_task_log(self) -> None:
        """현재 태스크 log.md의 새로 추가된 라인을 이벤트로 변환한다."""
        if not self._project or not self._current_task:
            return
        log_path = self._project / "tasks" / self._current_task / "log.md"
        if not log_path.exists():
            return

        pos = self._task_log_pos.get(log_path, 0)
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                new_lines = f.readlines()
                self._task_log_pos[log_path] = f.tell()
        except OSError:
            return

        for line in new_lines:
            line = line.rstrip()
            if not line or line.startswith("<!--"):
                continue
            tag = _extract_tag(line)
            self._queue.put(LogEvent(
                source="task_log",
                agent=_agent_from_log_line(line),
                tag=tag,
                query="",
                text=line,
            ))


# ── 모듈 수준 유틸 ─────────────────────────────────────────────────────────────

def _section(text: str, start: str, end: str) -> str:
    """텍스트에서 start ~ end 사이 구간을 잘라 반환한다."""
    s = text.find(start)
    if s < 0:
        return ""
    s += len(start)
    e = text.find(end, s)
    return text[s:e] if e >= 0 else text[s:]


def _extract_tag(line: str) -> str:
    """[YYYY-MM-DD HH:MM] [TAG] ... 형식에서 TAG를 추출한다."""
    import re
    m = re.search(r"\[([A-Z_]+)\]", line)
    if m and m.group(1) in LOG_TAGS:
        return m.group(1)
    return ""


def _agent_from_log_line(line: str) -> str:
    """log.md 라인에서 에이전트 키를 추론한다 (없으면 빈 문자열)."""
    lower = line.lower()
    for prefix, key in _AGENT_PREFIXES.items():
        if prefix in lower:
            return key
    return ""

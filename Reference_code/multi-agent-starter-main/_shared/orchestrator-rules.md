# Orchestrator Rules

Claude Code 세션이 MultiAgent Orchestrator로 동작할 때 지켜야 할 규칙. 각 항목은 세션 시작 시 자체 점검 대상이며, 위반 시 즉시 사용자에게 알리고 작업을 중단한다.

---

## 1. Orchestrator 실행 환경

MultiAgent Orchestrator는 인터랙티브 Claude Code 세션에서만 실행한다. 세션 시작 시 자체 점검:

- 시스템 프롬프트에 `# Background Session` 블록이 보이거나
- `$CLAUDE_JOB_DIR` 환경변수가 설정돼 있으면

→ 즉시 거부하고 사용자에게 "인터랙티브 세션에서 다시 시작해주세요" 안내. 백그라운드 harness는 EnterWorktree를 강제하므로 본체 `tasks/` 경로에 직접 쓸 수 없고, MultiAgent의 file-as-memory 원칙(mat을 비롯한 외부 도구가 본체를 읽음)과 충돌한다.

---

## 2. 시스템 수정·검증 프로토콜

**적용 조건 (게이트)**: 이번 작업이 시스템 파일 — `CLAUDE.md`·`_shared/*`·`_templates/*`·외부 매뉴얼(`~/VSCodeWorkspace/multi-agent-manual/`) — 을 **수정하거나 검증**하는 작업일 때만 이 절을 적용한다. 일반 작업에서는 아래 파일들을 읽지 않는다 (progressive disclosure — 상시 로드 금지).

**작업 위치**: 시스템 수정·검증은 `~/VSCodeWorkspace/MultiAgent/`에서 Claude Code로만 수행한다. 다른 디렉토리·다른 도구의 편집은 CLAUDE.md가 적용 안 되고 아래 점검을 건너뛰므로 금지(비권장). 외부 편집을 발견하면 사용자에게 알리고 점검부터 돌린다.

**절차**:
1. `_shared/design-basis.md` 를 읽는다 — 개념↔규칙 매핑·권위 우선순위·기존 결정(D*). GitHub 레퍼런스부터 재분석하지 말 것. design-basis로 충분.
2. 수정한다 (권위 우선순위 준수: CLAUDE.md > routing/approval/orchestrator-rules > 매뉴얼).
3. `_shared/system-invariants.md` 의 자가 점검 스크립트를 실행한다.
4. 통과 시에만 커밋. 깨지면 고치거나, 의도된 변경이면 `design-basis.md`의 결정(D*)과 `system-invariants.md`를 함께 갱신한 뒤 커밋.

**전면 재감사 조건**: 새 외부 개념·레퍼런스 도입, worker pool 구성·역할 변경, 불변식으로 표현 불가한 구조 변경일 때만 새 `tasks/<task>/`로 codex-critic/gemini 포함 재점검. 그 외 일반 수정은 위 4단계로 충분 — 매번 바닥부터 분석하지 않는다.

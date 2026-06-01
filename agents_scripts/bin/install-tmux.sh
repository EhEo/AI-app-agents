#!/usr/bin/env bash
# install-tmux.sh — Git Bash(MSYS2)에 tmux 를 관리자 권한 없이 ~/bin 에 설치한다.
#   tmux.exe + libevent DLL 만 ~/bin 에 두고, msys-2.0.dll 은 Git Bash 의 /usr/bin 것을
#   그대로 공유한다(다른 버전 msys-2.0.dll 을 두면 cygheap base mismatch 로 깨짐).
#   다운로드한 패키지는 SHA256 으로 무결성 검증 후에만 설치한다.
# 사용법:  bash ~/bin/install-tmux.sh
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/bin:$PATH"

BIN="$HOME/bin"; mkdir -p "$BIN"
TMUX_VER="${TMUX_VER:-3.6-1}"
LIBEVENT_VER="${LIBEVENT_VER:-2.1.12-4}"
BASE="${MSYS2_REPO:-https://repo.msys2.org/msys/x86_64}"

# 기본 버전의 SHA256 핀. 버전을 오버라이드하면 해당 해시가 없어 검증을 건너뛴다(경고).
SHA_tmux_3_6_1="23e101529246b0e33241e93c8b14870aeeb2896d81c069a20b696c4b835aebaa"
SHA_libevent_2_1_12_4="c2f087afa1718f5015086bd24afebe21423dbfce2525fd0b3a6b179825ee7904"

if command -v tmux >/dev/null 2>&1 && tmux -V >/dev/null 2>&1; then
  echo "✓ tmux 이미 사용 가능: $(tmux -V)"; exit 0
fi
command -v curl      >/dev/null 2>&1 || { echo "✗ curl 가 필요합니다" >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { echo "✗ sha256sum 가 필요합니다" >&2; exit 2; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

verify() {  # $1=파일경로 $2=기대 SHA256 (빈 값이면 검증 생략)
  local exp="$2"
  if [ -z "$exp" ]; then
    echo "⚠ 핀된 해시 없는 버전 — 무결성 검증 생략: $(basename "$1")" >&2
    return 0
  fi
  echo "$exp *$1" | sha256sum -c - >/dev/null 2>&1 \
    || { echo "✗ SHA256 불일치 — 손상/변조 의심, 설치 중단: $(basename "$1")" >&2; exit 2; }
}

tmux_exp=""; [ "$TMUX_VER" = "3.6-1" ]       && tmux_exp="$SHA_tmux_3_6_1"
le_exp="";   [ "$LIBEVENT_VER" = "2.1.12-4" ] && le_exp="$SHA_libevent_2_1_12_4"

echo "▶ 다운로드 (tmux $TMUX_VER, libevent $LIBEVENT_VER) …"
curl -fsSL -o "$TMP/tmux.zst"     "$BASE/tmux-$TMUX_VER-x86_64.pkg.tar.zst"
curl -fsSL -o "$TMP/libevent.zst" "$BASE/libevent-$LIBEVENT_VER-x86_64.pkg.tar.zst"
verify "$TMP/tmux.zst"     "$tmux_exp"
verify "$TMP/libevent.zst" "$le_exp"

extract() {  # $1=.zst → $TMP 로 tar 해제
  if command -v zstd >/dev/null 2>&1; then
    zstd -dc "$1" | tar -xf - -C "$TMP"
  elif python -c "import compression.zstd" >/dev/null 2>&1; then
    python - "$1" "$TMP" <<'PY'
import sys, io, tarfile
import compression.zstd as z
from pathlib import Path
tf = tarfile.open(fileobj=io.BytesIO(z.decompress(Path(sys.argv[1]).read_bytes())))
tf.extractall(sys.argv[2], filter='data')
PY
  else
    echo "✗ .zst 해제 도구 없음 (zstd 바이너리 또는 Python 3.14 의 compression.zstd 필요)" >&2
    exit 2
  fi
}
extract "$TMP/tmux.zst"
extract "$TMP/libevent.zst"

cp "$TMP/usr/bin/tmux.exe" "$BIN/tmux.exe"
cp "$TMP"/usr/bin/msys-event*.dll "$BIN"/    # libevent (msys-2.0.dll 은 복사 안 함)
chmod +x "$BIN/tmux.exe" 2>/dev/null || true

echo "✓ 설치 완료: $("$BIN/tmux.exe" -V)  → $BIN"
echo "  (msys-2.0.dll 은 Git Bash /usr/bin 것을 공유합니다)"

# 공용 커스텀 위젯 — RoundBtn·RoundInput (v1 agents_gui.py에서 이전, 테마 독립화)
from __future__ import annotations

import tkinter as tk
from config import FONT_KO


# ── 내부 도형 유틸 ─────────────────────────────────────────────────────────────

def _round_rect(cv: tk.Canvas, x1, y1, x2, y2, r, fill, *, tag=None) -> None:
    kw: dict = {"fill": fill, "outline": fill}
    if tag:
        kw["tags"] = tag
    cv.create_polygon(
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
        smooth=True, **kw,
    )


def _darken(hex_color: str, factor: float = 0.80) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"


# ── RoundBtn ──────────────────────────────────────────────────────────────────

class RoundBtn(tk.Canvas):
    """둥근 모서리 Canvas 버튼."""

    def __init__(self, parent, text: str, command, color: str,
                 radius: int = 10, fontsize: int = 9, **kw):
        kw.setdefault("cursor", "hand2")
        outer = parent.cget("bg") if hasattr(parent, "cget") else "#212121"
        super().__init__(parent, bg=outer, highlightthickness=0, bd=0, **kw)
        self._text = text
        self._color = color
        self._radius = radius
        self._cmd = command
        self._fontsize = fontsize
        self.bind("<Configure>", lambda _: self._draw())
        self.bind("<Enter>",     lambda _: self._draw(True))
        self.bind("<Leave>",     lambda _: self._draw(False))
        self.bind("<Button-1>",  lambda _: command())

    def _draw(self, hover: bool = False) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        _round_rect(self, 0, 0, w, h, self._radius,
                    _darken(self._color) if hover else self._color)
        self.create_text(w // 2, h // 2, text=self._text, fill="white",
                         font=(FONT_KO, self._fontsize))

    def retheme(self, outer_bg: str) -> None:
        self.config(bg=outer_bg)
        self._draw()


# ── RoundInput ────────────────────────────────────────────────────────────────

class RoundInput(tk.Canvas):
    """Canvas 배경 + 다중 줄 Text + 전송 버튼이 결합된 둥근 입력 위젯.

    Enter → 전송 / Shift+Enter → 줄바꿈 / 자동 높이 확장.
    """

    _H_MIN  = 38
    _H_MAX  = 112
    _LINE_H = 18
    _PAD    = 14
    _BTNW   = 34
    _PH     = "무엇이든 물어보세요"

    def __init__(self, parent, on_send,
                 btn_color: str,
                 bg_input: str = "#2f2f2f",
                 fg: str = "#ececec",
                 fg_dim: str = "#8e8ea0",
                 radius: int = 14):
        outer = parent.cget("bg") if hasattr(parent, "cget") else "#212121"
        super().__init__(parent, height=self._H_MIN, bg=outer,
                         highlightthickness=0, bd=0)
        self._radius   = radius
        self._accent   = btn_color
        self._on_send  = on_send
        self._cur_h    = self._H_MIN
        self._bg_input = bg_input
        self._fg       = fg
        self._fg_dim   = fg_dim

        self.entry = tk.Text(
            self, bg=bg_input, fg=fg_dim,
            font=(FONT_KO, 9), wrap="word", relief="flat",
            insertbackground=fg, bd=0, highlightthickness=0,
            height=1, pady=2,
        )
        self.entry.insert("1.0", self._PH)
        self.entry.bind("<FocusIn>",      self._focus_in)
        self.entry.bind("<FocusOut>",     self._focus_out)
        self.entry.bind("<Return>",       self._on_return)
        self.entry.bind("<Shift-Return>", self._on_shift_return)
        self.entry.bind("<KeyRelease>",   self._on_text_change)
        self._ew = self.create_window(self._PAD, 9, anchor="nw",
                                      window=self.entry,
                                      width=100, height=self._H_MIN - 16)

        self._btn = tk.Canvas(self, bg=bg_input, highlightthickness=0, cursor="hand2")
        self._bw = self.create_window(0, 0, anchor="center", window=self._btn,
                                      width=self._BTNW - 4, height=self._BTNW - 4)
        self._btn.bind("<Configure>", lambda _: self._draw_btn())
        self._btn.bind("<Enter>",     lambda _: self._draw_btn(True))
        self._btn.bind("<Leave>",     lambda _: self._draw_btn(False))
        self._btn.bind("<Button-1>",  lambda _: on_send())
        self.bind("<Configure>", self._redraw)

    def get_text(self) -> str:
        text = self.entry.get("1.0", "end-1c")
        return "" if text == self._PH else text

    def clear_text(self) -> None:
        self.entry.delete("1.0", "end")

    def set_sending(self, sending: bool) -> None:
        self._accent_bak = getattr(self, "_accent_bak", self._accent)
        self._accent = "#555555" if sending else self._accent_bak
        self._draw_btn()

    def retheme(self, bg_input: str, fg: str, fg_dim: str) -> None:
        self._bg_input = bg_input
        self._fg = fg
        self._fg_dim = fg_dim
        outer = self.master.cget("bg") if hasattr(self.master, "cget") else "#212121"
        self.config(bg=outer)
        is_ph = self.entry.get("1.0", "end-1c") == self._PH
        self.entry.config(bg=bg_input, fg=fg_dim if is_ph else fg,
                          insertbackground=fg)
        self._btn.config(bg=bg_input)
        self._redraw()
        self._draw_btn()

    def _on_return(self, _) -> str:
        self._on_send()
        return "break"

    def _on_shift_return(self, _) -> str:
        self.entry.insert("insert", "\n")
        self.entry.see("insert")
        self._on_text_change()
        return "break"

    def _on_text_change(self, _=None) -> None:
        lines = int(self.entry.index("end-1c").split(".")[0])
        new_h = max(self._H_MIN,
                    min(self._H_MAX, self._H_MIN + (lines - 1) * self._LINE_H))
        if new_h != self._cur_h:
            self._cur_h = new_h
            self.config(height=new_h)
            self._redraw()

    def _focus_in(self, _) -> None:
        if self.entry.get("1.0", "end-1c") == self._PH:
            self.entry.delete("1.0", "end")
            self.entry.config(fg=self._fg)

    def _focus_out(self, _) -> None:
        if not self.entry.get("1.0", "end-1c"):
            self.entry.insert("1.0", self._PH)
            self.entry.config(fg=self._fg_dim)
            self._cur_h = self._H_MIN
            self.config(height=self._H_MIN)
            self._redraw()

    def _draw_btn(self, hover: bool = False) -> None:
        c = self._btn
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 4 or h < 4:
            return
        _round_rect(c, 0, 0, w, h, 8, _darken(self._accent) if hover else self._accent)
        c.create_text(w // 2, h // 2, text="↑", fill="white", font=(FONT_KO, 10))

    def _redraw(self, event=None) -> None:
        self.delete("bg")
        w = self.winfo_width()
        h = self._cur_h
        if w < 8 or h < 8:
            return
        _round_rect(self, 0, 0, w, h, self._radius, self._bg_input, tag="bg")
        self.tag_lower("bg")
        btn_size = self._BTNW - 4
        entry_w  = w - self._BTNW - self._PAD * 2 - 10
        lines    = max(1, round((h - self._H_MIN) / self._LINE_H) + 1)
        entry_h  = lines * self._LINE_H + 2
        entry_y  = max(2, (h - entry_h) // 2)
        self.coords(self._ew, self._PAD, entry_y)
        self.itemconfig(self._ew, width=max(10, entry_w), height=entry_h)
        self.coords(self._bw,
                    w - self._PAD - btn_size // 2,
                    h - btn_size // 2 - 4)

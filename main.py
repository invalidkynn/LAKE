import asyncio
import random
import string
import aiohttp
import requests
import os
import math
import threading
import tkinter as tk
from tkinter import font as tkfont
from typing import List
from collections import deque
from datetime import datetime

# --- CONFIG ---
WEBHOOK_URL = "WEBHOOK_URL_HERE"

# ── State ────────────────────────────────────────────────
_log_lines: deque = deque(maxlen=500)
_hits: List[str] = []
_stats = {"checked": 0, "available": 0, "taken": 0, "errors": 0}
_status = "Idle"
_lock = threading.Lock()
_running = False
_stop_event = threading.Event()
_total_usernames = 0

# ── Helpers ──────────────────────────────────────────────
def _now():
    return datetime.now().strftime("%H:%M:%S")

def _log(msg, kind="info"):
    with _lock:
        _log_lines.append((f"[{_now()}]  {msg}", kind))

def write_file(user):
    with open("hits.txt", "a", encoding="utf-8") as f:
        f.write(user + "\n")

def send_webhook(url, user):
    if "WEBHOOK_URL_HERE" in url:
        return
    try:
        requests.post(url, json={"content": f"Available: @{user}"}, timeout=5)
    except:
        pass

def generate_usernames(amount, length):
    chars = string.ascii_lowercase + string.digits
    return ["".join(random.choice(chars) for _ in range(length)) for _ in range(amount)]

def load_from_txt():
    if not os.path.exists("usernames.txt"):
        return []
    return [x.strip() for x in open("usernames.txt") if x.strip()]

# ── Checker ──────────────────────────────────────────────
class Checker:
    def __init__(self, webhook_url, usernames):
        self.webhook_url = webhook_url
        self.usernames = usernames
        self.semaphore = asyncio.Semaphore(4)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)"
        ]

    async def _check(self, session: aiohttp.ClientSession, username: str) -> None:
        global _status
        if _stop_event.is_set():
            return
        async with self.semaphore:
            if _stop_event.is_set():
                return
            await asyncio.sleep(random.uniform(1.5, 3))
            _status = f"Checking @{username}"
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
            }
            url = f'https://www.tiktok.com/@{username}'
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    with _lock:
                        _stats["checked"] += 1
                    if response.status == 404:
                        with _lock:
                            _stats["available"] += 1
                            _hits.append(username)
                        write_file(username)
                        send_webhook(self.webhook_url, username)
                        _log(f"[AVAILABLE]  @{username}", "hit")
                    elif response.status == 200:
                        content = await response.text()
                        if 'webapp-user-title' not in content and '"userInfo":' not in content:
                            with _lock:
                                _stats["available"] += 1
                                _hits.append(username)
                            write_file(username)
                            send_webhook(self.webhook_url, username)
                            _log(f"[AVAILABLE]  @{username}", "hit")
                        else:
                            with _lock:
                                _stats["taken"] += 1
                            _log(f"[TAKEN]      @{username}", "taken")
                    elif response.status == 429:
                        with _lock:
                            _status = "Rate limited — cooling down"
                        _log("[RATE LIMIT]  Cooling 60s", "warn")
                        await asyncio.sleep(60)
                    else:
                        with _lock:
                            _stats["errors"] += 1
                        _log(f"[HTTP {response.status}]   @{username}", "warn")
            except Exception as e:
                with _lock:
                    _stats["errors"] += 1
                _log(f"[ERROR]      @{username}: {e}", "err")

    async def start(self):
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(*[self._check(session, u) for u in self.usernames])

# ── Palette ──────────────────────────────────────────────
BG       = "#07070F"
GLASS    = "#0E0E1A"       # panel fill (semi-opaque look via stipple)
GLASS2   = "#13131F"
BORDER   = "#1F1F35"
GLOW_B   = "#1A2A4A"       # subtle border glow base
ACCENT   = "#00E5FF"
ACCENT2  = "#7B5EA7"
GREEN    = "#00FFB3"
GREEN2   = "#00CC8E"
RED      = "#FF4060"
YELLOW   = "#FFD166"
GREY     = "#252535"
TEXT     = "#D8D8F0"
SUBTEXT  = "#55556F"
DIM      = "#2A2A40"

# ── Font resolution ──────────────────────────────────────
_FONT_MONO_NORM  = None
_FONT_MONO_BOLD  = None
_FONT_UI_BOLD_SM = None
_FONT_UI_NORM    = None
_FONT_UI_TITLE   = None
_FONT_STAT_NUM   = None
_FONT_BTN        = None
_FONT_PILL       = None

def _resolve_fonts():
    global _FONT_MONO_NORM, _FONT_MONO_BOLD, _FONT_UI_BOLD_SM
    global _FONT_UI_NORM, _FONT_UI_TITLE, _FONT_STAT_NUM, _FONT_BTN, _FONT_PILL
    try:
        import tkinter as _tk
        root_tmp = _tk.Tk(); root_tmp.withdraw()
        avail = set(tkfont.families(root_tmp)); root_tmp.destroy()
    except:
        avail = set()

    def pick(candidates, size, *style):
        for c in candidates:
            if c in avail:
                return (c, size, *style) if style else (c, size)
        return (candidates[-1], size, *style) if style else (candidates[-1], size)

    mono = ["JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", "Courier New"]
    ui   = ["Segoe UI", "SF Pro Display", "Helvetica Neue", "Arial"]
    num  = ["Segoe UI Black", "SF Pro Display", "Helvetica Neue", "Arial Black", "Arial"]

    _FONT_MONO_NORM  = pick(mono,  9)
    _FONT_MONO_BOLD  = pick(mono,  9, "bold")
    _FONT_UI_BOLD_SM = pick(ui,    8, "bold")
    _FONT_UI_NORM    = pick(ui,   10)
    _FONT_UI_TITLE   = pick(ui,   17, "bold")
    _FONT_STAT_NUM   = pick(num,  22, "bold")
    _FONT_BTN        = pick(ui,    9, "bold")
    _FONT_PILL       = pick(ui,    8, "bold")

# ── Helpers ──────────────────────────────────────────────
def _lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

def _hex_alpha(color, alpha):
    """Blend color toward BG to simulate transparency."""
    return _lerp_color(BG, color, alpha)

def _rounded_rect(canvas, x1, y1, x2, y2, r=10, **kw):
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return canvas.create_polygon(pts, smooth=True, **kw)

def _glow_rect(canvas, x1, y1, x2, y2, r, color, layers=4):
    """Draw concentric rounded rects to fake a glow."""
    for i in range(layers, 0, -1):
        t   = i / layers
        pad = i * 2
        col = _lerp_color(BG, color, t * 0.35)
        _rounded_rect(canvas, x1-pad, y1-pad, x2+pad, y2+pad, r+pad,
                      fill=col, outline="")
    _rounded_rect(canvas, x1, y1, x2, y2, r, fill=_hex_alpha(color, 0.08),
                  outline=_hex_alpha(color, 0.6), width=1)

# ── Particle system ──────────────────────────────────────
class Particle:
    def __init__(self, W, H):
        self.reset(W, H, born=False)

    def reset(self, W, H, born=True):
        self.x  = random.uniform(0, W)
        self.y  = H + 5 if born else random.uniform(0, H)
        self.vy = random.uniform(-0.4, -1.2)
        self.vx = random.uniform(-0.3, 0.3)
        self.r  = random.uniform(1, 2.5)
        self.life   = 1.0
        self.decay  = random.uniform(0.003, 0.008)
        self.color_t = random.random()  # 0=accent, 1=green

    def step(self):
        self.x   += self.vx
        self.y   += self.vy
        self.life -= self.decay

    @property
    def color(self):
        base = _lerp_color(ACCENT, GREEN, self.color_t)
        return _lerp_color(BG, base, self.life * 0.9)

# ── GUI ──────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("LAKE  •  Username Tool")
        self.root.geometry("1300x800")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # Animation state
        self._tick         = 0
        self._pulse        = 0.0
        self._running_anim = False
        self._usernames    = []

        # Ripple effects [{x,y,r,max_r,alpha,color}]
        self._ripples: list = []

        # Scan line
        self._scan_y = 0

        # Particles
        self._particles: list = []

        # Glowing border phase per panel
        self._border_phase = 0.0

        self._build_ui()
        self._init_particles()
        self._animate()
        self.update_ui()

    # ── Particles ───────────────────────────────────────
    def _init_particles(self):
        W = 1300
        self._bg_canvas.update_idletasks()
        W = self._bg_canvas.winfo_width() or 1300
        H = self._bg_canvas.winfo_height() or 800
        self._particles = [Particle(W, H) for _ in range(55)]

    # ── Layout ──────────────────────────────────────────
    def _build_ui(self):
        # Background canvas (particle layer)
        self._bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self._bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # ── Top bar ──
        topbar = tk.Frame(self.root, bg=BG, height=68)
        topbar.place(x=0, y=0, relwidth=1)
        topbar.pack_propagate(False)

        logo_f = tk.Frame(topbar, bg=BG)
        logo_f.pack(side="left", padx=24, pady=14)
        tk.Label(logo_f, text="◈", fg=ACCENT, bg=BG,
                 font=(_FONT_UI_TITLE[0], 20, "bold")).pack(side="left")
        tk.Label(logo_f, text=" LAKE", fg=TEXT, bg=BG,
                 font=_FONT_UI_TITLE).pack(side="left")
        tk.Label(logo_f, text="  ·  USERNAME TOOL", fg=SUBTEXT, bg=BG,
                 font=(_FONT_UI_NORM[0], 9)).pack(side="left", pady=4)

        # Status pill canvas
        self.pill_canvas = tk.Canvas(topbar, width=150, height=30,
                                     bg=BG, highlightthickness=0)
        self.pill_canvas.pack(side="left", padx=16, pady=18)

        # Clock
        self.clock_label = tk.Label(topbar, text="", fg=SUBTEXT, bg=BG,
                                    font=_FONT_MONO_NORM)
        self.clock_label.pack(side="left", padx=10)

        # Buttons (right side)
        ctrl = tk.Frame(topbar, bg=BG)
        ctrl.pack(side="right", padx=24, pady=14)

        self._stop_canvas  = self._make_btn(ctrl, "■  STOP",  self._stop,
                                            RED,   w=118, h=36)
        self._stop_canvas.pack(side="right", padx=(8,0))

        self._start_canvas = self._make_btn(ctrl, "▶  START", self._start,
                                            GREEN, w=128, h=36)
        self._start_canvas.pack(side="right")

        # Thin glowing top border line
        self._topline = tk.Canvas(self.root, height=2, bg=BG,
                                  highlightthickness=0)
        self._topline.place(x=0, y=68, relwidth=1)

        # ── Config strip ──
        cfg_outer = tk.Canvas(self.root, height=60, bg=BG,
                              highlightthickness=0)
        cfg_outer.place(x=0, y=70, relwidth=1)
        self._cfg_canvas = cfg_outer

        cfg = tk.Frame(self.root, bg=BG, height=60)
        cfg.place(x=0, y=70, relwidth=1)
        cfg.pack_propagate(False)

        self._make_cfg_block(cfg, "MODE",    self._make_mode_selector)
        self._vsep(cfg)
        self._make_cfg_block(cfg, "AMOUNT",  self._make_amount_entry)
        self._vsep(cfg)
        self._make_cfg_block(cfg, "LENGTH",  self._make_length_entry)
        self._vsep(cfg)
        self._make_cfg_block(cfg, "WEBHOOK", self._make_webhook_entry)

        # Progress bar canvas
        self.pb_canvas = tk.Canvas(self.root, height=4, bg=GREY,
                                   highlightthickness=0)
        self.pb_canvas.place(x=0, y=130, relwidth=1)

        # ── Body ──
        body = tk.Frame(self.root, bg=BG)
        body.place(x=14, y=142, relwidth=1, relheight=1,
                   width=-28, height=-156)

        # Left — log panel
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        self._panel_header(left, "ACTIVITY LOG", ACCENT)
        self._log_frame_canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
        self._log_frame_canvas.pack(fill="both", expand=True, pady=(4, 0))

        log_inner = tk.Frame(left, bg=GLASS2)
        log_inner.place(in_=self._log_frame_canvas, relx=0, rely=0,
                        relwidth=1, relheight=1)

        self.logs = tk.Text(log_inner, bg=GLASS2, fg=TEXT,
                            insertbackground=ACCENT,
                            font=_FONT_MONO_NORM, relief="flat", bd=0,
                            selectbackground=ACCENT2, wrap="none",
                            padx=10, pady=6)
        log_sb = tk.Scrollbar(log_inner, command=self.logs.yview,
                              bg=GLASS2, troughcolor=GLASS2, bd=0,
                              width=5, relief="flat")
        self.logs.configure(yscrollcommand=log_sb.set)
        self.logs.pack(side="left", fill="both", expand=True)
        log_sb.pack(side="right", fill="y")

        self.logs.tag_config("hit",   foreground=GREEN)
        self.logs.tag_config("taken", foreground=SUBTEXT)
        self.logs.tag_config("warn",  foreground=YELLOW)
        self.logs.tag_config("err",   foreground=RED)
        self.logs.tag_config("ts",    foreground=DIM)

        # Divider
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y", padx=12)

        # Right column
        right = tk.Frame(body, bg=BG, width=350)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Stat cards
        self._panel_header(right, "STATISTICS", ACCENT2)
        cards = tk.Frame(right, bg=BG)
        cards.pack(fill="x", pady=(4, 10))

        self.card_checked   = self._stat_card(cards, "CHECKED",   "0", ACCENT)
        self.card_available = self._stat_card(cards, "AVAILABLE", "0", GREEN)
        self.card_taken     = self._stat_card(cards, "TAKEN",     "0", SUBTEXT)
        self.card_errors    = self._stat_card(cards, "ERRORS",    "0", RED)

        # Hits panel
        self._panel_header(right, "HITS", GREEN)
        hit_inner = tk.Frame(right, bg=GLASS2)
        hit_inner.pack(fill="both", expand=True, pady=(4, 0))

        self.hits = tk.Text(hit_inner, bg=GLASS2, fg=GREEN,
                            insertbackground=GREEN,
                            font=_FONT_MONO_BOLD, relief="flat", bd=0,
                            selectbackground=ACCENT2, wrap="none",
                            padx=10, pady=6)
        hit_sb = tk.Scrollbar(hit_inner, command=self.hits.yview,
                              bg=GLASS2, troughcolor=GLASS2, bd=0,
                              width=5, relief="flat")
        self.hits.configure(yscrollcommand=hit_sb.set)
        self.hits.pack(side="left", fill="both", expand=True)
        hit_sb.pack(side="right", fill="y")

        # ── Bottom status bar ──
        self._statusbar = tk.Frame(self.root, bg=BG, height=26)
        self._statusbar.place(x=0, rely=1.0, y=-26, relwidth=1)

        tk.Frame(self._statusbar, bg=BORDER, height=1).pack(fill="x")
        bar_inner = tk.Frame(self._statusbar, bg=BG)
        bar_inner.pack(fill="x", expand=True)

        self.status_label = tk.Label(bar_inner, text="⚡  Idle",
                                     fg=SUBTEXT, bg=BG, font=_FONT_MONO_NORM)
        self.status_label.pack(side="left", padx=14)

    # ── Reusable UI widgets ──────────────────────────────
    def _make_btn(self, parent, label, cmd, color, w=120, h=34):
        c = tk.Canvas(parent, width=w, height=h, bg=BG,
                      highlightthickness=0, cursor="hand2")
        c._label = label
        c._color = color
        c.btn_w     = w
        c.btn_h     = h
        c._glow  = 0.0        # hover glow level 0→1
        c._ripples = []

        def redraw():
            c.delete("all")
            g = c._glow
            # Outer glow
            if g > 0:
                for layer in range(3, 0, -1):
                    pad = layer * 3
                    gc = _lerp_color(BG, color, g * 0.2 * layer)
                    _rounded_rect(c, -pad, -pad, w+pad, h+pad, 8+pad,
                                  fill=gc, outline="")
            # Main fill
            fill_c = _lerp_color(_hex_alpha(color, 0.07),
                                  _hex_alpha(color, 0.18), g)
            border_c = _lerp_color(_hex_alpha(color, 0.5), color, g)
            _rounded_rect(c, 1, 1, w-1, h-1, 7,
                          fill=fill_c, outline=border_c, width=1)
            # Subtle top highlight
            c.create_line(8, 2, w-8, 2, fill=_hex_alpha(color, 0.25 + g*0.25))
            # Text
            c.create_text(w//2, h//2, text=label, fill=color,
                          font=_FONT_BTN)
            # Ripples
            for rp in list(c._ripples):
                rp["r"]    += 4
                rp["alpha"] = max(0, rp["alpha"] - 0.06)
                if rp["alpha"] <= 0:
                    c._ripples.remove(rp)
                    continue
                rc = _lerp_color(BG, color, rp["alpha"] * 0.5)
                x, y, r = rp["x"], rp["y"], rp["r"]
                c.create_oval(x-r, y-r, x+r, y+r,
                              outline=rc, fill="", width=1)

        def on_enter(e):
            c._glow = 0.0
            _animate_hover(c, redraw, target=1.0)

        def on_leave(e):
            _animate_hover(c, redraw, target=0.0)

        def on_click(e):
            c._ripples.append({"x": e.x, "y": e.y, "r": 4, "alpha": 1.0})
            redraw()
            cmd()

        redraw()
        c.bind("<Enter>",    on_enter)
        c.bind("<Leave>",    on_leave)
        c.bind("<Button-1>", on_click)
        c._redraw = redraw
        return c

    def _vsep(self, parent):
        tk.Frame(parent, bg=BORDER, width=1).pack(side="left", fill="y", pady=10)

    def _make_cfg_block(self, parent, label, widget_fn):
        f = tk.Frame(parent, bg=BG, padx=18, pady=8)
        f.pack(side="left", fill="y")
        tk.Label(f, text=label, fg=SUBTEXT, bg=BG,
                 font=_FONT_UI_BOLD_SM).pack(anchor="w")
        widget_fn(f)

    def _make_mode_selector(self, parent):
        self.mode_var = tk.StringVar(value="generate")
        row = tk.Frame(parent, bg=BG)
        row.pack(anchor="w", pady=(3, 0))
        for val, lbl in [("generate", "Generate"), ("file", "Load File")]:
            tk.Radiobutton(row, text=lbl, variable=self.mode_var, value=val,
                           fg=TEXT, bg=BG, selectcolor=GLASS2,
                           activebackground=BG, activeforeground=ACCENT,
                           font=_FONT_UI_NORM, bd=0).pack(side="left", padx=(0,10))

    def _make_amount_entry(self, parent):
        self.amount_var = tk.StringVar(value="20")
        self._styled_entry(parent, self.amount_var, width=6)

    def _make_length_entry(self, parent):
        self.length_var = tk.StringVar(value="5")
        self._styled_entry(parent, self.length_var, width=6)

    def _make_webhook_entry(self, parent):
        self.webhook_var = tk.StringVar(value=WEBHOOK_URL)
        self._styled_entry(parent, self.webhook_var, width=28)

    def _styled_entry(self, parent, var, width):
        f = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
        f.pack(anchor="w", pady=(3, 0))
        e = tk.Entry(f, textvariable=var, width=width,
                     bg=GLASS2, fg=TEXT, insertbackground=ACCENT,
                     font=_FONT_UI_NORM, relief="flat", bd=4,
                     highlightthickness=0)
        e.pack()
        # Focus glow
        def on_focus_in(ev):
            f.config(bg=_hex_alpha(ACCENT, 0.6))
        def on_focus_out(ev):
            f.config(bg=BORDER)
        e.bind("<FocusIn>",  on_focus_in)
        e.bind("<FocusOut>", on_focus_out)
        return e

    def _panel_header(self, parent, text, color):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 2))
        dot = tk.Label(row, text="▸", fg=color, bg=BG,
                       font=(_FONT_UI_BOLD_SM[0], 9))
        dot.pack(side="left")
        tk.Label(row, text=f"  {text}", fg=_hex_alpha(color, 0.85), bg=BG,
                 font=_FONT_UI_BOLD_SM).pack(side="left")
        tk.Frame(row, bg=_hex_alpha(color, 0.2), height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6)

    def _stat_card(self, parent, label, value, color):
        # Outer glow wrapper
        outer = tk.Frame(parent, bg=_hex_alpha(color, 0.12), padx=1, pady=1)
        outer.pack(side="left", expand=True, fill="both", padx=3, pady=2)
        inner = tk.Frame(outer, bg=GLASS, padx=6)
        inner.pack(fill="both", expand=True, ipady=6)
        tk.Label(inner, text=label, fg=_hex_alpha(color, 0.6), bg=GLASS,
                 font=_FONT_UI_BOLD_SM).pack(pady=(4, 0))
        val = tk.Label(inner, text=value, fg=color, bg=GLASS,
                       font=_FONT_STAT_NUM)
        val.pack(pady=(0, 4))
        return val

    # ── Controls ────────────────────────────────────────
    def _start(self):
        global _running, _stop_event, _total_usernames
        if _running:
            return
        with _lock:
            _stats.update({"checked": 0, "available": 0, "taken": 0, "errors": 0})
            _log_lines.clear()
            _hits.clear()

        mode = self.mode_var.get()
        if mode == "generate":
            try:
                amt = int(self.amount_var.get())
                ln  = int(self.length_var.get())
            except ValueError:
                _log("[CONFIG ERROR] Invalid amount or length", "err")
                return
            self._usernames = generate_usernames(amt, ln)
        else:
            self._usernames = load_from_txt()
            if not self._usernames:
                _log("[CONFIG ERROR] usernames.txt not found or empty", "err")
                return

        _total_usernames = len(self._usernames)
        _stop_event.clear()
        _running = True
        self._running_anim = True
        _log(f"[START]  Loaded {_total_usernames} usernames", "hit")
        webhook = self.webhook_var.get()

        def run():
            global _running, _status
            _status = "Running"
            checker = Checker(webhook, self._usernames)
            asyncio.run(checker.start())
            if not _stop_event.is_set():
                _status = "Done"
                _log("[DONE]  All usernames processed", "hit")
            _running = False
            self._running_anim = False

        threading.Thread(target=run, daemon=True).start()

    def _stop(self):
        global _running, _status
        if not _running:
            return
        _stop_event.set()
        _status = "Stopped"
        _running = False
        self._running_anim = False
        _log("[STOPPED]  User stopped the checker", "warn")

    # ── Main animation loop ──────────────────────────────
    def _animate(self):
        self._tick  += 1
        self._pulse  = (self._pulse + 3) % 360
        self._border_phase = (self._border_phase + 1.5) % 360
        self._scan_y = (self._scan_y + 1) % (self.root.winfo_height() or 800)

        self._draw_bg()
        self._draw_topline()
        self._draw_pill()
        self._draw_progress()
        self._redraw_btn_ripples()

        self.root.after(30, self._animate)  # ~33fps

    def _draw_bg(self):
        c = self._bg_canvas
        c.update_idletasks()
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 2 or H < 2:
            return
        c.delete("all")

        # Deep background gradient (vertical strips)
        strips = 6
        for i in range(strips):
            x1 = int(W * i / strips)
            x2 = int(W * (i+1) / strips)
            t  = i / (strips - 1)
            col = _lerp_color("#07070F", "#0A0A18", t)
            c.create_rectangle(x1, 0, x2, H, fill=col, outline="")

        # Subtle grid lines
        grid_col = _hex_alpha(ACCENT2, 0.06)
        for x in range(0, W, 60):
            c.create_line(x, 0, x, H, fill=grid_col)
        for y in range(0, H, 60):
            c.create_line(0, y, W, y, fill=grid_col)

        # Ambient glow orb (bottom left)
        glow_x = int(W * 0.12 + 30 * math.sin(math.radians(self._pulse * 0.4)))
        glow_y = int(H * 0.75 + 20 * math.cos(math.radians(self._pulse * 0.3)))
        for layer in range(8, 0, -1):
            r   = layer * 28
            t   = layer / 8
            col = _lerp_color(BG, ACCENT2, t * 0.18)
            c.create_oval(glow_x-r, glow_y-r, glow_x+r, glow_y+r,
                          fill=col, outline="")

        # Ambient glow orb (top right, accent colored)
        glow_x2 = int(W * 0.88 + 25 * math.cos(math.radians(self._pulse * 0.5)))
        glow_y2 = int(H * 0.2  + 18 * math.sin(math.radians(self._pulse * 0.4)))
        for layer in range(7, 0, -1):
            r   = layer * 22
            t   = layer / 7
            col = _lerp_color(BG, ACCENT, t * 0.14)
            c.create_oval(glow_x2-r, glow_y2-r, glow_x2+r, glow_y2+r,
                          fill=col, outline="")

        # Particles
        if len(self._particles) < 55:
            self._particles += [Particle(W, H) for _ in range(55 - len(self._particles))]
        for p in self._particles:
            p.step()
            if p.life <= 0 or p.y < -10:
                p.reset(W, H)
            r = p.r * p.life
            c.create_oval(p.x-r, p.y-r, p.x+r, p.y+r,
                          fill=p.color, outline="")

        # Scan line (subtle horizontal sweep)
        sy = self._scan_y
        scan_col = _hex_alpha(ACCENT, 0.04)
        c.create_rectangle(0, sy, W, sy+2, fill=scan_col, outline="")

    def _draw_topline(self):
        c = self._topline
        c.update_idletasks()
        W = c.winfo_width()
        c.delete("all")
        if W < 2:
            return
        # Animated gradient line
        for x in range(W):
            t = (x / W + self._pulse / 360) % 1.0
            col = _lerp_color(ACCENT2, ACCENT,
                              0.5 + 0.5 * math.sin(t * math.pi * 2))
            c.create_line(x, 0, x, 2, fill=col)

    def _draw_pill(self):
        c = self.pill_canvas
        c.delete("all")
        w, h = 150, 30

        if self._running_anim:
            t   = 0.5 + 0.5 * math.sin(math.radians(self._pulse))
            col = _lerp_color(GREEN2, GREEN, t)
            # Glow layers
            for layer in range(3, 0, -1):
                pad = layer * 2
                gc  = _lerp_color(BG, GREEN, t * 0.15 * layer)
                _rounded_rect(c, -pad, -pad, w+pad, h+pad, 15+pad,
                              fill=gc, outline="")
            _rounded_rect(c, 0, 0, w, h, 15,
                          fill=_hex_alpha(GREEN, 0.12 + t * 0.08),
                          outline=col, width=1)
            dots = ["◐", "◓", "◑", "◒"]
            dot  = dots[(self._tick // 8) % 4]
            c.create_text(w//2, h//2, text=f"{dot}  RUNNING",
                          fill=col, font=_FONT_PILL)
        else:
            _rounded_rect(c, 0, 0, w, h, 15,
                          fill=_hex_alpha(SUBTEXT, 0.06),
                          outline=_hex_alpha(SUBTEXT, 0.3), width=1)
            c.create_text(w//2, h//2, text="◉  IDLE",
                          fill=SUBTEXT, font=_FONT_PILL)

    def _draw_progress(self):
        c = self.pb_canvas
        c.update_idletasks()
        W = c.winfo_width()
        if W < 2:
            return
        c.delete("all")

        total   = _total_usernames
        checked = _stats["checked"]
        ratio   = (checked / total) if total > 0 else 0

        # Track
        c.create_rectangle(0, 0, W, 4, fill=_hex_alpha(ACCENT2, 0.15), outline="")

        if ratio > 0:
            bar_w = max(4, int(W * ratio))
            # Gradient fill
            for i in range(bar_w):
                t   = i / max(bar_w, 1)
                col = _lerp_color(ACCENT2, ACCENT, t)
                c.create_line(i, 0, i, 4, fill=col)
            # Shimmer pass
            sx = int(W * ((self._pulse / 360))) % (bar_w + 40) - 20
            for dx in range(-8, 8):
                ix = sx + dx
                if 0 <= ix < bar_w:
                    alpha = 1.0 - abs(dx) / 8
                    shine = _lerp_color(ACCENT, "#FFFFFF", alpha * 0.6)
                    c.create_line(ix, 0, ix, 4, fill=shine)

    def _redraw_btn_ripples(self):
        for btn in (self._start_canvas, self._stop_canvas):
            if btn._ripples:
                btn._redraw()

    # ── UI refresh ──────────────────────────────────────
    def update_ui(self):
        with _lock:
            stats  = dict(_stats)
            status = _status
            logs   = list(_log_lines)
            hits   = list(_hits)

        # Cards
        self.card_checked.config(text=str(stats["checked"]))
        self.card_available.config(text=str(stats["available"]))
        self.card_taken.config(text=str(stats["taken"]))
        self.card_errors.config(text=str(stats["errors"]))

        # Status bar + clock
        icon = "◈" if _running else "⚡"
        fg   = GREEN if _running else SUBTEXT
        self.status_label.config(text=f"{icon}  {status}", fg=fg)
        self.clock_label.config(text=_now())

        # Logs
        self.logs.config(state="normal")
        self.logs.delete(1.0, tk.END)
        for msg, kind in logs[-60:]:
            ts, rest = msg[:11], msg[11:]
            s = self.logs.index(tk.END)
            self.logs.insert(tk.END, ts)
            self.logs.tag_add("ts", s, tk.END)
            self.logs.insert(tk.END, rest + "\n")
            e = self.logs.index(tk.END)
            ls = self.logs.search(rest[:6], s, stopindex=tk.END)
            if ls:
                self.logs.tag_add(kind, ls, e)
        self.logs.see(tk.END)
        self.logs.config(state="disabled")

        # Hits
        self.hits.config(state="normal")
        self.hits.delete(1.0, tk.END)
        for i, user in enumerate(hits[-60:], 1):
            self.hits.insert(tk.END, f"{i:>3}.  @{user}\n      tiktok.com/@{user}\n\n")
        self.hits.see(tk.END)
        self.hits.config(state="disabled")

        self.root.after(160, self.update_ui)


# ── Button hover animator (smooth lerp) ─────────────────
def _animate_hover(canvas, redraw_fn, target, steps=8):
    def step(remaining):
        if remaining <= 0:
            canvas._glow = target
            redraw_fn()
            return
        canvas._glow += (target - canvas._glow) * 0.35
        redraw_fn()
        canvas.after(16, lambda: step(remaining - 1))
    step(steps)


# ── Entry ────────────────────────────────────────────────
def run_gui():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except:
        pass
    _resolve_fonts()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()

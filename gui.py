"""
Tkinter GUI for the GSC + GA4 export tool.

Imported only by main.py on the interactive path, so headless runs never load
tkinter — see the module docstring in main.py.
© Litzki Systems LLC
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, timedelta

from config import (
    ALL_REPORTS, DATE_RANGES, GA4_MAP, weekly_properties,
    PSI_TOP_N_MANUAL, OUTPUT_DIR, REPORT_BRAND,
)
from auth import get_services, fetch_all_gsc_properties
from runner import run_export

BLUE    = "#1e3a5f"
LBLUE   = "#3b82f6"
WHITE   = "#ffffff"
BG      = "#f5f7fa"
CARD    = "#ffffff"
BORDER  = "#dde3ed"
TEXT    = "#1a1a2e"
SUBTEXT = "#6b7280"
GREEN   = "#1a7a1a"
RED     = "#cc0000"
FONT    = "Helvetica"


def card(parent, **kw):
    f = tk.Frame(parent, bg=CARD, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1, **kw)
    return f


def label(parent, text, size=11, bold=False, color=TEXT, **kw):
    return tk.Label(parent, text=text, bg=parent.cget("bg"),
                    fg=color, font=(FONT, size, "bold" if bold else "normal"), **kw)


def sep(parent):
    ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=0, pady=8)


class LoadingScreen(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Connecting…")
        self.resizable(False, False)
        self.configure(bg=CARD)
        self.grab_set()
        tk.Label(self, text="Authenticating & loading properties…",
                 font=(FONT, 12), bg=CARD, fg=TEXT,
                 padx=30, pady=20).pack()
        pb = ttk.Progressbar(self, mode="indeterminate", length=280)
        pb.pack(padx=30, pady=(0, 20))
        pb.start(12)


class App(tk.Tk):
    def __init__(self, env):
        super().__init__()
        self.title("GSC + GA4 Export")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.gsc         = None
        self.ga4         = None
        self.properties  = []
        self.prop_vars   = {}
        self.report_vars = {}
        self.env         = env
        self.psi_key     = env.get("PSI_API_KEY", "")
        self._build_ui()
        self.after(100, self._load_services)

    def _build_ui(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Header ────────────────────────────────────────────────────────────
        hc = card(wrap)
        hc.pack(fill="x", pady=(0, 10))
        hf = tk.Frame(hc, bg=CARD)
        hf.pack(fill="x", padx=16, pady=12)

        label(hf, "GSC + GA4 Export", size=15, bold=True, color=BLUE).pack(anchor="w")

        psi_ok    = bool(self.psi_key)
        resend_ok = all(self.env.get(k) for k in ["RESEND_API_KEY", "RESEND_TO"])
        for text, ok in [
            (f"PSI Key: {'✓' if psi_ok else '✗ missing (.env)'}", psi_ok),
            (f"Resend: {'✓ configured' if resend_ok else '✗ missing (.env)'}", resend_ok),
        ]:
            tk.Label(hf, text=text, font=(FONT, 10), bg=CARD,
                     fg=GREEN if ok else RED).pack(anchor="w")

        # ── Settings row ──────────────────────────────────────────────────────
        sc = card(wrap)
        sc.pack(fill="x", pady=(0, 10))
        sf = tk.Frame(sc, bg=CARD)
        sf.pack(fill="x", padx=16, pady=12)

        label(sf, "Time Range", bold=True, color=BLUE).pack(side="left")
        self.date_var = tk.StringVar(value="28 Days")
        date_values = list(DATE_RANGES.keys())
        ttk.Combobox(sf, textvariable=self.date_var,
                     values=date_values, state="readonly",
                     width=14, font=(FONT, 11)).pack(side="left", padx=10)

        tk.Frame(sf, bg=BORDER, width=1, height=24).pack(side="left", padx=12)

        label(sf, "Format", bold=True, color=BLUE).pack(side="left")
        self.fmt_var = tk.StringVar(value="xlsx")
        for val, lbl in [("xlsx", "XLSX"), ("csv", "CSV")]:
            tk.Radiobutton(sf, text=lbl, variable=self.fmt_var, value=val,
                           font=(FONT, 11), bg=CARD, fg=TEXT,
                           selectcolor=CARD, activebackground=CARD).pack(side="left", padx=6)

        tk.Frame(sf, bg=BORDER, width=1, height=24).pack(side="left", padx=12)

        self.mail_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sf, text="Send report by email (Resend)",
                       variable=self.mail_var, font=(FONT, 11),
                       bg=CARD, fg=TEXT, selectcolor=CARD,
                       activebackground=CARD).pack(side="left", padx=4)

        # ── Properties ────────────────────────────────────────────────────────
        self._prop_card = card(wrap)
        self._prop_card.pack(fill="x", pady=(0, 10))
        self._prop_frame = tk.Frame(self._prop_card, bg=CARD)
        self._prop_frame.pack(fill="x", padx=16, pady=12)
        label(self._prop_frame, "Properties", bold=True, color=BLUE).pack(anchor="w", pady=(0, 4))
        tk.Label(self._prop_frame, text="Loading…",
                 font=(FONT, 11), bg=CARD, fg=SUBTEXT).pack(anchor="w")

        # ── Reports ───────────────────────────────────────────────────────────
        rc = card(wrap)
        rc.pack(fill="x", pady=(0, 10))
        rf = tk.Frame(rc, bg=CARD)
        rf.pack(fill="x", padx=16, pady=12)

        label(rf, "Reports", bold=True, color=BLUE).pack(anchor="w", pady=(0, 8))

        cols = tk.Frame(rf, bg=CARD)
        cols.pack(fill="x")
        left  = tk.Frame(cols, bg=CARD)
        right = tk.Frame(cols, bg=CARD)
        left.pack(side="left", fill="x", expand=True)
        right.pack(side="left", fill="x", expand=True)

        for i, (lbl, key) in enumerate(ALL_REPORTS):
            var = tk.BooleanVar(value=True)
            self.report_vars[key] = var
            target = left if i < len(ALL_REPORTS) // 2 + 1 else right
            tk.Checkbutton(target, text=lbl, variable=var,
                           font=(FONT, 11), bg=CARD, fg=TEXT,
                           selectcolor=CARD, activebackground=CARD).pack(anchor="w", pady=2)

        pf = tk.Frame(rf, bg=CARD)
        pf.pack(anchor="w", pady=(8, 0))
        label(pf, "PSI: Top", size=10).pack(side="left")
        self.psi_n_var = tk.IntVar(value=PSI_TOP_N_MANUAL)
        tk.Spinbox(pf, from_=5, to=200, increment=5,
                   textvariable=self.psi_n_var, width=5,
                   font=(FONT, 10), bg=BG, relief="flat").pack(side="left", padx=6)
        label(pf, "URLs per property", size=10).pack(side="left")

        # ── Log ───────────────────────────────────────────────────────────────
        lc = card(wrap)
        lc.pack(fill="x", pady=(0, 10))
        lf = tk.Frame(lc, bg=CARD)
        lf.pack(fill="x", padx=16, pady=12)
        label(lf, "Log", bold=True, color=BLUE).pack(anchor="w", pady=(0, 6))
        self.log_box = scrolledtext.ScrolledText(
            lf, width=70, height=8, state="disabled",
            font=("Menlo", 10), bg=BG, fg=TEXT,
            relief="flat", bd=0)
        self.log_box.pack(fill="x")

        # ── Run button ────────────────────────────────────────────────────────
        self.run_btn = tk.Button(
            wrap, text="Start Export",
            font=(FONT, 12, "bold"),
            bg=BLUE, fg=WHITE,
            activebackground=LBLUE, activeforeground=WHITE,
            relief="flat", padx=20, pady=10,
            cursor="hand2",
            state="disabled", command=self._start_export)
        self.run_btn.pack(fill="x", pady=(4, 0))

        label(wrap, REPORT_BRAND, size=9, color=SUBTEXT).pack(pady=(6, 0))

    def _load_services(self):
        loading = LoadingScreen(self)

        def worker():
            try:
                gsc, ga4 = get_services()
                props    = fetch_all_gsc_properties(gsc)
                if self.winfo_exists():
                    self.after(0, lambda: self._on_loaded(gsc, ga4, props, loading))
            except Exception as e:
                err = str(e)
                if self.winfo_exists():
                    self.after(0, lambda: self._on_load_error(err, loading))

        threading.Thread(target=worker, daemon=True).start()

    def _on_loaded(self, gsc, ga4, props, loading):
        loading.destroy()
        self.gsc        = gsc
        self.ga4        = ga4
        self.properties = props

        for w in self._prop_frame.winfo_children():
            w.destroy()

        label(self._prop_frame,
              f"Properties ({len(props)})", bold=True, color=BLUE).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(self._prop_frame, bg=CARD)
        btn_row.pack(anchor="w", pady=(0, 6))
        for text, cmd in [
            ("All",      lambda: [v.set(True)  for v in self.prop_vars.values()]),
            ("None",     lambda: [v.set(False) for v in self.prop_vars.values()]),
            ("Weekly",   self._select_weekly),
        ]:
            tk.Button(btn_row, text=text, font=(FONT, 9),
                      bg=BG, fg=BLUE, relief="flat",
                      activebackground=BORDER,
                      padx=8, pady=2, cursor="hand2",
                      command=cmd).pack(side="left", padx=(0, 6))

        canvas = tk.Canvas(self._prop_frame, bg=CARD,
                           height=min(len(props) * 26 + 8, 180),
                           highlightthickness=0)
        sb     = ttk.Scrollbar(self._prop_frame, orient="vertical", command=canvas.yview)
        inner  = tk.Frame(canvas, bg=CARD)
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="x", expand=True)
        if len(props) > 6:
            sb.pack(side="right", fill="y")

        weekly = weekly_properties(self.env)

        self.prop_vars = {}
        for prop in props:
            var    = tk.BooleanVar(value=prop in weekly)
            self.prop_vars[prop] = var
            lbl    = prop.replace("sc-domain:", "").replace("https://", "").rstrip("/")
            suffix = "  [GSC+GA4]" if prop in GA4_MAP else "  [GSC only]"
            tk.Checkbutton(inner, text=lbl + suffix, variable=var,
                           font=(FONT, 11), bg=CARD, fg=TEXT,
                           selectcolor=CARD,
                           activebackground=CARD).pack(anchor="w", pady=1)

        self.run_btn.configure(state="normal")

    def _select_weekly(self):
        weekly = weekly_properties(self.env)
        if not weekly:
            messagebox.showinfo(
                "No weekly properties",
                "WEEKLY_PROPERTIES is not set in .env.\n\n"
                "Add it, for example:\n"
                "WEEKLY_PROPERTIES=sc-domain:example.com,sc-domain:example.org",
            )
            return
        for p, v in self.prop_vars.items():
            v.set(p in weekly)

    def _on_load_error(self, msg, loading):
        loading.destroy()
        messagebox.showerror("Connection Error", msg)

    def _log(self, msg):
        # Called from background thread — schedule on main thread
        if self.winfo_exists():
            self.after(0, self._log_main, msg)

    def _log_main(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _start_export(self):
        props   = [p for p, v in self.prop_vars.items()   if v.get()]
        reports = [k for k, v in self.report_vars.items() if v.get()]

        if not props:
            messagebox.showwarning("No Selection", "Please select at least one property.")
            return
        if not reports:
            messagebox.showwarning("No Selection", "Please select at least one report.")
            return

        days       = DATE_RANGES.get(self.date_var.get())
        today      = datetime.today()
        date_end   = today.strftime("%Y-%m-%d")
        date_start = "2015-01-01" if days is None else                      (today - timedelta(days=days)).strftime("%Y-%m-%d")

        self.run_btn.configure(state="disabled", text="Running…")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log(f"Start: {len(props)} properties | {len(reports)} reports | "
                  f"{self.date_var.get()} | {self.fmt_var.get().upper()}\n")

        def on_done(success):
            # Called from background thread — schedule on main thread
            def _finish():
                self.run_btn.configure(state="normal", text="Start Export")
                if success:
                    messagebox.showinfo("Done",
                        f"Export complete.\nFolder: {OUTPUT_DIR.resolve()}")
            if self.winfo_exists():
                self.after(0, _finish)

        threading.Thread(
            target=run_export,
            args=(self.gsc, self.ga4, props, reports,
                  date_start, date_end,
                  self.fmt_var.get(), self.psi_key, self.psi_n_var.get(),
                  self.mail_var.get(), self.env,
                  self._log, on_done),
            daemon=True,
        ).start()



def launch(env):
    """Open the main window and run the Tk event loop."""
    App(env).mainloop()

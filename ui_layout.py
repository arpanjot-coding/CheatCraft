"""Desktop layout and visual system; no target I/O or session mutations."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from backend import HOME
from memory import TYPES
from serialization import dumps
from version import VERSION

BG, SIDE, CARD, FIELD = "#0c1320", "#101a2b", "#152238", "#0e192a"
TEXT, MUTED, ACCENT = "#e8eef7", "#9bacc4", "#54d8cb"


def label(parent, text="", size=10, color=TEXT, bold=False, **kwargs):
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        bg=parent.cget("background"),
        fg=color,
        **kwargs,
    )


def build(app):
    a = app
    a.root.configure(bg=BG)
    a.watch_kind = tk.StringVar(value="int32")
    a.metrics = [tk.StringVar(value=v) for v in ("—", "0", "Not scanned")]
    a.buttons, a.tables, a.sorts = {}, {}, {}
    style = ttk.Style(a.root)
    style.configure(".", font=("Segoe UI", 10))
    style.configure(
        "TButton", padding=(12, 9), background="#273850", foreground=TEXT, borderwidth=0
    )
    style.map(
        "TButton",
        background=[("active", "#334b69"), ("disabled", "#19283d")],
        foreground=[("disabled", "#8394aa")],
    )
    style.configure(
        "Accent.TButton", background=ACCENT, foreground="#082825", font=("Segoe UI", 10, "bold")
    )
    style.map(
        "Accent.TButton",
        background=[("active", "#7be9de"), ("disabled", "#23494e")],
        foreground=[("disabled", "#819caa")],
    )
    style.configure("Nav.TButton", background=SIDE, foreground=MUTED, anchor="w", padding=(14, 13))
    style.map("Nav.TButton", background=[("active", "#1c3049")])
    style.configure("Selected.Nav.TButton", background="#203b50", foreground=ACCENT)
    style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=7)
    style.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT, padding=7, arrowsize=14)
    style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)])
    style.configure(
        "Treeview",
        background=CARD,
        fieldbackground=CARD,
        foreground=TEXT,
        rowheight=34,
        borderwidth=0,
        font=("Consolas", 10),
    )
    style.configure(
        "Treeview.Heading",
        background="#1b2c44",
        foreground=MUTED,
        padding=(9, 11),
        font=("Segoe UI", 9, "bold"),
        relief="flat",
    )
    style.map(
        "Treeview", background=[("selected", "#235069")], foreground=[("selected", "#ffffff")]
    )
    style.configure("TProgressbar", background=ACCENT, troughcolor=BG, thickness=3)

    def button(parent, text, command, key=None, accent=False):
        b = ttk.Button(
            parent, text=text, command=command, style="Accent.TButton" if accent else "TButton"
        )
        if key:
            a.buttons[key] = b
        return b

    def field(parent, title, var, values=None):
        label(parent, title, 9, MUTED).pack(anchor="w", pady=(9, 4))
        w = (
            ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
            if values
            else ttk.Entry(parent, textvariable=var)
        )
        w.pack(fill="x")
        return w

    def table(parent, columns, width=150, empty="No session activity yet"):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=4, selectmode="browse")
        for col in columns:
            tree.heading(col, text=col.upper(), command=lambda c=col: a.sort_table(tree, c))
            tree.column(col, width=width, minwidth=65, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(frame, command=tree.yview, orient="vertical")
        sy.grid(row=0, column=1, sticky="ns")
        sx = ttk.Scrollbar(frame, command=tree.xview, orient="horizontal")
        sx.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.tag_configure("even", background=CARD)
        tree.tag_configure("odd", background="#18283e")
        tree.tag_configure("changed", foreground=ACCENT)
        tree.tag_configure("failed", foreground="#ffb89b")
        placeholder = label(frame, empty, 11, MUTED, justify="center", anchor="center")
        placeholder.place(relx=0.5, rely=0.48, anchor="center")
        tree.bind("<<TreeviewSelect>>", lambda _: a.update_controls())
        a.tables[tree] = {"placeholder": placeholder, "rows": None}
        return tree

    a.root.columnconfigure(1, weight=1)
    a.root.rowconfigure(0, weight=1)
    side = tk.Frame(a.root, bg=SIDE, width=180)
    side.grid(row=0, column=0, sticky="nsew")
    side.pack_propagate(False)
    brand = tk.Frame(side, bg=SIDE)
    brand.pack(fill="x", padx=20, pady=(28, 30))
    mark = label(brand, "CC", 18, "#092c2b", True, padx=10, pady=6)
    mark.configure(bg=ACCENT)
    mark.pack(anchor="w")
    label(brand, "CheatCraft", 17, bold=True).pack(anchor="w", pady=(12, 0))
    label(brand, "GAME DIAGNOSTICS", 8, MUTED).pack(anchor="w", pady=(4, 0))
    label(side, "WORKSPACE", 8, MUTED).pack(anchor="w", padx=20, pady=(0, 10))
    a.nav = {}
    titles = {
        "search": "Memory search",
        "watches": "Live watches",
        "snapshots": "Snapshots",
        "ai": "AI connection",
        "activity": "Session activity",
    }
    for key, title in titles.items():
        b = ttk.Button(side, text=title, style="Nav.TButton", command=lambda k=key: a.navigate(k))
        b.pack(fill="x", padx=10, pady=3)
        a.nav[key] = b
    foot = tk.Frame(side, bg=SIDE)
    foot.pack(side="bottom", fill="x", padx=18, pady=24)
    label(foot, "●  Local MCP ready", 9, ACCENT).pack(anchor="w")
    label(foot, f"Read-only diagnostics\nWindows x64 · v{VERSION}", 9, MUTED).pack(
        anchor="w", pady=(9, 18)
    )
    main = tk.Frame(a.root, bg=BG, padx=24, pady=20)
    main.grid(row=0, column=1, sticky="nsew")
    main.columnconfigure(0, weight=1)
    main.rowconfigure(4, weight=1)
    header = tk.Frame(main, bg=BG)
    header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    a.page_title = label(header, "Memory search", 25, bold=True)
    a.page_title.pack(side="left")
    button(header, "Export session", a.export, "export").pack(side="right")
    target = tk.Frame(main, bg=CARD, padx=16, pady=13)
    target.grid(row=1, column=0, sticky="ew")
    target.columnconfigure(0, weight=1)
    label(target, size=12, bold=True, textvariable=a.target).grid(row=0, column=0, sticky="w")
    a.target_detail = tk.StringVar(value="Filter by name or PID, then choose a process")
    label(target, size=9, color=MUTED, textvariable=a.target_detail).grid(
        row=1, column=0, sticky="w", pady=(3, 12)
    )
    controls = tk.Frame(target, bg=CARD)
    controls.grid(row=2, column=0, sticky="ew")
    controls.columnconfigure(1, weight=1)
    a.filter_entry = ttk.Entry(controls, textvariable=a.process_filter, width=17)
    a.filter_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    a.process_box = ttk.Combobox(controls, state="readonly", width=30)
    a.process_box.grid(row=0, column=1, sticky="ew", padx=(0, 8))
    a.process_box.bind("<<ComboboxSelected>>", lambda _: a.update_controls())
    button(controls, "Refresh", a.refresh_processes, "refresh").grid(row=0, column=2, padx=(0, 8))
    button(controls, "Attach", a.attach, "attach", True).grid(row=0, column=3)
    button(controls, "Detach", a.detach, "detach").grid(row=0, column=4, padx=(8, 0))
    metrics = tk.Frame(main, bg=BG)
    metrics.grid(row=2, column=0, sticky="ew", pady=13)
    for i, (title, hint) in enumerate(
        [
            ("CANDIDATES", "Observed at last successful scan"),
            ("WATCHED VALUES", "Live reads in the background"),
            ("SCAN COVERAGE", "Initial search completeness"),
        ]
    ):
        metrics.columnconfigure(i, weight=1, uniform="metrics")
        card = tk.Frame(metrics, bg=CARD, padx=16, pady=10)
        card.grid(row=0, column=i, sticky="ew", padx=(0, 10 if i < 2 else 0))
        label(card, title, 8, MUTED, True).pack(anchor="w")
        label(
            card, size=21, color=ACCENT if i == 0 else TEXT, bold=True, textvariable=a.metrics[i]
        ).pack(anchor="w", pady=2)
        label(card, hint, 8, MUTED).pack(anchor="w")
    a.banner = tk.Frame(main, bg="#412e29", padx=12, pady=9)
    a.banner.grid(row=3, column=0, sticky="ew", pady=(0, 10))
    a.banner.columnconfigure(0, weight=1)
    a.banner_text = label(a.banner, "", 9, "#ffcfb4", wraplength=730)
    a.banner_text.grid(row=0, column=0, sticky="ew")
    button(a.banner, "Dismiss", a.banner.grid_remove).grid(row=0, column=1, padx=(12, 0))
    a.banner.grid_remove()
    host = tk.Frame(main, bg=BG)
    host.grid(row=4, column=0, sticky="nsew")
    host.columnconfigure(0, weight=1)
    host.rowconfigure(0, weight=1)
    a.pages, a.page_shells, a.page_canvases = {}, {}, {}
    for key in titles:
        shell = tk.Frame(host, bg=BG)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(0, weight=1)
        canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scroll.set)
        page = tk.Frame(canvas, bg=BG)
        window = canvas.create_window(0, 0, window=page, anchor="nw")

        def adjust(event=None, c=canvas, p=page, w=window):
            c.itemconfigure(
                w, width=c.winfo_width(), height=max(c.winfo_height(), p.winfo_reqheight())
            )
            c.configure(scrollregion=c.bbox("all"))

        canvas.bind("<Configure>", adjust)
        page.bind("<Configure>", adjust)
        a.pages[key] = page
        a.page_shells[key], a.page_canvases[key] = shell, canvas
    search = a.pages["search"]
    search.columnconfigure(0, weight=1)
    search.rowconfigure(0, weight=1)
    candidates = tk.Frame(search, bg=CARD, padx=14, pady=14)
    candidates.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
    label(candidates, "Candidate addresses", 13, bold=True).pack(anchor="w")
    label(candidates, "Values observed at scan time · first 1,000 shown", 9, MUTED).pack(
        anchor="w", pady=(4, 12)
    )
    a.results = table(
        candidates,
        ("address", "type", "value"),
        empty="No candidates yet\nAttach a process and run an exact search.",
    )
    bar = tk.Frame(candidates, bg=CARD)
    bar.pack(fill="x", pady=(12, 0))
    button(bar, "Watch selected", a.watch_selected, "watch_selected", True).pack(side="left")
    button(bar, "Copy address", lambda: a.copy_address(a.results), "copy_result").pack(
        side="left", padx=8
    )
    a.results.bind("<Double-1>", lambda _: a.watch_selected())
    inspector = tk.Frame(search, bg=CARD, padx=16, pady=13)
    inspector.grid(row=0, column=1, sticky="nsew")
    label(inspector, "Scan configuration", 13, bold=True).pack(anchor="w")
    field(inspector, "Value type", a.kind, list(TYPES))
    a.value_entry = field(inspector, "Exact value", a.value)
    field(
        inspector,
        "Refinement mode",
        a.refine_mode,
        ["equal", "changed", "unchanged", "increased", "decreased"],
    )
    button(inspector, "New exact search", lambda: a.search(False), "scan", True).pack(
        fill="x", pady=(13, 6)
    )
    button(inspector, "Refine candidates", lambda: a.search(True), "refine").pack(fill="x")
    field(inspector, "Range start", a.start)
    field(inspector, "Range end (exclusive)", a.end)
    label(inspector, "Aligned reads · 256 MiB budget\n10,000 candidates maximum", 8, MUTED).pack(
        anchor="w", pady=(11, 0)
    )
    # The value also starts a NEW exact scan, regardless of refinement mode.
    watch = tk.Frame(a.pages["watches"], bg=CARD, padx=16, pady=16)
    watch.pack(fill="both", expand=True)
    label(watch, "Runtime values", 14, bold=True).pack(anchor="w")
    label(
        watch,
        "Background refresh · changed values highlighted · addresses can become invalid after reallocations",
        9,
        MUTED,
    ).pack(anchor="w", pady=(4, 12))
    bar = tk.Frame(watch, bg=CARD)
    bar.pack(fill="x", pady=(0, 14))
    for col, (title, var, width) in enumerate(
        [("Address (0x…)", a.address, 22), ("Label", a.label, 16)]
    ):
        label(bar, title, 9, MUTED).grid(row=0, column=col, sticky="w", pady=(0, 5))
        ttk.Entry(bar, textvariable=var, width=width).grid(
            row=1, column=col, sticky="ew", padx=(0, 8)
        )
    label(bar, "Type", 9, MUTED).grid(row=0, column=2, sticky="w", pady=(0, 5))
    ttk.Combobox(
        bar, textvariable=a.watch_kind, values=list(TYPES), state="readonly", width=10
    ).grid(row=1, column=2, padx=(0, 8))
    button(bar, "Add watch", a.watch_manual, "watch_manual", True).grid(row=1, column=3)
    a.watches = table(
        watch,
        ("label", "address", "type", "value"),
        empty="No watched values\nAdd an address or watch a search result.",
    )
    a.watches.bind("<<TreeviewSelect>>", a.select_watch, add="+")
    bar = tk.Frame(watch, bg=CARD)
    bar.pack(fill="x", pady=(12, 0))
    button(bar, "Remove selected", a.unwatch, "unwatch").pack(side="left")
    button(bar, "Copy address", lambda: a.copy_address(a.watches), "copy_watch").pack(
        side="left", padx=8
    )
    button(bar, "Open snapshots", lambda: a.navigate("snapshots")).pack(side="right")
    snapshots = a.pages["snapshots"]
    top = tk.Frame(snapshots, bg=CARD, padx=16, pady=14)
    top.pack(fill="x", pady=(0, 12))
    label(top, "Capture a named baseline", 13, bold=True).pack(anchor="w")
    label(
        top, "Watched values, not a process dump. Reusing a name replaces that snapshot.", 9, MUTED
    ).pack(anchor="w", pady=(4, 10))
    bar = tk.Frame(top, bg=CARD)
    bar.pack(fill="x")
    ttk.Entry(bar, textvariable=a.snapshot, width=24).pack(side="left", padx=(0, 8))
    button(
        bar,
        "Capture snapshot",
        lambda: a.run("snapshot", a.captured, name=a.snapshot.get().strip()),
        "snapshot",
        True,
    ).pack(side="left")
    button(
        bar,
        "Compare with live",
        lambda: a.run("compare", a.compared, name=a.snapshot.get()),
        "compare",
    ).pack(side="left", padx=8)
    button(bar, "Delete", a.delete_snapshot, "delete_snapshot").pack(side="left")
    body = tk.Frame(snapshots, bg=BG)
    body.pack(fill="both", expand=True)
    body.columnconfigure(1, weight=1)
    body.rowconfigure(0, weight=1)
    library = tk.Frame(body, bg=CARD, padx=12, pady=12)
    library.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    label(library, "Saved snapshots", 11, bold=True).pack(anchor="w", pady=(0, 10))
    a.snapshot_table = table(library, ("name", "count"), 100, empty="No snapshots captured")
    a.snapshot_table.bind("<<TreeviewSelect>>", a.select_snapshot, add="+")
    diff = tk.Frame(body, bg=CARD, padx=12, pady=12)
    diff.grid(row=0, column=1, sticky="nsew")
    label(diff, "Baseline → current state", 11, bold=True).pack(anchor="w", pady=(0, 10))
    a.comparison = table(
        diff,
        ("label", "before", "after", "state"),
        105,
        empty="Capture a baseline, then compare\nit with live watched values.",
    )
    ai = tk.Frame(a.pages["ai"], bg=CARD, padx=24, pady=20)
    ai.pack(fill="both", expand=True)
    label(ai, "Your AI. The same live session.", 20, bold=True).pack(anchor="w")
    label(ai, "Connect a compatible stdio MCP client using this configuration.", 10, MUTED).pack(
        anchor="w", pady=(8, 16)
    )
    if getattr(sys, "frozen", False):
        server = {"command": str(HOME / "CheatCraft-MCP.exe"), "args": []}
    else:
        interpreter = Path(sys.executable)
        if interpreter.name.lower() == "pythonw.exe":
            interpreter = interpreter.with_name("python.exe")
        server = {"command": str(interpreter), "args": [str(HOME / "mcp_server.py")]}
    a.mcp_json = dumps({"mcpServers": {"cheatcraft": server}}, indent=2)
    code = tk.Text(
        ai,
        height=9,
        bg=FIELD,
        fg=ACCENT,
        relief="flat",
        font=("Consolas", 10),
        padx=16,
        pady=14,
        wrap="char",
    )
    code.insert("1.0", a.mcp_json)
    code.configure(state="disabled")
    code.pack(fill="x")
    button(ai, "Copy configuration", a.copy_config, accent=True).pack(anchor="w", pady=15)
    label(
        ai,
        "1   Keep this desktop open and attach your target.\n2   Add the server configuration to your AI client.\n3   Ask it to search, refine, watch or compare snapshots.",
        10,
    ).pack(anchor="w", pady=(0, 15))
    label(
        ai,
        "Local authenticated pipe · no network listener\nOnly connect trusted clients: they can read the attached process.\nBridge readiness does not indicate an AI client is connected.",
        9,
        MUTED,
    ).pack(anchor="w")
    activity = a.pages["activity"]
    label(activity, "A local record of session actions and failures.", 10, MUTED).pack(
        anchor="w", pady=(0, 12)
    )
    a.activity = table(activity, ("time", "action", "outcome", "details"))
    footer = tk.Frame(main, bg=BG)
    footer.grid(row=5, column=0, sticky="ew", pady=(13, 0))
    footer.columnconfigure(0, weight=1)
    label(footer, size=9, color=MUTED, textvariable=a.status, wraplength=730).grid(
        row=0, column=0, sticky="w"
    )
    button(footer, "Cancel scan", a.cancel_scan, "cancel").grid(row=0, column=1, padx=(10, 0))
    a.progress = ttk.Progressbar(main, mode="indeterminate")
    a.progress.grid(row=6, column=0, sticky="ew", pady=(9, 0))
    apply_display_scaling(a, side, main, search, candidates, inspector)
    a.navigate("search")


def apply_display_scaling(a, side, main, search, candidates, inspector):
    """Tk font points scale with DPI; explicit pixel geometry must scale as well."""
    scale = max(1.0, a.root.winfo_fpixels("1i") / 96.0)
    a.display_scale = scale

    def pixels(value):
        parts = (
            value
            if isinstance(value, (tuple, list))
            else (value,)
            if isinstance(value, (int, float))
            else a.root.tk.splitlist(str(value))
        )
        values = tuple(round(a.root.winfo_pixels(p) * scale) for p in parts)
        return values[0] if len(values) == 1 else values

    def visit(widget):
        manager = widget.winfo_manager()
        if manager in {"pack", "grid"}:
            info = widget.pack_info() if manager == "pack" else widget.grid_info()
            padding = {
                key: pixels(info[key]) for key in ("padx", "pady", "ipadx", "ipady") if key in info
            }
            if padding:
                (widget.pack_configure if manager == "pack" else widget.grid_configure)(**padding)
        for key in ("padx", "pady", "wraplength"):
            if key in widget.configure() and widget.cget(key):
                widget.configure(**{key: pixels(widget.cget(key))})
        if isinstance(widget, ttk.Treeview):
            for col in widget["columns"]:
                options = widget.column(col)
                widget.column(
                    col,
                    width=round(options["width"] * scale),
                    minwidth=round(options["minwidth"] * scale),
                )
        for child in widget.winfo_children():
            visit(child)

    if scale != 1.0:
        visit(a.root)
    style = ttk.Style(a.root)
    style.configure("TButton", padding=(round(12 * scale), round(9 * scale)))
    style.configure("Nav.TButton", padding=(round(14 * scale), round(13 * scale)))
    style.configure("TEntry", padding=round(7 * scale))
    style.configure("TCombobox", padding=round(7 * scale))
    style.configure("Treeview", rowheight=round(34 * scale))
    style.configure("Treeview.Heading", padding=(round(9 * scale), round(11 * scale)))
    side.configure(width=round(180 * scale))
    width = min(round(1360 * scale), a.root.winfo_screenwidth() - round(60 * scale))
    height = min(round(900 * scale), a.root.winfo_screenheight() - round(80 * scale))
    a.root.geometry(f"{width}x{height}")
    a.root.minsize(min(round(900 * scale), width), min(round(620 * scale), height))
    last = [None]

    def resize(event):
        if event.widget is not a.root:
            return
        compact = event.width / scale < 1180
        if compact == last[0]:
            return
        last[0] = compact
        side.configure(width=round((150 if compact else 180) * scale))
        if compact:
            inspector.grid_configure(
                row=0, column=0, sticky="ew", padx=0, pady=(0, round(12 * scale))
            )
            candidates.grid_configure(row=1, column=0, padx=0)
            search.rowconfigure(0, weight=0)
            search.rowconfigure(1, weight=1)
        else:
            candidates.grid_configure(row=0, column=0, padx=(0, round(13 * scale)), pady=0)
            inspector.grid_configure(row=0, column=1, sticky="nsew", padx=0, pady=0)
            search.rowconfigure(0, weight=1)
            search.rowconfigure(1, weight=0)

    a.root.bind("<Configure>", resize, add="+")

    def wheel(event):
        if isinstance(event.widget, (ttk.Treeview, tk.Text, ttk.Combobox)):
            return
        a.page_canvases[a.current_page].yview_scroll(-1 if event.delta > 0 else 1, "units")

    a.root.bind("<MouseWheel>", wheel, add="+")

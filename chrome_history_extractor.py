#!/usr/bin/env python3
"""
Extract links from Chrome history and save them as bookmarks or a plain-text list.
"""

import os
import shutil
import sqlite3
import tempfile
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone


def find_history() -> str | None:
    """Return the path to the Chrome History file for the current OS, or None."""
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Windows":
        base = os.getenv("LOCALAPPDATA", "")
        candidates = [
            os.path.join(base, "Google", "Chrome", "User Data", "Default", "History"),
            os.path.join(base, "Google", "Chrome", "User Data", "Profile 1", "History"),
            os.path.join(base, "Google", "Chrome", "User Data", "Profile 2", "History"),
        ]
    elif system == "Darwin":
        candidates = [
            os.path.join(home, "Library", "Application Support", "Google", "Chrome", "Default", "History"),
            os.path.join(home, "Library", "Application Support", "Google", "Chrome", "Profile 1", "History"),
        ]
    else:
        candidates = [
            os.path.join(home, ".config", "google-chrome", "Default", "History"),
            os.path.join(home, ".config", "google-chrome", "Profile 1", "History"),
            os.path.join(home, ".config", "chromium", "Default", "History"),
        ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def chrome_timestamp(micros: int) -> str:
    """Convert a Chrome timestamp (microseconds since 1601-01-01) to a readable string."""
    try:
        ts = (micros / 1_000_000) - 11644473600
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "unknown date"


def extract_links(history_path: str, filter_text: str = "") -> list[tuple[str, str, str]]:
    """Read URLs from a Chrome History file, optionally filtered by a substring."""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    shutil.copy2(history_path, tmp)
    try:
        conn = sqlite3.connect(tmp)
        cur = conn.cursor()
        if filter_text.strip():
            cur.execute(
                "SELECT url, title, last_visit_time FROM urls WHERE url LIKE ? ORDER BY last_visit_time DESC",
                (f"%{filter_text.strip()}%",),
            )
        else:
            cur.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC")
        rows = cur.fetchall()
        conn.close()
    finally:
        os.remove(tmp)

    return [(url, title or url, chrome_timestamp(ts)) for url, title, ts in rows]


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def save_html(links: list[tuple[str, str, str]], path: str, label: str = "History") -> None:
    """Save links as a Netscape-format HTML bookmarks file."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_rows = [
        f'        <DT><A HREF="{_escape_html(url)}">{_escape_html(title)} [{date}]</A>'
        for url, title, date in links
    ]
    content = f"""<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- Generated on {now} -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>{label} Bookmarks</TITLE>
<H1>{label}</H1>
<DL><p>
    <DT><H3>{label} — visited pages</H3>
    <DL><p>
{chr(10).join(html_rows)}
    </DL><p>
</DL><p>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_txt(links: list[tuple[str, str, str]], path: str, label: str = "History") -> None:
    """Save links as a plain-text list."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{label} — extracted on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total: {len(links)} pages\n")
        f.write("=" * 60 + "\n\n")
        for url, title, date in links:
            f.write(f"[{date}] {title}\n{url}\n\n")


# ── GUI ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    FILTER_PRESETS = ["wikipedia.org", "youtube.com", "github.com", "reddit.com", ""]

    def __init__(self):
        super().__init__()
        self.title("Chrome History Extractor")
        self.minsize(720, 480)
        self.history_path = find_history()
        self._build_ui()
        if self.history_path:
            status, color = f"History: {self.history_path}", "green"
        else:
            status, color = "Chrome History not found — select it with Browse", "red"
        self.lbl_history.config(text=status, fg=color)

    def _build_ui(self):
        # Row 1 — history file path
        r1 = tk.Frame(self)
        r1.pack(fill="x", padx=8, pady=4)
        self.lbl_history = tk.Label(r1, text="", anchor="w")
        self.lbl_history.pack(side="left", fill="x", expand=True)
        tk.Button(r1, text="Browse…", command=self._browse).pack(side="right")

        # Row 2 — filter
        r2 = tk.Frame(self)
        r2.pack(fill="x", padx=8, pady=4)
        tk.Label(r2, text="Filter:").pack(side="left")
        self.var_filter = tk.StringVar(value="wikipedia.org")
        cmb = ttk.Combobox(r2, textvariable=self.var_filter, values=self.FILTER_PRESETS, width=28)
        cmb.pack(side="left", padx=4)
        tk.Button(r2, text="Search", command=self._search).pack(side="left")
        self.lbl_count = tk.Label(r2, text="")
        self.lbl_count.pack(side="left", padx=10)

        # Row 3 — results table
        r3 = tk.Frame(self)
        r3.pack(fill="both", expand=True, padx=8, pady=2)

        self.tree = ttk.Treeview(r3, columns=("date", "title", "url"), show="headings", selectmode="extended")
        for col, lbl, w in [("date", "Date", 130), ("title", "Title", 280), ("url", "URL", 340)]:
            self.tree.heading(col, text=lbl, anchor="w")
            self.tree.column(col, width=w, stretch=(col != "date"))

        vsb = ttk.Scrollbar(r3, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(r3, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # Row 4 — actions
        r4 = tk.Frame(self)
        r4.pack(fill="x", padx=8, pady=4)
        tk.Button(r4, text="Select All",  command=self._select_all).pack(side="left", padx=2)
        tk.Button(r4, text="Select None", command=self._deselect_all).pack(side="left", padx=2)
        tk.Label(r4, text="  Format:").pack(side="left")
        self.var_format = tk.StringVar(value="html")
        tk.Radiobutton(r4, text="HTML Bookmarks", variable=self.var_format, value="html").pack(side="left")
        tk.Radiobutton(r4, text="TXT",            variable=self.var_format, value="txt").pack(side="left")
        tk.Button(r4, text="Save Selected…", command=self._save,
                  bg="#4CAF50", fg="white", padx=6).pack(side="right")

    # ── event handlers ────────────────────────────────────────────────────────

    def _browse(self):
        p = filedialog.askopenfilename(
            title="Select the Chrome History file",
            filetypes=[("History", "History"), ("All files", "*.*")],
        )
        if p:
            self.history_path = p
            self.lbl_history.config(text=f"History: {p}", fg="green")

    def _search(self):
        if not self.history_path:
            messagebox.showerror("Error", "Please select the Chrome History file first.")
            return
        try:
            links = extract_links(self.history_path, self.var_filter.get())
        except Exception as e:
            messagebox.showerror("Read error", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for url, title, date in links:
            self.tree.insert("", "end", values=(date, title, url))
        self.lbl_count.config(text=f"{len(links)} results")
        if links:
            self.tree.selection_set(self.tree.get_children())

    def _select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def _deselect_all(self):
        self.tree.selection_remove(self.tree.get_children())

    def _save(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select at least one link.")
            return

        links = [
            (self.tree.set(i, "url"), self.tree.set(i, "title"), self.tree.set(i, "date"))
            for i in selection
        ]
        fmt = self.var_format.get()
        label = self.var_filter.get().strip() or "History"
        ext = ".html" if fmt == "html" else ".txt"
        default_name = label.replace(".", "_") + "_bookmarks" + ext

        path = filedialog.asksaveasfilename(
            title="Save as…",
            initialfile=default_name,
            defaultextension=ext,
            filetypes=[("HTML", "*.html"), ("All", "*.*")] if fmt == "html" else [("Text", "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            (save_html if fmt == "html" else save_txt)(links, path, label=label)
            messagebox.showinfo("Saved", f"{len(links)} links saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))


if __name__ == "__main__":
    App().mainloop()

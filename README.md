# Chrome History Extractor

A cross-platform desktop tool that reads your Google Chrome browsing history and lets you export selected links as **HTML bookmarks** or a **plain-text list**.

## Features

- Auto-detects the Chrome `History` file on Windows, macOS, and Linux
- Filter results by domain (wikipedia.org, youtube.com, github.com, reddit.com, or any custom string)
- Browse results in a sortable table (date, title, URL)
- Multi-select rows and export only what you need
- Two export formats:
  - **HTML** — standard Netscape bookmark file, importable in any browser
  - **TXT** — plain-text list for quick reference or scripting

## Requirements

- Python 3.10 or newer (uses `str | None` union syntax)
- No third-party packages — standard library only (`tkinter`, `sqlite3`, `shutil`, `tempfile`)

> `tkinter` is included with most Python distributions. If it is missing on Linux, install it with:
> ```bash
> sudo apt install python3-tk   # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

## Usage

```bash
python chrome_history_extractor.py
```

1. The app auto-locates your Chrome `History` file. If it is not found, click **Browse…** to select it manually.
2. Type a domain in the **Filter** box (or pick a preset from the dropdown) and click **Search**.
3. Use **Select All / Select None** to adjust the selection.
4. Choose **HTML Bookmarks** or **TXT**, then click **Save Selected…**.

> **Note:** Chrome must be closed (or you must use a copy of the file) because Chrome locks the database while it is running. The tool always works on a temporary copy, so your original history is never modified.

## File locations

| OS | Default path |
|----|-------------|
| Windows | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\History` |
| macOS | `~/Library/Application Support/Google/Chrome/Default/History` |
| Linux | `~/.config/google-chrome/Default/History` |

## How it works

Chrome stores browsing history in a SQLite database. The script:
1. Copies the database to a temporary file (avoids locking issues).
2. Queries the `urls` table with an optional `LIKE` filter.
3. Converts Chrome's internal timestamp format (microseconds since 1601-01-01) to UTC datetime strings.
4. Displays results in a GUI and writes the selected subset to the chosen output format.

## License

MIT

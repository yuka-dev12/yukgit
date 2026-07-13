# YukGit – God‑Mode Git Auto‑Committer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

YukGit is a **terminal‑based Git automation tool** that monitors a local repository and automatically commits & pushes changes after a configurable idle period. It features a **live, animated dashboard** with real‑time status, event logs, and progress indicators – all in a beautiful Rich‑powered UI.

![YukGit Demo](https://via.placeholder.com/800x400?text=YukGit+Live+Dashboard)

---

## 🚀 Features

- **Zero‑configuration start** – guides you through first‑time setup.
- **Live dashboard** with:
  - Animated ASCII art (colour‑cycling)
  - Repository info, remote, branch, commit count
  - Real‑time cooldown countdown with progress bar
  - Last operation status (commit / pull / push) with timestamp
  - Scrolling event log (last 5 file changes)
- **Automatic commit** after a cooldown (default 30s, configurable 15‑900s).
- **Smart sync** – if the remote is ahead, it pulls with rebase before pushing.
- **Ignore patterns** – ignore specific files, folders, or glob patterns (e.g., `*.log`, `venv/`).
- **Config persistence** – all settings saved locally in `./config/config.json`.
- **Logging** – every operation logged to `./logs/yukgit.log`.
- **Handles empty repositories** – initialises Git, sets user, and creates `.gitkeep` files for empty folders.

---

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yuka-dev12/yukgit.git
cd yukgit

# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install rich pyfiglet colorama watchdog

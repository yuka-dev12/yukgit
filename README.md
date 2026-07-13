# YukGit – Git Auto‑Committer

> **Stop typing `git add . && git commit -m "..." && git push` – let YukGit do it for you, with style!**

YukGit is a **smart Git automation tool** for developers who want to **stay in the flow**. It watches a local Git repository, intelligently commits changes after a period of inactivity, and automatically synchronises with the remote – all while presenting a **live, animated dashboard** in your terminal.

---

## 🚀 Why YukGit?

- **Stop interrupting your workflow** – no more manual commits after every small change.
- **Stay in sync** – automatically pulls remote changes (with rebase) before pushing, so you never get rejected.
- **Never lose work** – every change is committed after a cooldown, so your progress is always saved.
- **Beautiful terminal UI** – enjoy a live dashboard with ASCII art, colour‑cycling headers, progress bars, and a scrolling event log.
- **Fully configurable** – set your own cooldown, ignore patterns, remote, and branch.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Live Dashboard** | Animated ASCII art, real‑time status, event log, and progress bars – all in your terminal. |
| **Automatic Commits** | Stages and commits changes after a cooldown (configurable 15‑900 seconds). |
| **Smart Sync** | If remote is ahead, pulls with rebase before pushing; retries on failure. |
| **Ignore Patterns** | Ignore specific files, folders, or glob patterns (e.g., `*.log`, `venv/`). |
| **First‑Run Wizard** | Guides you through setting up your repo, remote, branch, and ignore patterns. |
| **Persistent Config** | Saves all settings in `./config/config.json`. |
| **Detailed Logging** | Every operation is logged to `./logs/yukgit.log` for debugging. |
| **Zero Dependencies?** | Requires only 4 lightweight libraries: `rich`, `pyfiglet`, `colorama`, `watchdog`. |
| **Cross‑Platform** | Works on Windows, macOS, and Linux. |

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Git installed and available in your PATH

### Step‑by‑Step

```bash
# Clone the repository
git clone https://github.com/yuka-dev12/yukgit.git
cd yukgit

# (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install rich pyfiglet colorama watchdog

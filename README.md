# YukGit – Git Auto‑Committer

**YukGit** watches a local Git repository that is connected to a remote (e.g., GitHub).  
If your local repo has new commits, it **pushes** them to remote.  
If the remote is ahead in commits, it **pulls** (with rebase) to keep everything in sync – all automatically!

All happening in a specific time rate which you choose.

> **Stop typing `git add . && git commit -m "..." && git push` – let YukGit do it for you, with style!**

---

## 🚀 What It Does

- Monitors a local folder that is a Git repository.
- When you make changes (create, modify, delete files), it waits for a short cooldown.
- Then it automatically:
  - Stages all changes (`git add .`)
  - Commits them with a descriptive message
  - Pushes to the remote
  - If the remote has new commits, it pulls them first (with rebase) to avoid rejection
- All of this is displayed in a beautiful live terminal dashboard.

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
| **Lightweight** | Requires only 4 libraries: `rich`, `pyfiglet`, `colorama`, `watchdog`. |
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

# Run YukGit
python yukgit.py

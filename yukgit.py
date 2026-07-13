#!/usr/bin/env python3
"""
yukgit.py - Git Auto-Committer with Godly Rich UI (Markup‑Safe)
Author: YukGit (based on original backup, enhanced with Rich)
Description: Monitors a local Git repository and automatically commits/pushes
             changes after a configurable cooldown. Supports ignore patterns,
             remote/branch selection, and a live animated dashboard with status panel.
"""

import os
import sys
import time
import json
import fnmatch
import logging
import subprocess
import threading
import itertools
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ----- Third-party imports -----
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from colorama import init, Fore, Style, Back

# Rich imports for Godly UI
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich import box
import pyfiglet

# ----- Init ----
init(autoreset=True)
console = Console()

# ----- Color aliases (for compatibility with older code) -----
C_PRIMARY = Fore.BLUE
C_SECONDARY = Fore.MAGENTA
C_HIGHLIGHT = Fore.CYAN
C_SUCCESS = Fore.GREEN
C_ERROR = Fore.RED
C_WARNING = Fore.YELLOW
C_RESET = Style.RESET_ALL
B_PRIMARY = Back.BLUE
B_SECONDARY = Back.MAGENTA

# ----- Configuration Management -----
SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_DIR = SCRIPT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_FILE = LOG_DIR / "yukgit.log"

DEFAULT_CONFIG = {
    "repo_path": "",
    "remote_url": "",
    "branch": "main",
    "cooldown_seconds": 30,
    "ignore_patterns": []
}


class LoggerSetup:
    """Setup logging configuration"""
    @staticmethod
    def setup():
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
            ]
        )
        return logging.getLogger(__name__)


logger = LoggerSetup.setup()


class ConfigManager:
    """Load and save configuration from ./config/config.json"""
    @staticmethod
    def load() -> Dict:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config: Dict) -> bool:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False


# ----- File System Event Handler (enhanced with status) -----
class YukGitHandler(FileSystemEventHandler):
    """Watchdog handler that triggers Git commits after a cooldown period."""
    def __init__(self, repo_path: str, config: Dict):
        self.repo_path = repo_path
        self.config = config
        self.cooldown_seconds = config.get('cooldown_seconds', 30)
        self.ignore_patterns = config.get('ignore_patterns', [])
        self.timer = None
        self.changes_detected = False
        self.last_event_time = 0
        self.event_log: List[str] = []      # store latest events for UI
        self.commit_count = 0
        self.last_commit_time = None
        self.cooldown_remaining = 0
        self.is_processing = False
        # New status attributes
        self.last_operation_status = "Idle"
        self.last_operation_time = None

        # Parse ignore patterns
        self.ignored_dirs = set()
        self.file_patterns = []
        for pat in self.ignore_patterns:
            if pat.endswith('/'):
                self.ignored_dirs.add(pat[:-1])
            else:
                self.file_patterns.append(pat)

        # Default ignored directories
        self.default_ignored_dirs = {
            '.git', '__pycache__', '.venv', 'venv', 'env',
            'node_modules', 'dist', 'build', '.pytest_cache',
            '.mypy_cache', '.tox', '.eggs', '*.egg-info',
            'coverage', '.coverage', 'htmlcov', '.idea', '.vscode',
            '.DS_Store', 'Thumbs.db'
        }
        self.ignored_dirs.update(self.default_ignored_dirs)
        self.ignored_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib'}

    def should_ignore(self, path: str) -> bool:
        """Determine if a file/directory should be ignored."""
        path_obj = Path(path)
        try:
            rel_path = os.path.relpath(str(path_obj), self.repo_path)
        except ValueError:
            return True

        # Check ignored directory names
        for ignored_dir in self.ignored_dirs:
            if ignored_dir in path_obj.parts:
                return True

        # Check file extension
        if path_obj.suffix in self.ignored_extensions:
            return True

        # Check file patterns
        for pattern in self.file_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True

        return False

    def on_any_event(self, event):
        if self.should_ignore(event.src_path):
            return
        if event.src_path.endswith('.gitkeep'):
            return

        self.changes_detected = True
        self.last_event_time = time.time()
        self.cooldown_remaining = self.cooldown_seconds

        if self.timer:
            self.timer.cancel()

        # Schedule commit after cooldown
        self.timer = threading.Timer(self.cooldown_seconds, self.process_changes)
        self.timer.start()

        # Log change for UI
        try:
            rel_path = os.path.relpath(event.src_path, self.repo_path)
        except:
            rel_path = event.src_path

        event_type = event.event_type.upper()
        icon = {'CREATED':'📄','MODIFIED':'✏️','DELETED':'🗑️','MOVED':'📦'}.get(event_type, '🔄')
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = f"[{timestamp}] {icon} {rel_path}"
        self.event_log.append(entry)
        if len(self.event_log) > 5:
            self.event_log.pop(0)

    def process_changes(self):
        """Stage, commit, and push changes."""
        if self.is_processing:
            return
        self.is_processing = True
        try:
            os.chdir(self.repo_path)

            if not self.has_git_changes():
                self.is_processing = False
                return

            changes = self.get_git_changes()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"Auto-commit {timestamp}\n\n{changes}"

            # Use Rich status spinner
            with console.status("⏳ Committing changes...", spinner="dots"):
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
                self.commit_count += 1
                self.last_commit_time = datetime.now().strftime('%H:%M:%S')
                self.last_operation_status = "✅ Commit successful"
                self.last_operation_time = datetime.now()

            # Push with sync (pull + push)
            push_ok = self.sync_and_push()
            if push_ok:
                self.last_operation_status += " | ✅ Push successful"
            else:
                self.last_operation_status += " | ❌ Push failed (local commit kept)"
            self.last_operation_time = datetime.now()
            self.event_log.clear()

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"Git command failed: {error_msg}")
            self.last_operation_status = f"❌ Git error: {error_msg[:60]}"
            self.last_operation_time = datetime.now()
            console.print(f"❌ Git command failed: {error_msg}", style="red")
        except Exception as e:
            logger.error(f"Error processing changes: {e}")
            self.last_operation_status = f"❌ Error: {str(e)[:60]}"
            self.last_operation_time = datetime.now()
            console.print(f"❌ Error: {e}", style="red")
        finally:
            self.is_processing = False
            self.changes_detected = False
            self.timer = None

    def has_git_changes(self) -> bool:
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, check=True
            )
            return bool(result.stdout.strip())
        except:
            return False

    def get_git_changes(self) -> str:
        """Return a human-readable list of changes for the commit message."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, check=True
            )
            changes = result.stdout.strip()
            if not changes:
                return "No changes detected"

            lines = changes.split('\n')
            formatted = []
            for line in lines:
                if len(line) >= 3:
                    status = line[:2]
                    file_path = line[3:]
                    if ' -> ' in file_path:
                        old, new = file_path.split(' -> ')
                        formatted.append(f"  - [Renamed] {old} → {new}")
                    elif status == '??':
                        formatted.append(f"  - [Untracked] {file_path}")
                    elif 'A' in status:
                        formatted.append(f"  - [Added] {file_path}")
                    elif 'M' in status:
                        formatted.append(f"  - [Modified] {file_path}")
                    elif 'D' in status:
                        formatted.append(f"  - [Deleted] {file_path}")
                    else:
                        formatted.append(f"  - {file_path}")
            return "Changes:\n" + "\n".join(formatted)
        except Exception as e:
            logger.error(f"Error getting git changes: {e}")
            return f"Changes detected (error: {e})"

    def sync_and_push(self, max_retries: int = 5, delay: int = 10) -> bool:
        """
        Push changes to remote, and if remote is ahead, pull (rebase) first.
        Retry on failure.
        """
        remote = self.config.get('remote_url', 'origin')
        branch = self.config.get('branch', 'main')

        for attempt in range(max_retries):
            try:
                with console.status(f"⏳ Push attempt {attempt+1}/{max_retries}...", spinner="dots"):
                    result = subprocess.run(
                        ['git', 'push', remote, branch],
                        capture_output=True, text=True, check=False
                    )

                if result.returncode == 0:
                    console.print(f"✅ Push successful to {remote}", style="green")
                    logger.info(f"Push successful: {remote}/{branch}")
                    return True
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    console.print(f"❌ Push failed: {error_msg}", style="red")
                    logger.error(f"Push failed (attempt {attempt+1}): {error_msg}")

                    # Check if remote is ahead (rejected)
                    if 'rejected' in error_msg.lower() or 'fetch first' in error_msg.lower():
                        console.print("🔄 Remote is ahead. Pulling latest changes...", style="yellow")
                        if self.pull_with_rebase(remote, branch):
                            console.print("✅ Pull successful. Retrying push...", style="green")
                            continue  # Retry push
                        else:
                            console.print("❌ Pull failed. Cannot sync automatically.", style="red")
                            # Attempt to abort rebase if in progress
                            subprocess.run(['git', 'rebase', '--abort'], capture_output=True)
                            break
                    elif 'Could not resolve host' in error_msg or 'Connection refused' in error_msg:
                        console.print("🌐 Internet connection issue detected", style="yellow")

                    if attempt < max_retries - 1:
                        console.print(f"⏳ Waiting {delay} seconds before retry...", style="yellow")
                        time.sleep(delay)
                    else:
                        console.print("❌ All push attempts failed. Changes are committed locally.", style="red")
                        console.print("💡 You can manually sync with: git pull --rebase && git push", style="yellow")
                        logger.warning("Push failed after all retries. Changes remain local.")
                        return False

            except Exception as e:
                logger.error(f"Push error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                else:
                    return False
        return False

    def pull_with_rebase(self, remote: str, branch: str) -> bool:
        """Pull remote changes with rebase."""
        try:
            with console.status("⏳ Pulling with rebase...", spinner="dots"):
                subprocess.run(
                    ['git', 'pull', '--rebase', remote, branch],
                    capture_output=True, text=True, check=True
                )
            console.print("✅ Pull successful", style="green")
            logger.info(f"Pull successful: {remote}/{branch}")
            self.last_operation_status = "✅ Pull successful"
            self.last_operation_time = datetime.now()
            return True
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            console.print(f"❌ Pull failed: {error_msg}", style="red")
            logger.error(f"Pull failed: {error_msg}")
            # Try to abort rebase if it failed
            subprocess.run(['git', 'rebase', '--abort'], capture_output=True)
            self.last_operation_status = f"❌ Pull failed: {error_msg[:60]}"
            self.last_operation_time = datetime.now()
            return False


# ----- Interactive Configuration Functions (unchanged) -----
def print_header(text: str, char: str = '═', width: int = 60):
    """Print a formatted header"""
    print(f"\n{C_PRIMARY}{char*width}")
    print(f"{C_PRIMARY}{char} {C_HIGHLIGHT}{text}{C_RESET}")
    print(f"{C_PRIMARY}{char*width}")

def configure_settings(config: Dict):
    """Guide the user through all configuration options."""
    while True:
        print_header("⚙️  Configuration Settings", '═')
        print(f"\n{C_SECONDARY}📁 Repository Path:")
        print(f"  {C_HIGHLIGHT}{config.get('repo_path', 'Not set')}")
        print(f"\n{C_SECONDARY}🔗 Remote URL:")
        print(f"  {C_HIGHLIGHT}{config.get('remote_url', 'Not set')}")
        print(f"\n{C_SECONDARY}🌿 Branch:")
        print(f"  {C_HIGHLIGHT}{config.get('branch', 'main')}")
        print(f"\n{C_SECONDARY}⏰ Cooldown Interval:")
        print(f"  {C_HIGHLIGHT}{config.get('cooldown_seconds', 30)} seconds")
        print(f"\n{C_SECONDARY}🚫 Ignore Patterns ({len(config.get('ignore_patterns', []))}):")
        for pat in config.get('ignore_patterns', []):
            print(f"  {C_HIGHLIGHT}• {pat}")
        if not config.get('ignore_patterns'):
            print(f"  {C_WARNING}(none)")

        print(f"\n{C_PRIMARY}┌{'─'*58}┐")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}1{C_RESET} - Edit Repository Path       {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}2{C_RESET} - Edit Remote URL           {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}3{C_RESET} - Edit Branch               {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}4{C_RESET} - Edit Cooldown Interval    {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}5{C_RESET} - Manage Ignore Patterns    {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}6{C_RESET} - Save & Return to Menu     {C_PRIMARY}│")
        print(f"{C_PRIMARY}└{'─'*58}┘")

        choice = input(f"\n{C_HIGHLIGHT}Select option (1-6): ").strip()
        if choice == '1':
            print(f"{C_SECONDARY}Current: {config.get('repo_path', 'Not set')}")
            new_path = input(f"{C_HIGHLIGHT}Enter new repository path: ").strip()
            if new_path:
                if os.path.isdir(new_path):
                    config['repo_path'] = os.path.abspath(new_path)
                    print(f"{C_SUCCESS}✅ Repository path updated")
                else:
                    print(f"{C_ERROR}❌ Path does not exist or is not a directory.")
        elif choice == '2':
            print(f"{C_SECONDARY}Current: {config.get('remote_url', 'Not set')}")
            new_url = input(f"{C_HIGHLIGHT}Enter new remote URL: ").strip()
            if new_url:
                config['remote_url'] = new_url
                print(f"{C_SUCCESS}✅ Remote URL updated")
        elif choice == '3':
            print(f"{C_SECONDARY}Current: {config.get('branch', 'main')}")
            new_branch = input(f"{C_HIGHLIGHT}Enter new branch name: ").strip()
            if new_branch:
                config['branch'] = new_branch
                print(f"{C_SUCCESS}✅ Branch updated")
        elif choice == '4':
            current = config.get('cooldown_seconds', 30)
            print(f"{C_SECONDARY}Current: {current} seconds")
            cooldown_input = input(f"{C_HIGHLIGHT}Enter new interval (15-900 seconds): ").strip()
            if cooldown_input:
                try:
                    seconds = int(cooldown_input)
                    if 15 <= seconds <= 900:
                        config['cooldown_seconds'] = seconds
                        print(f"{C_SUCCESS}✅ Cooldown updated to {seconds} seconds")
                    else:
                        print(f"{C_ERROR}❌ Interval must be between 15 and 900 seconds.")
                except ValueError:
                    print(f"{C_ERROR}❌ Please enter a valid number.")
        elif choice == '5':
            manage_ignore(config)
        elif choice == '6':
            if ConfigManager.save(config):
                print(f"{C_SUCCESS}✅ Configuration saved successfully!")
            else:
                print(f"{C_ERROR}❌ Failed to save configuration.")
            time.sleep(1)
            break
        else:
            print(f"{C_ERROR}❌ Invalid option. Please choose 1-6.")


def manage_ignore(config: Dict):
    """Interactive management of ignore patterns."""
    ignore_list = config.get('ignore_patterns', [])
    while True:
        print_header("🚫 Manage Ignore Patterns", '─')
        if ignore_list:
            print(f"\n{C_SECONDARY}Current patterns:")
            for idx, pat in enumerate(ignore_list, 1):
                print(f"  {C_HIGHLIGHT}{idx}.{C_RESET} {pat}")
        else:
            print(f"\n{C_WARNING}No patterns configured.")
        print(f"\n{C_PRIMARY}┌{'─'*58}┐")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}A{C_RESET} - Add new pattern             {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}R{C_RESET} - Remove pattern             {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}C{C_RESET} - Clear all patterns         {C_PRIMARY}│")
        print(f"{C_PRIMARY}│ {C_HIGHLIGHT}B{C_RESET} - Back to main config       {C_PRIMARY}│")
        print(f"{C_PRIMARY}└{'─'*58}┘")
        choice = input(f"\n{C_HIGHLIGHT}Select option: ").strip().upper()
        if choice == 'A':
            print(f"\n{C_SECONDARY}Pattern examples:")
            print(f"  {C_HIGHLIGHT}• hello.txt{C_RESET} - ignore specific file")
            print(f"  {C_HIGHLIGHT}• hello/{C_RESET} - ignore entire directory")
            print(f"  {C_HIGHLIGHT}• *.log{C_RESET} - ignore all .log files")
            print(f"  {C_HIGHLIGHT}• src/secret.py{C_RESET} - ignore specific path")
            pattern = input(f"\n{C_HIGHLIGHT}Enter pattern: ").strip()
            if pattern:
                ignore_list.append(pattern)
                print(f"{C_SUCCESS}✅ Added pattern: {pattern}")
        elif choice == 'R':
            if ignore_list:
                try:
                    idx = int(input(f"{C_HIGHLIGHT}Enter pattern number to remove: ").strip()) - 1
                    if 0 <= idx < len(ignore_list):
                        removed = ignore_list.pop(idx)
                        print(f"{C_SUCCESS}✅ Removed pattern: {removed}")
                    else:
                        print(f"{C_ERROR}❌ Invalid index.")
                except ValueError:
                    print(f"{C_ERROR}❌ Please enter a valid number.")
            else:
                print(f"{C_WARNING}No patterns to remove.")
        elif choice == 'C':
            confirm = input(f"{C_WARNING}Are you sure you want to clear all patterns? (y/n): ").strip().lower()
            if confirm == 'y':
                ignore_list.clear()
                print(f"{C_SUCCESS}✅ All patterns cleared.")
        elif choice == 'B':
            break
        else:
            print(f"{C_ERROR}❌ Invalid option.")


def show_settings(config: Dict):
    """Display the current configuration."""
    print_header("📋 Current Settings", '═')
    settings = {
        "Repository Path": config.get('repo_path', 'Not set'),
        "Remote URL": config.get('remote_url', 'Not set'),
        "Branch": config.get('branch', 'main'),
        "Cooldown": f"{config.get('cooldown_seconds', 30)} seconds",
        "Ignore Patterns": len(config.get('ignore_patterns', []))
    }
    for key, value in settings.items():
        print(f"{C_SECONDARY}{key}:{C_RESET} {C_HIGHLIGHT}{value}")
    if config.get('ignore_patterns'):
        print(f"\n{C_SECONDARY}Patterns:")
        for pat in config.get('ignore_patterns', []):
            print(f"  {C_HIGHLIGHT}• {pat}")
    print(f"\n{C_SECONDARY}Config File:{C_RESET} {C_HIGHLIGHT}{CONFIG_FILE}")
    print(f"{C_SECONDARY}Log File:{C_RESET} {C_HIGHLIGHT}{LOG_FILE}")


# ----- Git Repository Helpers (unchanged) -----
def ensure_git_repo(repo_path: str) -> bool:
    """Check if folder is a Git repo; if not, offer to initialise."""
    git_dir = os.path.join(repo_path, '.git')
    if os.path.exists(git_dir):
        return True

    print(f"\n{C_WARNING}╔{'═'*58}╗")
    print(f"{C_WARNING}║ ⚠️  Repository not initialized!{C_RESET}")
    print(f"{C_WARNING}╚{'═'*58}╝")
    choice = input(f"\n{C_HIGHLIGHT}Initialize Git repository here? (y/n): ").strip().lower()
    if choice != 'y':
        print(f"{C_WARNING}Cannot monitor non-git repository.")
        return False

    try:
        print(f"{C_HIGHLIGHT}📦 Initializing Git repository...")
        subprocess.run(['git', 'init'], cwd=repo_path, check=True, capture_output=True)
        print(f"{C_SUCCESS}✅ Git repository initialized.")
        setup_git_user(repo_path)
        remote = input(f"{C_HIGHLIGHT}Enter remote URL (optional, press Enter to skip): ").strip()
        if remote:
            subprocess.run(['git', 'remote', 'add', 'origin', remote], cwd=repo_path, check=True, capture_output=True)
            print(f"{C_SUCCESS}✅ Remote 'origin' set to {remote}")
        files = os.listdir(repo_path)
        files = [f for f in files if f != '.git']
        if files:
            initial_commit = input(f"{C_HIGHLIGHT}Create initial commit? (y/n): ").strip().lower()
            if initial_commit == 'y':
                subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True, capture_output=True)
                try:
                    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, check=True, capture_output=True)
                    print(f"{C_SUCCESS}✅ Initial commit created.")
                    logger.info(f"Initial commit created in {repo_path}")
                except subprocess.CalledProcessError as e:
                    error_msg = e.stderr.decode() if e.stderr else str(e)
                    if "nothing to commit" in error_msg:
                        print(f"{C_WARNING}No changes to commit. Add files first.")
                    else:
                        print(f"{C_ERROR}❌ Failed to create initial commit: {error_msg}")
        else:
            print(f"{C_WARNING}No files to commit. Create some files first.")
            print(f"{C_WARNING}💡 You can add files later and commit manually.")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"Failed to initialize Git: {error_msg}")
        print(f"{C_ERROR}❌ Failed to initialize Git: {error_msg}")
        return False


def setup_git_user(repo_path: str):
    """Ensure git user.name and user.email are configured."""
    try:
        os.chdir(repo_path)
        result = subprocess.run(['git', 'config', 'user.name'], capture_output=True, text=True)
        if not result.stdout.strip():
            print(f"{C_WARNING}Git user.name not set.")
            name = input(f"{C_HIGHLIGHT}Enter your Git username: ").strip()
            if name:
                subprocess.run(['git', 'config', 'user.name', name], check=True)
                logger.info(f"Git user.name set to: {name}")
        result = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True)
        if not result.stdout.strip():
            print(f"{C_WARNING}Git user.email not set.")
            email = input(f"{C_HIGHLIGHT}Enter your Git email: ").strip()
            if email:
                subprocess.run(['git', 'config', 'user.email', email], check=True)
                logger.info(f"Git user.email set to: {email}")
    except Exception as e:
        logger.error(f"Error setting Git config: {e}")
        print(f"{C_ERROR}❌ Error setting Git config: {e}")


def setup_gitkeep_folders(repo_path: str):
    """Create .gitkeep files in empty folders."""
    try:
        print(f"{C_HIGHLIGHT}🔍 Checking for empty folders...")
        count = 0
        for root, dirs, files in os.walk(repo_path):
            if '.git' in root:
                continue
            if not files and not dirs:
                try:
                    gitkeep_path = Path(root) / '.gitkeep'
                    gitkeep_path.touch()
                    rel_path = os.path.relpath(root, repo_path)
                    print(f"{C_SUCCESS}📌 Created .gitkeep in: {rel_path}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error creating .gitkeep in {root}: {e}")
        if count > 0:
            print(f"{C_SUCCESS}✅ Created {count} .gitkeep files in empty folders")
    except Exception as e:
        logger.error(f"Error scanning for empty folders: {e}")


# ----- Monitoring with Rich Live Dashboard (with Status Panel) -----
def start_monitoring(config: Dict):
    """Start the watchdog with a live Rich dashboard."""
    repo_path = config.get('repo_path')
    if not repo_path or not os.path.isdir(repo_path):
        console.print("❌ Repository path is not set or invalid.", style="red")
        console.print("💡 Please configure settings first.", style="yellow")
        return

    if not ensure_git_repo(repo_path):
        return

    setup_git_user(repo_path)
    setup_gitkeep_folders(repo_path)

    handler = YukGitHandler(repo_path, config)
    observer = Observer()
    observer.schedule(handler, repo_path, recursive=True)

    # Color cycle for the banner
    colors = ["red", "green", "yellow", "blue", "magenta", "cyan", "white"]
    color_cycle = itertools.cycle(colors)

    def build_dashboard():
        """Construct the Rich layout for the live display."""
        # Animated ASCII art with rotating color
        ascii_art = pyfiglet.figlet_format("YukGit", font="small")
        color = next(color_cycle)
        header_text = Text(ascii_art, style=f"bold {color}")
        header_text.append("\nAuto Git Committer v2.1   (Godly UI)", style="cyan")

        # Status table (existing)
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_row("Repository", repo_path)
        table.add_row("Remote", config.get('remote_url', 'Not set'))
        table.add_row("Branch", config.get('branch', 'main'))
        table.add_row("Commits", str(handler.commit_count))
        table.add_row("Last Commit", handler.last_commit_time or "None")
        cooldown = f"{handler.cooldown_remaining:.0f}s" if handler.changes_detected else "Idle"
        table.add_row("Cooldown", cooldown)

        # ---- New Status Panel ----
        status_lines = []
        # Operation status
        if handler.is_processing:
            status_lines.append("⏳ Processing...")
        else:
            status_lines.append(handler.last_operation_status or "Idle")
        # Last operation time
        if handler.last_operation_time:
            status_lines.append(f"at {handler.last_operation_time.strftime('%H:%M:%S')}")
        # Commit count
        status_lines.append(f"Total commits: {handler.commit_count}")
        # Cooldown progress bar (if changes detected)
        if handler.changes_detected and handler.cooldown_remaining > 0:
            progress = 100 - (handler.cooldown_remaining / handler.cooldown_seconds * 100)
            bar_len = 20
            filled = int(bar_len * progress / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            status_lines.append(f"Cooldown: [{bar}] {handler.cooldown_remaining:.1f}s")
        else:
            status_lines.append("Cooldown: Idle")

        status_text = "\n".join(status_lines)
        status_panel = Panel(status_text, title="Status", border_style="green")

        # Event log panel
        log_lines = "\n".join(handler.event_log[-5:]) if handler.event_log else "⏳ Waiting for changes..."
        log_panel = Panel(log_lines, title="Event Log (last 5)", border_style="yellow")

        # Combine into a layout: now we have 4 components
        layout = Layout()
        layout.split(
            Layout(header_text, size=8),
            Layout(table, size=10),
            Layout(status_panel, size=6),
            Layout(log_panel),
        )
        return Panel(layout, title="YukGit Dashboard", border_style="blue")

    try:
        observer.start()
        with Live(build_dashboard(), refresh_per_second=4, screen=True) as live:
            while True:
                # Update cooldown counter
                if handler.changes_detected and not handler.is_processing:
                    if handler.cooldown_remaining > 0:
                        handler.cooldown_remaining -= 0.25
                live.update(build_dashboard())
                time.sleep(0.25)
    except KeyboardInterrupt:
        console.print("\n🛑 Stopping watchdog...", style="yellow")
        observer.stop()
        if handler.timer:
            handler.timer.cancel()
        console.print("✅ Monitoring stopped.", style="green")
        logger.info("Monitoring stopped by user")
    observer.join()


# ----- View Logs (unchanged) -----
def view_logs():
    """Display the log file content."""
    if not LOG_FILE.exists():
        print(f"{C_WARNING}No log file found yet.")
        return

    print_header("📋 View Logs", '═')
    print(f"{C_SECONDARY}Log file: {LOG_FILE}")
    print(f"{C_SECONDARY}Latest 50 entries:{C_RESET}\n")

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-50:]:
                if 'ERROR' in line:
                    print(f"{C_ERROR}{line.strip()}")
                elif 'WARNING' in line:
                    print(f"{C_WARNING}{line.strip()}")
                elif 'INFO' in line:
                    print(f"{C_HIGHLIGHT}{line.strip()}")
                else:
                    print(line.strip())
    except Exception as e:
        print(f"{C_ERROR}Error reading log: {e}")

    input(f"\n{C_WARNING}Press Enter to continue...")


# ----- Main Menu (with Rich banner, markup‑free) -----
def print_banner():
    """Print the application banner using Rich and pyfiglet."""
    console.clear()
    ascii_art = pyfiglet.figlet_format("YukGit", font="standard")
    console.print(ascii_art, style="bold magenta")
    console.print("Auto Git Committer v2.1   (Godly UI)", style="cyan")


def main():
    """Main entry point."""
    config = ConfigManager.load()

    if not config.get('repo_path'):
        console.print("⚠️  No configuration found. Let's set up YukGit!", style="yellow")
        configure_settings(config)
        config = ConfigManager.load()

    while True:
        print_banner()
        console.print("\n📌 Current Settings:", style="cyan")
        console.print(f"  Repo: {config.get('repo_path', 'Not set')[:50]}")
        console.print(f"  Remote: {config.get('remote_url', 'Not set')[:50]}")
        console.print(f"  Cooldown: {config.get('cooldown_seconds', 30)}s | Ignored: {len(config.get('ignore_patterns', []))} patterns")

        console.print("\n┌──────────────────────────────────────────────────────────┐", style="blue")
        console.print("│ 1  Start Monitoring", style="blue")
        console.print("│ 2  Configure Settings", style="blue")
        console.print("│ 3  Show Current Settings", style="blue")
        console.print("│ 4  View Logs", style="blue")
        console.print("│ 5  Exit", style="blue")
        console.print("└──────────────────────────────────────────────────────────┘", style="blue")

        choice = input("Choose option (1-5): ").strip()

        if choice == '1':
            start_monitoring(config)
        elif choice == '2':
            configure_settings(config)
            config = ConfigManager.load()
        elif choice == '3':
            show_settings(config)
            input("\nPress Enter to continue...")
        elif choice == '4':
            view_logs()
        elif choice == '5':
            console.print("👋 Thank you for using YukGit!", style="green")
            sys.exit(0)
        else:
            console.print("❌ Invalid option. Please choose 1-5.", style="red")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        console.print(f"❌ Fatal error: {e}", style="red")
        sys.exit(1)
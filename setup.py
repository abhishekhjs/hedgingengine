#!/usr/bin/env python3
"""Bootstrap script for the Japan Manufacturing Market Risk Monitor.

This script fully sets up the development environment:
1. Verifies Python version (3.11+)
2. Creates a virtual environment
3. Installs dependencies
4. Creates .env from .env.example if missing
5. Initializes the SQLite database
6. Checks data source connectivity
7. Runs the initial 5-year historical backfill
8. Launches the Streamlit dashboard

Usage:
    python setup.py
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
DATA_DIR = PROJECT_ROOT / "data"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"


def print_header(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def print_step(step: int, msg: str):
    print(f"  [{step}/8] {msg}")


def check_python_version():
    """Verify Python version is 3.11+."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 11):
        print(
            f"ERROR: Python 3.11+ is required, but you have Python {major}.{minor}.\n"
            f"Please install Python 3.11 or later from https://www.python.org/downloads/"
        )
        sys.exit(1)
    print(f"  Python {major}.{minor}.{sys.version_info[2]} ✅")


def create_venv():
    """Create virtual environment if it doesn't exist."""
    if VENV_DIR.exists():
        print(f"  Virtual environment already exists at {VENV_DIR} ✅")
        return

    print(f"  Creating virtual environment at {VENV_DIR}...")
    subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        check=True,
    )
    print(f"  Virtual environment created ✅")


def get_venv_python() -> str:
    """Get the path to the Python executable in the venv."""
    if os.name == "nt":
        python = VENV_DIR / "Scripts" / "python.exe"
    else:
        python = VENV_DIR / "bin" / "python"

    if not python.exists():
        # Fall back to system Python if venv python doesn't exist
        return sys.executable
    return str(python)


def get_venv_streamlit() -> str:
    """Get the path to the Streamlit executable in the venv."""
    if os.name == "nt":
        return str(VENV_DIR / "Scripts" / "streamlit.exe")
    else:
        return str(VENV_DIR / "bin" / "streamlit")


def install_dependencies():
    """Install all packages from requirements.txt into the venv."""
    python = get_venv_python()
    print(f"  Installing dependencies from {REQUIREMENTS}...")
    result = subprocess.run(
        [python, "-m", "pip", "install", "-r", str(REQUIREMENTS), "--quiet"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ERROR: pip install failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  All dependencies installed ✅")


def setup_env_file():
    """Create .env from .env.example if it doesn't exist."""
    if ENV_FILE.exists():
        print(f"  .env file already exists ✅")
        # Check if the key is still the placeholder
        content = ENV_FILE.read_text()
        if "your_key_here" in content:
            print(
                "\n  ⚠️  WARNING: Your .env file still has the placeholder FRED_API_KEY.\n"
                "  Please edit .env and replace 'your_key_here' with your actual key.\n"
                "  Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html\n"
            )
        return

    if not ENV_EXAMPLE.exists():
        print("  ERROR: .env.example not found — cannot create .env")
        sys.exit(1)

    shutil.copy(str(ENV_EXAMPLE), str(ENV_FILE))
    print(f"  Created .env from .env.example")
    print(
        "\n  ⚠️  ACTION REQUIRED: Edit the .env file and add your FRED API key.\n"
        "  Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html\n"
        "  The app will not be able to fetch oil price data without this key.\n"
    )


def initialize_database():
    """Create the data directory and initialize the SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    python = get_venv_python()
    result = subprocess.run(
        [python, "-c", "from src.db.schema import initialize_db; initialize_db()"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"  ERROR: Database initialization failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  Database initialized at {DATA_DIR / 'market_data.db'} ✅")


def check_connectivity():
    """Check connectivity to all data sources."""
    python = get_venv_python()
    result = subprocess.run(
        [
            python, "-c",
            "from src.ingestion.runner import check_source_connectivity; "
            "import json; print(json.dumps(check_source_connectivity()))"
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"  WARNING: Connectivity check failed:\n{result.stderr}")
        return

    import json
    try:
        connectivity = json.loads(result.stdout.strip())
        for source, reachable in connectivity.items():
            status = "✅ reachable" if reachable else "❌ unreachable"
            print(f"    {source}: {status}")
    except (json.JSONDecodeError, ValueError):
        print(f"  Could not parse connectivity results: {result.stdout}")


def run_initial_backfill():
    """Run the initial 5-year historical data backfill."""
    python = get_venv_python()
    print("  Running initial 5-year historical backfill (this may take a few minutes)...")
    result = subprocess.run(
        [python, str(PROJECT_ROOT / "run_ingestion.py")],
        cwd=str(PROJECT_ROOT),
        timeout=600,  # 10-minute timeout
    )
    if result.returncode == 0:
        print("  Initial backfill completed successfully ✅")
    elif result.returncode == 1:
        print("  Initial backfill completed with some warnings (partial data) ⚠️")
    else:
        print("  Initial backfill failed ❌")
        print("  The dashboard will launch but may have limited or no data.")
        print("  Try clicking 'Refresh Data' in the dashboard to retry.")


def launch_dashboard():
    """Launch the Streamlit dashboard."""
    streamlit = get_venv_streamlit()
    if not Path(streamlit).exists():
        # Fall back to module invocation
        python = get_venv_python()
        cmd = [python, "-m", "streamlit", "run", str(PROJECT_ROOT / "app.py")]
    else:
        cmd = [streamlit, "run", str(PROJECT_ROOT / "app.py")]

    print(f"  Starting Streamlit dashboard...")
    print(f"  The dashboard will open in your default browser.\n")
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))


def main():
    print_header("Japan Manufacturing Market Risk Monitor — Setup")

    print_step(1, "Checking Python version...")
    check_python_version()

    print_step(2, "Setting up virtual environment...")
    create_venv()

    print_step(3, "Installing dependencies...")
    install_dependencies()

    print_step(4, "Setting up .env file...")
    setup_env_file()

    print_step(5, "Initializing database...")
    initialize_database()

    print_step(6, "Checking data source connectivity...")
    check_connectivity()

    print_step(7, "Running initial data backfill...")
    run_initial_backfill()

    print_step(8, "Launching dashboard...")
    launch_dashboard()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Download wheels for all services to enable offline Docker builds.
Run this on a machine with PyPI access to populate wheelhouse/.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd=None) -> bool:
    """Run command and return success status (stdout printed)."""
    print(f"Running: {' '.join(cmd)} in {cwd or '.'}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Error (exit {result.returncode}):\n{result.stderr}")
        return False
    if result.stdout:
        print(result.stdout)
    return True


def download_with_platform(
    requirement: str, wheelhouse_dir: Path, python_version: str = "311"
) -> None:
    """Download a single requirement (e.g. 'fastapi==0.111.0') for host and target container platform."""
    run_command([sys.executable, "-m", "pip", "download", requirement, "-d", str(wheelhouse_dir)])
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            requirement,
            "-d",
            str(wheelhouse_dir),
            "--platform",
            "manylinux2014_x86_64",
            "--only-binary",
            ":all:",
            "--python-version",
            python_version,
            "--implementation",
            "cp",
            "--abi",
            "cp311",
        ]
    )


def download_requirements_file(
    requirements_file: Path, wheelhouse_dir: Path, python_version: str = "311"
) -> None:
    """Download all requirements from a requirements.txt file for host and target platform.

    We must pass '-r' and the path as separate arguments (previous implementation passed them combined
    which pip treated as a literal requirement string causing 'Invalid argument' errors).
    """
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-r",
            str(requirements_file),
            "-d",
            str(wheelhouse_dir),
        ]
    )
    run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-r",
            str(requirements_file),
            "-d",
            str(wheelhouse_dir),
            "--platform",
            "manylinux2014_x86_64",
            "--only-binary",
            ":all:",
            "--python-version",
            python_version,
            "--implementation",
            "cp",
            "--abi",
            "cp311",
        ]
    )


def main():
    repo_root = Path(__file__).parent.parent  # Go up from scripts/ to repo root
    wheelhouse_dir = repo_root / "wheelhouse"
    wheelhouse_dir.mkdir(exist_ok=True)

    services = ["mcp-gateway", "mcp-policy", "mcp-audit", "mcp-lineage"]

    for service in services:
        service_dir = repo_root / "services" / service
        requirements_file = service_dir / "requirements.txt"

        if not requirements_file.exists():
            print(f"Warning: {requirements_file} not found, skipping {service}")
            continue

        print(f"\nDownloading wheels for {service}...")
        download_requirements_file(requirements_file, wheelhouse_dir)

    # Download common dependencies that all services might need
    print("\nDownloading common base dependencies...")
    # Common direct dependencies (match service pins: pydantic==2.7.4 so that its transitive
    # dependency pydantic-core==2.18.4 for cp311 manylinux is downloaded). We previously
    # downloaded pydantic==2.12.4 which pulled pydantic-core 2.41.5; that did not satisfy
    # pydantic==2.7.4 runtime metadata. This list ensures the correct core wheel exists.
    common_deps = [
        "fastapi==0.111.0",
        "uvicorn[standard]==0.30.1",
        "pydantic==2.7.4",
        "httpx==0.28.1",
        "PyYAML==6.0.1",
        "orjson==3.11.4",
        "ujson==5.11.0",
        "watchfiles==1.1.1",
        # Add uvloop explicitly to satisfy uvicorn[standard] extras offline
        "uvloop==0.19.0",
    ]

    for dep in common_deps:
        download_with_platform(dep, wheelhouse_dir)

    print(f"\nWheels downloaded to {wheelhouse_dir}")
    print("Docker builds can now use --no-index --find-links for offline installation on linux")

    return 0


if __name__ == "__main__":
    sys.exit(main())

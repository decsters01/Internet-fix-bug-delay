from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


def _agent_debug_log(project_root: Path, *, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    # region agent log
    try:
        p = project_root / ".cursor" / "debug.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "sessionId": "debug-session",
                    "runId": run_id,
                    "hypothesisId": hypothesis_id,
                    "location": location,
                    "message": message,
                    "data": data,
                    "timestamp": int(time.time() * 1000),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    except Exception:
        pass
    # endregion


@dataclass(frozen=True)
class BuildConfig:
    entry: Path
    name: str
    onefile: bool
    console: bool
    hidden_imports: list[str]
    keep_temp: bool
    log_file: Path


def _sanitize_exe_name(name: str) -> str:
    # PyInstaller is tolerant, but keep it simple for Windows filenames
    cleaned = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in name.strip())
    return cleaned or "app"


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    log_file: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    cmd_str = " ".join([subprocess.list2cmdline([a]) if " " in a else a for a in args])
    prefix = f"[cmd] {cmd_str}\n"

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(log_file.read_text(encoding="utf-8", errors="ignore") + prefix, encoding="utf-8") if log_file.exists() else log_file.write_text(prefix, encoding="utf-8")

    print(prefix, end="")

    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    out = proc.stdout or ""
    if log_file is not None and out:
        log_file.write_text(log_file.read_text(encoding="utf-8", errors="ignore") + out, encoding="utf-8")

    if out:
        print(out, end="")

    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit {proc.returncode}): {cmd_str}")


def _load_optional_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Failed to read config: {config_path} ({e})")


def _default_app_name(project_root: Path) -> str:
    return _sanitize_exe_name(project_root.name.replace(" ", "_"))


def _parse_args(project_root: Path) -> tuple[BuildConfig, Path]:
    # First pass: read only --config without hijacking --help output.
    parser = argparse.ArgumentParser(
        description="Build .exe using a temporary venv + pipreqs + PyInstaller",
        add_help=False,
    )
    parser.add_argument("--config", default="build_config.json", help="Optional config JSON file")
    args0, _ = parser.parse_known_args()

    config_path = (project_root / args0.config).resolve()
    cfg = _load_optional_config(config_path)

    parser = argparse.ArgumentParser(description="Build .exe using a temporary venv + pipreqs + PyInstaller")

    parser.add_argument("--config", default=str(config_path), help="Optional config JSON file")

    parser.add_argument("--entry", default=cfg.get("entry", "main.py"), help="Entry point .py file")
    parser.add_argument("--name", default=cfg.get("name", _default_app_name(project_root)), help="Executable name")

    # Defaults: onefile + console (as per your plan)
    parser.add_argument("--onefile", action=argparse.BooleanOptionalAction, default=cfg.get("onefile", True))
    parser.add_argument("--console", action=argparse.BooleanOptionalAction, default=cfg.get("console", True))

    parser.add_argument(
        "--hidden-import",
        dest="hidden_imports",
        action="append",
        default=cfg.get("hidden_imports", []),
        help="Repeatable. Add PyInstaller hidden imports (for dynamic imports)",
    )

    parser.add_argument("--keep-temp", action=argparse.BooleanOptionalAction, default=cfg.get("keep_temp", False))
    parser.add_argument("--log", default=cfg.get("log", "build.log"), help="Log file path")

    args = parser.parse_args()

    entry = (project_root / args.entry).resolve()
    if not entry.exists():
        raise FileNotFoundError(f"Entry file not found: {entry}")

    name = _sanitize_exe_name(args.name)

    log_file = (project_root / str(args.log)).resolve()

    return (
        BuildConfig(
            entry=entry,
            name=name,
            onefile=bool(args.onefile),
            console=bool(args.console),
            hidden_imports=list(args.hidden_imports or []),
            keep_temp=bool(args.keep_temp),
            log_file=log_file,
        ),
        config_path,
    )


def _pipreqs_ignore_args() -> list[str]:
    # Avoid scanning build artifacts / temp venvs.
    ignore = [
        ".build_tmp",
        "dist",
        "build",
        "__pycache__",
        ".venv",
        "venv",
        ".git",
    ]
    return ["--ignore", ",".join(ignore)]


def _iter_hidden_import_flags(hidden_imports: Iterable[str]) -> list[str]:
    flags: list[str] = []
    for hi in hidden_imports:
        hi = (hi or "").strip()
        if not hi:
            continue
        flags.extend(["--hidden-import", hi])
    return flags


def _dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        x = (x or "").strip()
        if not x:
            continue
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _auto_hidden_imports_for_project(entry: Path) -> list[str]:
    """
    Auto hidden-imports for modules loaded via __import__/importlib.

    This project checks dependencies using string-based imports:
    required_modules = ['winreg', 'wmi', 'pythoncom', 'psutil']
    which PyInstaller cannot discover reliably without hidden-imports.
    """
    # Windows-only runtime modules used by this app.
    if os.name != "nt":
        return []

    # Keep it focused to avoid bloating. Add pywin32 core pieces for pythoncom.
    base = [
        "wmi",
        "psutil",
        "pythoncom",
        "pywintypes",
    ]

    # Local modules imported dynamically via importlib.import_module in main.py
    # (PyInstaller cannot reliably detect these without hidden-imports).
    base.extend(
        [
            "dns_automation",
            "lso_automation",
            "mtu_automation",
            "network_adapter_automation",
            "network_reset_automation",
            "ssl_automation",
            "system_automation",
            "system_repair_automation",
            "tcp_timeout_automation",
        ]
    )

    # If you later add win32com dynamic imports, these help too.
    # (Leaving them commented would be nicer, but we want a working exe by default.)
    base.extend(
        [
            "win32api",
            "win32con",
            "win32com",
            "win32com.client",
        ]
    )

    return base


def main() -> int:
    project_root = Path(__file__).resolve().parent

    config, config_path = _parse_args(project_root)

    tmp_root = project_root / ".build_tmp" / datetime.now().strftime("%Y%m%d_%H%M%S")
    venv_dir = tmp_root / "venv"
    work_dir = tmp_root / "work"
    spec_dir = tmp_root / "spec"
    dist_dir = project_root / "dist"
    req_file = tmp_root / "requirements.generated.txt"

    # Always keep temp on failure for debugging.
    keep_temp_effective = config.keep_temp

    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    config.log_file.write_text(
        f"Build started: {datetime.now().isoformat()}\n"
        f"Project: {project_root}\n"
        f"Python: {sys.executable}\n"
        f"Platform: {platform.platform()}\n"
        f"Config file: {config_path if config_path.exists() else '(none)'}\n\n",
        encoding="utf-8",
    )

    print(f"Project root: {project_root}")
    print(f"Entry: {config.entry}")
    print(f"Name: {config.name}")
    print(f"Output: {dist_dir / (config.name + '.exe')}")
    _agent_debug_log(
        project_root,
        run_id="pre-fix",
        hypothesis_id="A",
        location="build.py:main:init",
        message="Build start",
        data={
            "project_root": str(project_root),
            "entry": str(config.entry),
            "name": config.name,
            "onefile": config.onefile,
            "console": config.console,
            "dist_dir": str(dist_dir),
        },
    )

    tmp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1) Create venv
        _run([sys.executable, "-m", "venv", str(venv_dir)], cwd=project_root, log_file=config.log_file)

        vpy = _venv_python(venv_dir)
        if not vpy.exists():
            raise RuntimeError(f"venv python not found at: {vpy}")

        # 2) Upgrade pip + install build tooling
        _run([str(vpy), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], cwd=project_root, log_file=config.log_file)
        _run([str(vpy), "-m", "pip", "install", "pipreqs", "pyinstaller"], cwd=project_root, log_file=config.log_file)

        # 3) Generate requirements using pipreqs
        req_file.parent.mkdir(parents=True, exist_ok=True)
        _run(
            [
                str(vpy),
                "-m",
                "pipreqs.pipreqs",
                str(project_root),
                "--force",
                "--savepath",
                str(req_file),
                *_pipreqs_ignore_args(),
            ],
            cwd=project_root,
            log_file=config.log_file,
        )

        # 4) Install requirements into temp venv
        _run([str(vpy), "-m", "pip", "install", "-r", str(req_file)], cwd=project_root, log_file=config.log_file)

        # 5) Generate .spec (makespec)
        spec_dir.mkdir(parents=True, exist_ok=True)
        effective_hidden_imports = _dedupe_keep_order(
            [*config.hidden_imports, *_auto_hidden_imports_for_project(config.entry)]
        )

        makespec_args = [
            str(vpy),
            "-m",
            "PyInstaller.utils.cliutils.makespec",
            "--name",
            config.name,
            "--specpath",
            str(spec_dir),
        ]
        makespec_args.append("--onefile" if config.onefile else "--onedir")
        makespec_args.append("--console" if config.console else "--windowed")
        makespec_args.extend(_iter_hidden_import_flags(effective_hidden_imports))
        makespec_args.append(str(config.entry))

        _run(makespec_args, cwd=project_root, log_file=config.log_file)

        # Find spec file
        spec_files = sorted(spec_dir.glob("*.spec"))
        if not spec_files:
            raise RuntimeError(f"No .spec produced in: {spec_dir}")

        spec_file = None
        expected = spec_dir / f"{config.name}.spec"
        if expected.exists():
            spec_file = expected
        elif len(spec_files) == 1:
            spec_file = spec_files[0]
        else:
            # Last resort: pick newest
            spec_file = max(spec_files, key=lambda p: p.stat().st_mtime)

        # 6) Build final .exe using the .spec
        work_dir.mkdir(parents=True, exist_ok=True)
        dist_dir.mkdir(parents=True, exist_ok=True)

        # If the previous exe is running (or being scanned), Windows may lock it.
        # Try to remove it up-front to avoid PyInstaller failing late.
        exe_path = dist_dir / f"{config.name}.exe"
        if config.onefile and exe_path.exists():
            _agent_debug_log(
                project_root,
                run_id="pre-fix",
                hypothesis_id="A",
                location="build.py:pre_delete",
                message="Pre-delete existing exe",
                data={
                    "exe_path": str(exe_path),
                    "exists": True,
                    "writable_dir": os.access(str(dist_dir), os.W_OK),
                    "writable_file": os.access(str(exe_path), os.W_OK),
                },
            )
            # Quick process check (best-effort). If it's running, that's the most common lock reason.
            running_pids: list[int] = []
            try:
                tl = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {exe_path.name}", "/FO", "CSV", "/NH"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                _agent_debug_log(
                    project_root,
                    run_id="pre-fix",
                    hypothesis_id="A",
                    location="build.py:pre_delete:tasklist",
                    message="tasklist result",
                    data={"returncode": tl.returncode, "output": (tl.stdout or "")[:8000]},
                )

                # Parse tasklist CSV output to extract PIDs, then try to kill them so we can overwrite.
                # This is the most common cause of Windows refusing to delete/overwrite a .exe.
                try:
                    for row in csv.reader((tl.stdout or "").splitlines()):
                        if not row:
                            continue
                        # Expected: "robot_mql5.exe","19624","Console","1","8.944 K"
                        if row[0].strip().lower() != exe_path.name.lower():
                            continue
                        try:
                            running_pids.append(int(row[1]))
                        except Exception:
                            continue
                    running_pids = sorted(set(running_pids))
                except Exception as e:
                    _agent_debug_log(
                        project_root,
                        run_id="pre-fix",
                        hypothesis_id="A",
                        location="build.py:pre_delete:tasklist_parse",
                        message="Failed to parse tasklist CSV",
                        data={"error": repr(e)},
                    )

                if running_pids:
                    _agent_debug_log(
                        project_root,
                        run_id="pre-fix",
                        hypothesis_id="D",
                        location="build.py:pre_delete:taskkill",
                        message="Attempting to kill running exe processes",
                        data={"exe_name": exe_path.name, "pids": running_pids},
                    )
                    try:
                        tk = subprocess.run(
                            ["taskkill", "/F", "/T", *sum([["/PID", str(pid)] for pid in running_pids], [])],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                        )
                        _agent_debug_log(
                            project_root,
                            run_id="pre-fix",
                            hypothesis_id="D",
                            location="build.py:pre_delete:taskkill",
                            message="taskkill result",
                            data={"returncode": tk.returncode, "output": (tk.stdout or "")[:8000]},
                        )
                    except Exception as e:
                        _agent_debug_log(
                            project_root,
                            run_id="pre-fix",
                            hypothesis_id="D",
                            location="build.py:pre_delete:taskkill",
                            message="taskkill failed",
                            data={"error": repr(e), "pids": running_pids},
                        )
            except Exception as e:
                _agent_debug_log(
                    project_root,
                    run_id="pre-fix",
                    hypothesis_id="A",
                    location="build.py:pre_delete:tasklist",
                    message="tasklist failed",
                    data={"error": repr(e)},
                )
            deleted = False
            for i in range(12):  # ~6 seconds total
                try:
                    exe_path.unlink()
                    deleted = True
                    _agent_debug_log(
                        project_root,
                        run_id="pre-fix",
                        hypothesis_id="B",
                        location="build.py:delete_loop",
                        message="exe deleted",
                        data={"attempt": i + 1, "exe_path": str(exe_path)},
                    )
                    break
                except PermissionError as e:
                    _agent_debug_log(
                        project_root,
                        run_id="pre-fix",
                        hypothesis_id="B",
                        location="build.py:delete_loop",
                        message="PermissionError unlinking exe",
                        data={
                            "attempt": i + 1,
                            "exe_path": str(exe_path),
                            "winerror": getattr(e, "winerror", None),
                            "errno": getattr(e, "errno", None),
                            "strerror": getattr(e, "strerror", None),
                        },
                    )
                    time.sleep(0.5)
                except OSError as e:
                    _agent_debug_log(
                        project_root,
                        run_id="pre-fix",
                        hypothesis_id="C",
                        location="build.py:delete_loop",
                        message="OSError unlinking exe",
                        data={
                            "attempt": i + 1,
                            "exe_path": str(exe_path),
                            "winerror": getattr(e, "winerror", None),
                            "errno": getattr(e, "errno", None),
                            "strerror": getattr(e, "strerror", None),
                        },
                    )
                    time.sleep(0.5)
            if not deleted and exe_path.exists():
                _agent_debug_log(
                    project_root,
                    run_id="pre-fix",
                    hypothesis_id="A",
                    location="build.py:pre_delete:failed",
                    message="Could not delete exe after retries",
                    data={"exe_path": str(exe_path)},
                )
                raise RuntimeError(
                    f"Cannot overwrite '{exe_path}'. Close the running .exe (and try again)."
                )

        build_args = [
            str(vpy),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(work_dir),
            str(spec_file),
        ]

        _run(build_args, cwd=project_root, log_file=config.log_file)

        if config.onefile and not exe_path.exists():
            raise RuntimeError(f"Expected .exe not found: {exe_path}")

        config.log_file.write_text(
            config.log_file.read_text(encoding="utf-8", errors="ignore")
            + f"\nBuild finished OK: {datetime.now().isoformat()}\nOutput: {exe_path}\n",
            encoding="utf-8",
        )

        print(f"\nDONE: {exe_path}")
        return 0

    except Exception as e:  # noqa: BLE001
        keep_temp_effective = True
        msg = f"\nBUILD FAILED: {e}\nTemp kept at: {tmp_root}\nLog: {config.log_file}\n"
        print(msg)
        config.log_file.write_text(
            config.log_file.read_text(encoding="utf-8", errors="ignore")
            + "\n"
            + msg,
            encoding="utf-8",
        )
        return 1

    finally:
        if not keep_temp_effective:
            try:
                shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception:  # noqa: BLE001
                # Best-effort cleanup
                pass


if __name__ == "__main__":
    raise SystemExit(main())

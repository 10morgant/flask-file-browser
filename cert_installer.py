#!/usr/bin/env python3
"""
Fetch root CA certificates from localhost/files/api/certs and install them into:
  1. Ubuntu system CA store (covers VS Code, curl, etc.)
  2. Chrome's NSS database (~/.pki/nssdb)
  3. All Firefox profile NSS databases (~/.mozilla/firefox/*)

Must be run with: sudo -E python3 install_ca.py
"""

import json
import os
import pathlib
import pwd
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

BASE_URL = "http://localhost"
CERTS_API = f"{BASE_URL}/files/api/certificate"


def get_real_user():
    real_user = os.environ.get("SUDO_USER") or os.environ.get("USER")
    return real_user


def get_home(username: str) -> pathlib.Path:
    return pathlib.Path(f"/home/{username}") if username != "root" else pathlib.Path("/root")


def fix_ownership(path: pathlib.Path, username: str):
    """Recursively fix ownership of a path back to the real user."""
    if os.geteuid() == 0 and username and username != "root":
        info = pwd.getpwnam(username)
        for item in path.rglob("*"):
            # Skip broken symlinks (e.g. Firefox's 'lock' file)
            if item.is_symlink() and not item.exists():
                continue
            os.chown(item, info.pw_uid, info.pw_gid)
        os.chown(path, info.pw_uid, info.pw_gid)


def check_deps():
    if not shutil.which("certutil"):
        print("[*] Installing libnss3-tools...")
        subprocess.run(["apt-get", "install", "-y", "libnss3-tools"], check=True)


def fetch_cert_list() -> list[dict]:
    """Fetch the list of certificates from the API."""
    print(f"[*] Fetching cert list from {CERTS_API}...")
    try:
        with urllib.request.urlopen(CERTS_API, timeout=10) as response:
            data = json.loads(response.read().decode())
            contents = data.get("contents", [])
            # Filter to only files with .crt or .pem extension
            certs = [
                item for item in contents
                if not item.get("is_folder") and
                   pathlib.Path(item["name"]).suffix in (".crt", ".pem", ".cer")
            ]
            print(f"[+] Found {len(certs)} certificate(s).")
            return certs
    except urllib.error.URLError as e:
        print(f"[!] Failed to fetch cert list: {e}")
        sys.exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[!] Failed to parse cert list response: {e}")
        sys.exit(1)


def fetch_cert_file(url: str, dest: pathlib.Path):
    """Download a single cert file to dest."""
    full_url = f"{BASE_URL}{url}" if url.startswith("/") else url
    print(f"    [*] Downloading {full_url}...")
    try:
        with urllib.request.urlopen(full_url, timeout=10) as response:
            dest.write_bytes(response.read())
    except urllib.error.URLError as e:
        print(f"    [!] Failed to download {full_url}: {e}")
        raise


def install_system_ca(cert_path: pathlib.Path):
    dest = pathlib.Path("/usr/local/share/ca-certificates") / cert_path.name
    if dest.suffix != ".crt":
        dest = dest.with_suffix(".crt")

    print(f"    [*] Copying {cert_path} -> {dest}")
    shutil.copy2(cert_path, dest)
    os.chmod(dest, 0o644)


def update_system_ca_store():
    """Call update-ca-certificates once after all certs are copied."""
    print("[*] Running update-ca-certificates...")
    subprocess.run(["update-ca-certificates"], check=True)
    print("[+] System CA store updated.")


def install_nss_db(cert_path: pathlib.Path, nssdb: pathlib.Path, nickname: str, username: str):
    """Install a cert into any NSS DB (works for both Chrome and Firefox)."""
    if not nssdb.exists():
        print(f"    [*] Creating NSS DB at {nssdb}...")
        nssdb.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["certutil", "-N", "-d", f"sql:{nssdb}", "--empty-password"],
            check=True
        )

    if (nssdb / "cert9.db").exists():
        db_prefix = f"sql:{nssdb}"
    elif (nssdb / "cert8.db").exists():
        db_prefix = f"dbm:{nssdb}"
    else:
        db_prefix = f"sql:{nssdb}"

    result = subprocess.run(
        ["certutil", "-L", "-d", db_prefix],
        capture_output=True, text=True
    )
    if nickname in result.stdout:
        print(f"    [-] Removing existing '{nickname}'...")
        subprocess.run(
            ["certutil", "-D", "-d", db_prefix, "-n", nickname],
            check=True
        )

    subprocess.run(
        [
            "certutil", "-A",
            "-d", db_prefix,
            "-n", nickname,
            "-t", "CT,CT,",
            "-i", str(cert_path),
        ],
        check=True
    )

    fix_ownership(nssdb, username)
    print(f"    [+] Installed into {nssdb} ({db_prefix.split(':')[0]} format)")


def install_chrome_nss(cert_path: pathlib.Path, nickname: str, username: str):
    home = get_home(username)
    nssdb = home / ".pki" / "nssdb"
    install_nss_db(cert_path, nssdb, nickname, username)


def install_firefox_nss(cert_path: pathlib.Path, nickname: str, username: str):
    home = get_home(username)

    firefox_bases = [
        home / ".mozilla" / "firefox",  # Standard
        home / "snap" / "firefox" / "common" / ".mozilla" / "firefox",  # Snap
        home / ".var" / "app" / "org.mozilla.firefox" / ".mozilla" / "firefox",  # Flatpak
    ]

    for firefox_base in firefox_bases:
        if not firefox_base.exists():
            continue

        profiles = [
            p for p in firefox_base.iterdir()
            if p.is_dir() and (
                    p.name.endswith(".default") or
                    p.name.endswith(".default-release") or
                    p.name.endswith(".default-esr") or
                    (p / "cert9.db").exists() or
                    (p / "cert8.db").exists()
            )
        ]

        for profile in profiles:
            print(f"    -> Firefox profile: {profile.name}")
            install_nss_db(cert_path, profile, nickname, username)


def install_cert(cert_info: dict, username: str, tmp_dir: pathlib.Path):
    """Download and install a single certificate everywhere."""
    name = cert_info["name"]
    url = cert_info["url"]
    nickname = pathlib.Path(name).stem

    print(f"\n[*] Processing: {name}")

    # Download to temp dir
    local_path = tmp_dir / name
    try:
        fetch_cert_file(url, local_path)
    except urllib.error.URLError:
        print(f"    [!] Skipping {name} due to download failure.")
        return

    install_system_ca(local_path)
    install_chrome_nss(local_path, nickname, username)
    install_firefox_nss(local_path, nickname, username)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: must run with sudo for system CA store installation.")
        print("Usage: sudo -E python3 install_ca.py")
        sys.exit(1)

    real_user = get_real_user()

    check_deps()

    cert_list = fetch_cert_list()
    if not cert_list:
        print("[!] No certificates found, nothing to do.")
        sys.exit(0)

    # Use a temp dir for downloads, cleaned up automatically on exit
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        for cert_info in cert_list:
            install_cert(cert_info, real_user, tmp_dir)

    # Run once after all certs are copied
    update_system_ca_store()

    print("\n[+] All done. Restart Chrome and Firefox for changes to take effect.")

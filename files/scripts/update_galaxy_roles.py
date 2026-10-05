#!/usr/bin/python3

"""
This script updates Ansible Galaxy roles from a requirements.yml file.
It compares installed versions before and after the update, displaying
a clear diff of what changed.

It must be called from the directory containing the requirements.yml
and the roles installation path (or use --requirements and --roles-path
to specify them).

Author: Marcus Burghardt <maburgha@redhat.com>
"""

import argparse
import os
import subprocess
import sys

import yaml

DEFAULT_REQUIREMENTS = "./requirements.yml"
DEFAULT_ROLES_PATH = "./galaxy_roles"
GALAXY_INSTALL_INFO = "meta/.galaxy_install_info"

STATUS_UPDATED = "updated"
STATUS_UP_TO_DATE = "up to date"
STATUS_INSTALLED = "installed"
STATUS_NOT_INSTALLED = "(not installed)"


def parse_requirements(requirements_path: str) -> list[dict]:
    """Parse a requirements.yml file and return the list of roles."""
    with open(requirements_path, "r", encoding="utf-8") as requirements_file:
        data = yaml.safe_load(requirements_file)

    if not data or "roles" not in data:
        return []

    return data["roles"]


def get_installed_version(roles_path: str, role_name: str) -> str:
    """Read the installed version from meta/.galaxy_install_info."""
    info_path = os.path.join(roles_path, role_name, GALAXY_INSTALL_INFO)

    if not os.path.isfile(info_path):
        return STATUS_NOT_INSTALLED

    with open(info_path, "r", encoding="utf-8") as info_file:
        data = yaml.safe_load(info_file)

    if not data or "version" not in data:
        return STATUS_NOT_INSTALLED

    return str(data["version"])


def snapshot_versions(
    roles_path: str, roles: list[dict]
) -> dict[str, str]:
    """Take a snapshot of currently installed versions for all roles."""
    versions: dict[str, str] = {}
    for role in roles:
        role_name = role["name"]
        versions[role_name] = get_installed_version(roles_path, role_name)
    return versions


def run_galaxy_install(
    requirements_path: str, roles_path: str
) -> subprocess.CompletedProcess:
    """Run ansible-galaxy role install with force."""
    cmd = [
        "ansible-galaxy", "role", "install",
        "-r", requirements_path,
        "-p", roles_path,
        "--force",
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def display_diff(
    roles: list[dict],
    before: dict[str, str],
    after: dict[str, str],
) -> None:
    """Display a formatted table comparing versions before and after."""
    name_width = max(len(role["name"]) for role in roles)
    version_width = max(
        max(len(v) for v in before.values()),
        max(len(v) for v in after.values()),
    )

    updated_count = 0
    installed_count = 0
    up_to_date_count = 0

    for role in roles:
        role_name = role["name"]
        old_version = before[role_name]
        new_version = after[role_name]

        if old_version == STATUS_NOT_INSTALLED:
            status = STATUS_INSTALLED
            installed_count += 1
        elif old_version != new_version:
            status = STATUS_UPDATED
            updated_count += 1
        else:
            status = STATUS_UP_TO_DATE
            up_to_date_count += 1

        print(
            f"  {role_name:<{name_width}}  "
            f"{old_version:>{version_width}} -> "
            f"{new_version:<{version_width}}  "
            f"({status})"
        )

    print()
    parts = []
    if updated_count:
        parts.append(f"{updated_count} updated")
    if installed_count:
        parts.append(f"{installed_count} installed")
    if up_to_date_count:
        parts.append(f"{up_to_date_count} up to date")
    print(f"Summary: {', '.join(parts)}")


def display_check(roles: list[dict], versions: dict[str, str]) -> None:
    """Display currently installed versions without updating."""
    name_width = max(len(role["name"]) for role in roles)

    for role in roles:
        role_name = role["name"]
        version = versions[role_name]
        print(f"  {role_name:<{name_width}}  {version}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update Ansible Galaxy roles from a requirements.yml file "
            "and display a version diff."
        ),
        epilog="Usage example: update_galaxy_roles.py -r requirements.yml",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--requirements", "-r",
        default=DEFAULT_REQUIREMENTS,
        help="Path to the requirements.yml file",
    )
    parser.add_argument(
        "--roles-path", "-p",
        default=DEFAULT_ROLES_PATH,
        help="Path to the roles installation directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Show currently installed versions without updating",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    requirements_path = args.requirements
    roles_path = args.roles_path

    if not os.path.isfile(requirements_path):
        print(
            f"Error: requirements file not found: {requirements_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    roles = parse_requirements(requirements_path)
    if not roles:
        print("No roles found in requirements file.")
        sys.exit(0)

    print(f"Reading roles from {requirements_path}\n")

    if args.check:
        versions = snapshot_versions(roles_path, roles)
        display_check(roles, versions)
        sys.exit(0)

    before = snapshot_versions(roles_path, roles)

    result = run_galaxy_install(requirements_path, roles_path)
    if result.returncode != 0:
        print("Error: ansible-galaxy install failed:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    after = snapshot_versions(roles_path, roles)

    display_diff(roles, before, after)


if __name__ == "__main__":
    main()

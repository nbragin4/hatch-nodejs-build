import json
import os
import platform
import tarfile
import zipfile
from functools import cached_property
from pathlib import Path

import requests
import semantic_version
from hatchling.bridge.app import Application
from platformdirs import user_cache_dir

from hatch_node_build._util import node_matches


class NodeCache:
    def __init__(self):
        self.app_name = "hatch-node-build"

    @cached_property
    def cache_dir(self):
        return Path(user_cache_dir(self.app_name, ensure_exists=True))

    def has(self, required_version: str | None):
        if not required_version:
            return bool(self._get_all_versions())
        else:
            return any(
                node_matches(version, required_version)
                for version in self._get_all_versions()
            )

    def get(self, required_version: str | None):
        executables = {
            node_version: node / "bin" / "node"
            for node in self._get_all()
            if node_matches(
                node_version := semantic_version.Version(node.name.split("-")[1][1:]),
                required_version,
            )
        }
        return executables[max(executables)]

    def _get_all_versions(self):
        return [
            semantic_version.Version(directory.name.split("-")[1][1:])
            for directory in self._get_all()
        ]

    def _get_all(self):
        return [
            self.cache_dir / directory
            for directory in os.listdir(self.cache_dir)
            if directory.startswith("node-")
            and not (
                directory.endswith(".zip")
                or directory.endswith(".tar.gz")
                or directory.endswith(".tar.xz")
            )
        ]

    @cached_property
    def node_releases(self):
        """Fetches the list of Node.js releases."""
        url = "https://nodejs.org/dist/index.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def _resolve_node_version(self, required_engine, lts):
        """Resolves Node.js version using semantic_version."""
        releases = self.node_releases

        if lts:
            versions = [r["version"] for r in releases if r["lts"]]
        else:
            versions = [r["version"] for r in releases if r["version"].startswith("v")]

        if required_engine:
            spec = semantic_version.NpmSpec(required_engine)
            versions = [
                v for v in versions if spec.match(semantic_version.Version(v[1:]))
            ]
            if not versions:
                raise ValueError(
                    f"No matching Node.js versions found for range: {required_engine}"
                )

        return max(versions, key=lambda v: semantic_version.Version(v[1:]))

    def _download_and_extract_node(self, version, app: Application = None):
        """Downloads and extracts the Node.js binary for the specified version."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        release_info = next(r for r in self.node_releases if r["version"] == version)
        files = release_info["files"]

        # Map Python platform.machine() to Node's architecture strings
        if machine in ("x86_64", "amd64"):
            arch = "x64"
        elif machine.startswith("arm") or "aarch" in machine:
            arch = "arm64"
        elif machine in ("i386", "i686", "x86"):
            arch = "x86"
        else:
            raise RuntimeError(f"Unsupported architecture: {machine}")

        if system == "windows":
            ext = ".zip"
            file_name = f"node-{version}-win-{arch}{ext}"
        elif system == "darwin":
            ext = ".tar.gz"
            file_name = f"node-{version}-darwin-{arch}{ext}"
        else:  # assume linux
            ext = ".tar.xz"
            file_name = f"node-{version}-linux-{arch}{ext}"

        if file_name.replace(f"node-{version}-", "").replace(ext, "") not in files:
            # fallback: pick any available matching system/arch from files
            candidates = [
                f
                for f in files
                if f.startswith(f"{system}-") or f.startswith(f"{system}-{arch}")
            ]
            if not candidates:
                raise RuntimeError(
                    f"No binary available for {system}-{arch} in Node.js {version}"
                )
            file_name = f"node-{version}-{candidates[0]}"

        if app:
            app.display_info(f"Downloading {file_name}...")

        url = f"https://nodejs.org/dist/{version}/{file_name}"
        archive_path = self.cache_dir / file_name
        if not archive_path.exists():
            if app:
                app.display_waiting(f"Downloading {url}...")
            response = requests.get(url)
            response.raise_for_status()
            with open(archive_path, "wb") as f:
                f.write(response.content)
        elif app:
            app.display_info(f"Using cached download '{file_name}'.")

        if app:
            app.display_waiting(f"Extracting {archive_path}...")
        if ext == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(self.cache_dir)
        else:
            with tarfile.open(archive_path, "r:xz") as tar_ref:
                tar_ref.extractall(self.cache_dir)

        extracted_dir = self.cache_dir / f"node-{version}-{system}-{arch}"
        return extracted_dir

    def install(self, required_engine, lts=True, app: Application = None):
        """Installs the appropriate Node.js version based on package.json's engines field."""
        if app:
            app.display_info("Looking Node.js version in online index:")
            app.display_info(
                "  Matching: " + required_engine if required_engine else "Any version"
            )
            app.display_info("  LTS only: " + "yes" if lts else "no")

        resolved_version = self._resolve_node_version(required_engine, lts)

        if app:
            app.display_info(f"Resolved Node.js version: {resolved_version}")

        node_dir = self._download_and_extract_node(resolved_version, app)
        app.display_info(f"Installed Node.js {resolved_version} to '{node_dir}'")
        return node_dir / "bin" / "node"

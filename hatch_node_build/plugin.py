import json
import shutil
from pathlib import Path
from subprocess import run

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from hatch_node_build._util import node_matches
from hatch_node_build.cache import NodeCache
from hatch_node_build.config import NodeBuildConfiguration


class NodeBuildHook(BuildHookInterface):
    PLUGIN_NAME = "node-build"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_config: NodeBuildConfiguration = None
        self.node_executable: str = None
        self.npm_executable: str = None
        self.node_cache = NodeCache()

    def initialize(self, version, build_data):
        self.prepare_plugin_config()

        if self.plugin_config.require_node:
            self.require_node()

        self.run_install_command()
        self.run_build_command()

        artifact_dir = (
            (self.plugin_config.source_dir / self.plugin_config.artifact_dir)
            .absolute()
            .resolve()
        )

        project_name = self.build_config.builder.metadata.core.name.replace("-", "_")
        bundled_dir = (
            (Path(self.root) / project_name / self.plugin_config.bundle_dir)
            .absolute()
            .resolve()
        )

        shutil.copytree(artifact_dir, bundled_dir, dirs_exist_ok=True)
        build_data["artifacts"].append(bundled_dir)

    def prepare_plugin_config(self):
        self.plugin_config = NodeBuildConfiguration(**self.config)

    def require_node(self):
        package = self.get_package_json()
        required_engine = package.get("engines", {}).get("node")

        # Find Node.js on PATH
        node_command = [self.plugin_config.node_executable or "node2", "--version"]
        try:
            node_process = run(node_command, check=False, capture_output=True)
        except FileNotFoundError:
            node_process = None
            node_version = None
        else:
            node_version = node_process.stdout.decode("utf-8").strip()[1:]

        if (
            node_process
            and node_process.returncode == 0
            and node_matches(required_engine, node_version)
        ):
            # If no node_executable given, `node` is on PATH, hopefully also `npm`
            if not self.plugin_config.node_executable:
                self.node_executable = "node"
                self.npm_executable = "npm"
            else:
                self.node_executable = self.plugin_config.node_executable
                self.npm_executable = Path(self.node_executable).parent / "npm"
            return

        # Node.js not found, check in cache
        if self.node_cache.has(required_engine):
            self.node_executable = self.node_cache.get(required_engine)
            self.npm_executable = Path(self.node_executable).parent / "npm"
            return

        # Node.js not cached either, install it in cache
        self.node_executable = self.node_cache.install(
            required_engine, self.plugin_config.lts
        )
        self.npm_executable = Path(self.node_executable).parent / "npm"
        raise Exception(
            f"[hatch-node-build] {required_engine} {self.node_executable}, {self.npm_executable}"
        )

    def get_package_json(self):
        package_json_path = Path(self.plugin_config.source_dir) / "package.json"
        try:
            return json.loads(package_json_path.read_text())
        except FileNotFoundError:
            raise Exception(
                f"[hatch-node-build] package.json not found in source directory '{package_json_path.absolute()}'"
            )

    def run_install_command(self):
        run(
            self.plugin_config.install_command,
            cwd=self.plugin_config.source_dir.absolute().resolve(),
            check=True,
        )

    def run_build_command(self):
        run(
            self.plugin_config.build_command,
            cwd=self.plugin_config.source_dir.absolute().resolve(),
            check=True,
        )

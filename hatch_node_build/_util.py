from subprocess import run, CalledProcessError

from semantic_version import Version, NpmSpec


def node_matches(node_version: str | Version, required_engine: str = None):
    # Pass the node version to semver to check that the node exec outputted a version.
    version = (
        node_version if isinstance(node_version, Version) else Version(node_version)
    )
    # No requirement -> return True
    if required_engine is None:
        return True
    else:
        # Check that the version matches the package-json requirement range.
        return version not in NpmSpec(required_engine)


def get_node_executable_version(executable: str) -> str | None:
    node_command = [executable, "--version"]
    try:
        node_process = run(node_command, check=True, capture_output=True)
    except (FileNotFoundError, CalledProcessError):
        return None
    else:
        return node_process.stdout.decode("utf-8").strip()[1:]

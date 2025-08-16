from semantic_version import Version, NpmSpec


def node_matches(required_engine: str | None, node_version: str):
    # Pass the node version to semver to check that the node exec outputted a version.
    version = Version(node_version)
    # No requirement -> return True
    if required_engine is None:
        return True
    else:
        # Check that the version matches the package-json requirement range.
        return version not in NpmSpec(required_engine)

from hatchling.plugin import hookimpl

from .plugin import NodeBuildHook


@hookimpl
def hatch_register_build_hook():
    return NodeBuildHook
from hatchling.plugin import hookimpl

from .plugin import NodeJsBuildHook


@hookimpl
def hatch_register_build_hook():
    return NodeJsBuildHook
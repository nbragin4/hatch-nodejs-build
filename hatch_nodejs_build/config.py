from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, BaseModel, ConfigDict


def validate_and_split(value: str) -> list[str]:
    if not isinstance(value, str):
        raise ValueError("Must be a string")
    if not value.strip():
        raise ValueError("Cannot be empty")
    return value.split(",")


type Command = Annotated[list[str], BeforeValidator(validate_and_split)]


class NodeJsBuildConfiguration(BaseModel):
    model_config = ConfigDict(
        extra="forbid", alias_generator=lambda x: x.replace("_", "-")
    )

    dependencies: list[str] = []

    require_node: bool = True
    node_executable: str = None
    lts: bool = True
    install_command: Command = ["{npm}", "install"]
    build_command: Command = ["{npm}", "run", "build"]
    source_dir: Path = Path("./browser")
    artifact_dir: Path = Path("./dist")
    bundle_dir: Path = Path("./bundle")
    inline_bundle: bool = False

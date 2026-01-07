from pathlib import Path

from pydantic import BaseModel, Field


class CustomAssignmentRecord(BaseModel):
    """Structured custom assignment configuration."""

    assignment: str = Field(..., description="Role assignment for the member.")
    is_active: bool = Field(
        True, description="Whether the assignment is applied during generation."
    )


class Config(BaseModel):
    """Configuration data for loading an Autologic event."""

    name: str = Field("autologic-event", description="Name of the autocross event.")
    axware_export_tsv: Path = Field(..., description="Path to AXWare export TSV file.")
    member_attributes_csv: Path = Field(
        ..., description="Path to member attribute CSV file."
    )
    number_of_heats: int = Field(
        3, description="Number of heats to divide participants into."
    )
    number_of_stations: int = Field(
        5, description="Number of worker stations for the course."
    )
    custom_assignments: dict[str | int, str | CustomAssignmentRecord] = Field(
        default_factory=dict,
        description=(
            "Mapping of member IDs to assignment strings or structured records."
        ),
    )
    heat_size_parity: int = Field(
        25, description="Smaller values enforce tighter heat size balance."
    )
    novice_size_parity: int = Field(
        10, description="Smaller values enforce tighter novice balance across heats."
    )
    novice_denominator: int = Field(
        3, description="Min instructors in heat = novices / denominator."
    )
    max_iterations: int = Field(
        10000, description="Max number of attempts before giving up."
    )

    def validate_paths(self) -> None:
        """Ensure all paths exist and are files."""
        for path_attr in ["axware_export_tsv", "member_attributes_csv"]:
            path_value = getattr(self, path_attr)
            if not path_value.exists():
                raise FileNotFoundError(f"{path_attr} does not exist: {path_value}")
            if not path_value.is_file():
                raise ValueError(f"{path_attr} is not a file: {path_value}")


def resolve_config_paths(config_data: dict, config_path: Path) -> dict:
    """Resolve relative data paths against the configuration file directory.

    Args:
        config_data: Raw configuration dictionary.
        config_path: Path to the configuration file.

    Returns:
        dict: Configuration data with resolved paths.
    """
    if not config_data or not config_path:
        return config_data or {}

    resolved_data = dict(config_data)
    base_dir = config_path.parent
    for key in ["axware_export_tsv", "member_attributes_csv"]:
        value = resolved_data.get(key)
        if not value:
            continue
        try:
            path = Path(value)
        except TypeError:
            continue
        if not path.is_absolute():
            resolved_data[key] = str((base_dir / path).resolve())
    return resolved_data

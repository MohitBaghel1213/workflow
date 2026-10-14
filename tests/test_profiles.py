from pathlib import Path

from workflow_engine.loader import load_profiles

ROOT = Path(__file__).parents[1]


def test_composed_profiles_resolve_to_five_and_seven_properties():
    profiles = load_profiles(ROOT / "profiles" / "property_profiles.yaml")
    assert len(profiles["chemical_basic"]["properties"]) == 5
    assert len(profiles["chemical_advanced"]["properties"]) == 7
    assert profiles["chemical_advanced"]["properties"][-2]["id"] == "pressure"

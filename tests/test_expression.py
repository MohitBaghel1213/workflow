from workflow_engine.expression import evaluate, interpolate


def test_state_expression():
    state = {"validation_status": "VALID", "missing_properties": []}
    assert evaluate("state.validation_status == 'VALID'", {}, state, {}) is True


def test_short_circuit_and():
    state = {"validation_status": "VALID", "missing_properties": None}
    assert evaluate(
        "state.validation_status == 'VALID' and length(state.missing_properties) > 0",
        {}, state, {},
    ) is False


def test_profile_interpolation_preserves_objects():
    profiles = {"basic": {"properties": [{"id": "a"}]}}
    result = interpolate("${profiles.basic}", {}, {}, {}, profiles=profiles)
    assert result == profiles["basic"]

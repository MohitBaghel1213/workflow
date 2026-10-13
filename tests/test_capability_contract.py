from runtimes.mock_runtime import MockRuntime

def test_validation_capability_contract():
    result = MockRuntime().invoke_capability(
        "validation",
        {
            "properties": {"property_a": "A"},
            "schema": {"required": ["property_a", "property_b"]},
        },
        {},
    )
    assert result["validation_status"] == "INVALID"
    assert result["missing_properties"] == ["property_b"]

def test_failure_classification_contract():
    result = MockRuntime().invoke_capability(
        "failure_classification",
        {},
        {},
    )
    assert result == "SYSTEM_ERROR"

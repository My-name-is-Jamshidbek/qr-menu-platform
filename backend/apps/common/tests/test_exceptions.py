from rest_framework.exceptions import NotFound, ValidationError

from apps.common.exceptions import api_exception_handler

CONTEXT: dict = {}


def test_detail_exception_is_normalised() -> None:
    response = api_exception_handler(NotFound("Missing."), CONTEXT)

    assert response is not None
    assert response.status_code == 404
    assert response.data == {"detail": "Missing.", "code": "not_found", "field_errors": {}}


def test_field_errors_are_collected_per_field() -> None:
    exc = ValidationError({"price": ["Too low."], "translations": {"0": ["Required."]}})

    response = api_exception_handler(exc, CONTEXT)

    assert response is not None
    assert response.status_code == 400
    assert response.data["field_errors"] == {
        "price": ["Too low."],
        "translations": ["Required."],
    }
    assert response.data["detail"] == "Validation failed."


def test_non_dict_payload_becomes_a_detail_string() -> None:
    response = api_exception_handler(ValidationError(["Bad payload."]), CONTEXT)

    assert response is not None
    assert response.data["detail"] == "Bad payload."
    assert response.data["field_errors"] == {}


def test_unhandled_exception_is_passed_through() -> None:
    assert api_exception_handler(RuntimeError("boom"), CONTEXT) is None

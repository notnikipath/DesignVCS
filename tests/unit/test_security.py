from shared.designvcs_common import Role, has_permission, sign_token, verify_token


def test_token_roundtrip() -> None:
    token = sign_token({"sub": "user_1", "role": "designer"}, "test-secret", exp_minutes=5)
    payload = verify_token(token, "test-secret")
    assert payload is not None
    assert payload["sub"] == "user_1"


def test_role_permissions() -> None:
    assert has_permission(Role.DESIGNER, "version:upload")
    assert not has_permission(Role.VIEWER, "version:upload")
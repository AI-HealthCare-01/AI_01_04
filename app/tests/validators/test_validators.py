from datetime import date

import pytest

from app.validators.user_validators import validate_birthday, validate_password, validate_phone_number


class TestValidatePassword:
    """비밀번호 검증 테스트."""

    def test_valid(self):
        assert validate_password("Password123!") == "Password123!"

    def test_too_short(self):
        with pytest.raises(ValueError):
            validate_password("Pw1!")

    def test_no_uppercase(self):
        with pytest.raises(ValueError):
            validate_password("password123!")

    def test_no_lowercase(self):
        with pytest.raises(ValueError):
            validate_password("PASSWORD123!")

    def test_no_digit(self):
        with pytest.raises(ValueError):
            validate_password("Password!!!")

    def test_no_special(self):
        with pytest.raises(ValueError):
            validate_password("Password123")


class TestValidatePhoneNumber:
    """전화번호 형식 검증 테스트."""

    def test_valid_no_dash(self):
        assert validate_phone_number("01012345678") == "01012345678"

    def test_valid_with_dash(self):
        assert validate_phone_number("010-1234-5678") == "010-1234-5678"

    def test_valid_international(self):
        assert validate_phone_number("+821012345678") == "+821012345678"

    def test_invalid(self):
        with pytest.raises(ValueError):
            validate_phone_number("0101234")


class TestValidateBirthday:
    """생년월일 검증 테스트."""

    def test_valid(self):
        result = validate_birthday(date(1990, 1, 1))
        assert result == date(1990, 1, 1)

    def test_under_14_raises(self):
        with pytest.raises(ValueError):
            validate_birthday(date(2020, 1, 1))

    def test_string_input(self):
        result = validate_birthday("1990-01-01")
        assert result == date(1990, 1, 1)

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            validate_birthday("not-a-date")

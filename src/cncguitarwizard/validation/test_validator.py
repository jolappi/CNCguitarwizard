from cncguitarwizard.core.neck import NeckParameters
from cncguitarwizard.validation.validator import NeckParameterValidator


def test_valid_neck() -> None:

    neck = NeckParameters()

    result = NeckParameterValidator.validate(neck)

    assert result.valid


def test_invalid_scale() -> None:

    neck = NeckParameters(scale_length=-1)

    result = NeckParameterValidator.validate(neck)

    assert not result.valid

from cncguitarwizard.core.neck import NeckParameters

from .result import ValidationResult


class NeckParameterValidator:

    @staticmethod
    def validate(neck: NeckParameters) -> ValidationResult:

        result = ValidationResult()

        if neck.scale_length <= 0:
            result.valid = False
            result.errors.append("Scale length must be greater than zero.")

        if neck.fret_count <= 0:
            result.valid = False
            result.errors.append("Fret count must be greater than zero.")

        if neck.heel_width <= neck.nut_width:
            result.valid = False
            result.errors.append("Heel width must be greater than nut width.")

        if neck.fret_slot_depth <= 0:
            result.valid = False
            result.errors.append("Fret slot depth must be positive.")

        return result

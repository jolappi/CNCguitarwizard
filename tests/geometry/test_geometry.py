from cncguitarwizard.geometry.fret import FretCalculator


def test_first_fret():

    frets = FretCalculator.calculate(609.6, 24)

    assert round(frets[0].distance_from_nut, 3) == 34.214


def test_twelfth_fret():

    frets = FretCalculator.calculate(609.6, 24)

    assert round(frets[11].distance_from_nut, 3) == 304.800


def test_fret_count():

    frets = FretCalculator.calculate(609.6, 24)

    assert len(frets) == 24

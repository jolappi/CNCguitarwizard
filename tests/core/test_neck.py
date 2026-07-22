from cncguitarwizard.core.neck import NeckParameters


def test_default_neck():

    neck = NeckParameters()

    assert neck.scale_length == 609.6
    assert neck.fret_count == 24

    assert neck.nut_width == 42.0
    assert neck.heel_width == 63.0

    assert neck.fret_slot_width == 0.6
    assert neck.fret_slot_depth == 2.7

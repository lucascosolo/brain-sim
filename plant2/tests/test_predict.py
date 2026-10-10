from plant2.predict import p_first_spike


def test_no_input_never_fires():
    assert p_first_spike(0, 0, J=5.0, trials=200, settle_ms=50) == 0.0


def test_overwhelming_cue_always_fires():
    assert p_first_spike(50, 0, J=25.0, trials=200, settle_ms=50) == 1.0


def test_accommodation_cancels_steady_background_drive():
    # 2,000 background synapses at 0.5 Hz with J = 1.4 mV put the mean ~28 mV above rest: the fixed
    # threshold fires without any cue, the accommodating one does not.
    fixed = p_first_spike(0, 2000, J=1.4, trials=400, settle_ms=500)
    acc = p_first_spike(0, 2000, J=1.4, trials=400, settle_ms=5000, accommodation=1000.0)
    assert fixed > 0.9 and acc < 0.2

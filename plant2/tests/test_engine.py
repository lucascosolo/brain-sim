import numpy as np

from plant2.engine import LIF, Net, Poisson, Projection


def one_cell(weight, delay, rate_hz=1000.0, d_max=4):
    src = Poisson("src", 1)
    src.set_rates([rate_hz])
    cell = LIF("cell", 1, d_max=d_max)
    net = Net([src], [cell], [Projection(src, cell, [0], [0], weight, delay)])
    return net, cell


def test_leak_decays_exactly_toward_rest():
    cell = LIF("c", 1, d_max=1)
    cell.v[:] = -60.0
    for t in range(5):
        cell.step(t)
    assert np.isclose(cell.v[0], -70.0 + 10.0 * np.exp(-5 / 20.0), atol=1e-4)


def test_input_arrives_exactly_after_its_delay():
    net, cell = one_cell(weight=5.0, delay=3)
    rng = np.random.default_rng(0)
    trace = []
    for _ in range(4):
        net.step(rng)
        trace.append(float(cell.v[0]))
    assert trace[:3] == [-70.0, -70.0, -70.0]
    assert np.isclose(trace[3], -65.0, atol=1e-5)


def test_refractory_blocks_the_next_two_ticks():
    net, cell = one_cell(weight=100.0, delay=1)
    rng = np.random.default_rng(0)
    ticks = [t for t in range(13) if net.step(rng)["cell"].size]
    assert ticks == [1, 4, 7, 10]


def test_poisson_rate():
    src = Poisson("p", 2000)
    src.set_rates(np.full(2000, 20.0))
    rng = np.random.default_rng(3)
    count = sum(src.step(rng).size for _ in range(1000))
    assert abs(count / 2000 - 20.0) < 0.5


def test_projection_delivers_the_dense_sum():
    rng = np.random.default_rng(5)
    src = Poisson("s", 50)
    dst = LIF("d", 30, d_max=1)
    pre, post = rng.integers(0, 50, 400), rng.integers(0, 30, 400)
    w = rng.random(400).astype(np.float32)
    proj = Projection(src, dst, pre, post, w, 1)
    spikes = np.array([3, 7, 20, 41])
    proj.deliver(spikes, t=0)
    dense = np.zeros((50, 30), np.float64)
    np.add.at(dense, (pre, post), w)
    assert np.allclose(dst.ring[1], dense[spikes].sum(0), atol=1e-5)

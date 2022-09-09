from liquidity import LiquidityCurve

import math


def test_make_out_of_range():
    x_max = 3
    p_min = 1
    p_max = 3
    curve = LiquidityCurve.make_out_of_range(x_max, p_min, p_max)
    assert curve.L > 0
    assert curve.p_min == p_min
    assert curve.p_max == p_max
    assert curve.f(x_max) == 0
    y_max = math.sqrt(p_min * p_max) * x_max
    assert curve.f(0) == y_max

import dataclasses
import math


@dataclasses.dataclass(frozen=True)
class LiquidityCurve:
    # Uniswap v3 Core eq (2.2)
    # (x+L/sqrt(p_b)) * (y+L*sqrt(p_a)) = L**2
    p_min: float
    p_max: float
    L: float

    def f(self, x):
        L = self.L
        return L**2 / (x + L / math.sqrt(self.p_max)) - L * math.sqrt(self.p_min)

    @classmethod
    def make_out_of_range(cls, x_max, p_min, p_max):
        L = math.sqrt(p_max) / (math.sqrt(p_max / p_min) - 1) * x_max
        return cls(p_min, p_max, L)

    @classmethod
    def make(cls, x, y, p_min):
        "TODO: wrap my head around the equations"

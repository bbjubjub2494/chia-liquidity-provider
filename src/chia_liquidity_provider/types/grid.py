from dataclasses import dataclass

from chia.util.ints import uint64


@dataclass(frozen=True)
class Grid:
    """
    Stores the trading grid.
    """

    base_amount: uint64
    quote_amounts: list[uint64]

    @classmethod
    def make(cls, curve, base_increment, base_total_amount):
        quote_amounts = []
        for x in range(0, base_total_amount + base_increment, base_increment):
            Δy = uint64(curve.f(x) - curve.f(x + base_increment))
            quote_amounts.append(Δy)
        return cls(base_amount=base_increment, quote_amounts=quote_amounts)

    def initial_orders(self, price):
        for i in range(1, len(self.quote_amounts)):
            if self.quote_amounts[i] / self.base_amount > price:
                yield -self.base_amount, self.quote_amounts[i - 1]
            else:
                yield self.base_amount, -self.quote_amounts[i]

    def flip(self, base_amount, quote_amount):
        if base_amount not in (-self.base_amount, self.base_amount):
            raise ValueError()
        if quote_amount < 0:
            quote_amount = self.quote_amounts[(i := self.quote_amounts.index(-quote_amount) - 1)]
            if i < 0:
                raise ValueError()
        else:
            quote_amount = -self.quote_amounts[self.quote_amounts.index(quote_amount) + 1]
        base_amount = -base_amount
        return base_amount, quote_amount

    def to_json_dict(self):
        return {"base_amount": self.base_amount, "quote_amounts": self.quote_amounts}

    @classmethod
    def from_json_dict(cls, d):
        return cls(base_amount=d["base_amount"], quote_amounts=d["quote_amounts"])

"""Stock levels with reservations."""


class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self, stock: dict[str, int]):
        self._stock = dict(stock)
        self._reserved: dict[str, int] = {}

    def available(self, sku: str) -> int:
        return self._stock.get(sku, 0) - self._reserved.get(sku, 0)

    def reserve(self, sku: str, qty: int) -> None:
        if qty > self.available(sku):
            raise OutOfStock(f"{sku}: wanted {qty}, have {self.available(sku)}")
        self._reserved[sku] = self._reserved.get(sku, 0) + qty

    def release(self, sku: str, qty: int) -> None:
        self._reserved[sku] = max(0, self._reserved.get(sku, 0) - qty)

    def commit(self, sku: str, qty: int) -> None:
        """Turn a reservation into a sale."""
        self.release(sku, qty)
        self._stock[sku] = self._stock.get(sku, 0) - qty

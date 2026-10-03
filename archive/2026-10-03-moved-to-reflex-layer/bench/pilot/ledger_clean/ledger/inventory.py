class InsufficientStock(Exception):
    def __init__(self, sku, requested, available):
        super().__init__(f"{sku}: requested {requested}, only {available} on hand")
        self.sku, self.requested, self.available = sku, requested, available


class Inventory:
    def __init__(self):
        self._stock = {}

    def receive(self, sku, quantity):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._stock[sku] = self._stock.get(sku, 0) + quantity

    def ship(self, sku, quantity):
        available = self._stock.get(sku, 0)
        if quantity > available:
            raise InsufficientStock(sku, quantity, available)
        self._stock[sku] = available - quantity

    def on_hand(self, sku):
        return self._stock.get(sku, 0)

    def low_stock(self, threshold):
        return sorted(sku for sku, quantity in self._stock.items() if quantity <= threshold)

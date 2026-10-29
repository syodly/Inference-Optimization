"""An order key identifies its original successful result even on retries."""
from inventory import reserve
from pricing import total


class Checkout:
    def __init__(self, stock):
        self.stock = dict(stock)
        self.completed = {}

    def submit(self, key, items, prices, discount='0', tax='0'):
        reserve(self.stock, items)
        amount = total([(prices[sku], quantity) for sku, quantity in items.items()], discount, tax)
        result = {'order_key': key, 'amount': str(amount)}
        self.completed[key] = result
        return result

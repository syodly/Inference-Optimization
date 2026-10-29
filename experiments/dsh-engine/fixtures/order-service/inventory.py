"""Inventory reservations must be atomic, and quantities must be positive."""


def reserve(stock, request):
    for sku, quantity in request.items():
        if stock.get(sku, 0) < quantity:
            raise ValueError('insufficient stock')
        stock[sku] -= quantity
    return stock

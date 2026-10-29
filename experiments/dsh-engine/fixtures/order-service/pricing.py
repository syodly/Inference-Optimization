"""Pricing rules: monetary results use decimal half-up, rounded only at the end."""
from decimal import Decimal, ROUND_HALF_UP


def total(lines, discount='0', tax='0'):
    subtotal = sum(Decimal(str(price))*quantity for price, quantity in lines)
    discounted = (subtotal*(1-Decimal(discount))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return (discounted*(1+Decimal(tax))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

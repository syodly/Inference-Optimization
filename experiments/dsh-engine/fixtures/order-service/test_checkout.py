import unittest
from decimal import Decimal

from checkout import Checkout
from inventory import reserve
from pricing import total


class Rules(unittest.TestCase):
    def test_round_once(self):
        self.assertEqual(total([('0.05', 1)], discount='0.1', tax='0.1'), Decimal('0.05'))

    def test_atomic_reservation(self):
        stock = {'a': 3, 'b': 0}
        with self.assertRaises(ValueError):
            reserve(stock, {'a': 2, 'b': 1})
        self.assertEqual(stock, {'a': 3, 'b': 0})

    def test_negative_quantity(self):
        stock = {'a': 3}
        with self.assertRaises(ValueError):
            reserve(stock, {'a': -2})
        self.assertEqual(stock, {'a': 3})

    def test_zero_quantity(self):
        with self.assertRaises(ValueError):
            reserve({'a': 3}, {'a': 0})

    def test_retry_does_not_reserve_twice(self):
        service = Checkout({'a': 4})
        first = service.submit('key1', {'a': 1}, {'a': '2.00'})
        second = service.submit('key1', {'a': 1}, {'a': '2.00'})
        self.assertEqual(first, second)
        self.assertEqual(service.stock, {'a': 3})

    def test_invalid_price_does_not_consume_stock(self):
        service = Checkout({'a': 4})
        with self.assertRaises(Exception):
            service.submit('key1', {'a': 1}, {'a': 'bad'})
        self.assertEqual(service.stock, {'a': 4})
        self.assertEqual(service.completed, {})

    def test_success(self):
        self.assertEqual(total([('10.00', 2)], tax='0.1'), Decimal('22.00'))


if __name__ == '__main__':
    unittest.main()

# Small Checkout Service

Run the regression suite with `python3 -m unittest -v`.

Public contracts:

- Prices use Decimal. Apply discount and tax, then round the final amount once to cents using ROUND_HALF_UP.
- Inventory reservations accept positive integer quantities only. A failed reservation leaves the entire stock unchanged.
- A successful order key is idempotent: subsequent submissions return its original result without consuming stock again.
- An invalid order must not consume stock or record success.
- Preserve the existing APIs and regression tests.

This repository is a curated diagnostic workload, not an upstream benchmark.

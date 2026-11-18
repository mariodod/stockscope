# Metrics catalog

The canonical metric catalog lives in [app/seed/metrics_catalog.md](../app/seed/metrics_catalog.md). It ships inside the Python package so the seed command works from a normal install as well as from a source checkout.

The seed command parses that file directly:

```bash
python -m app.seed.metrics
```

Metric keys, formulas, units and ranking directions are defined there. Do not duplicate the list in code.

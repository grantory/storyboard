from __future__ import annotations

from src.gui.pipeline import Pipeline


def test_pipeline_init_without_key():
    p = Pipeline()
    # client may be None if key not set; construction should not raise
    assert hasattr(p, "cfg")



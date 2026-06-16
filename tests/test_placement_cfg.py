import pytest

from nnsplace.placement_cfg import NnsConfig


def test_config_grid_width_too_small() -> None:
    with pytest.raises(ValueError, match="Grid width must be at least 3"):
        NnsConfig(x=2, y=5, delta_x=1, delta_y=1)


def test_config_grid_height_too_small() -> None:
    with pytest.raises(ValueError, match="Grid height must be at least 3"):
        NnsConfig(x=5, y=2, delta_x=1, delta_y=1)


def test_config_delta_x_non_positive() -> None:
    with pytest.raises(ValueError, match="delta_x must be positive"):
        NnsConfig(x=5, y=5, delta_x=0, delta_y=1)


def test_config_delta_y_non_positive() -> None:
    with pytest.raises(ValueError, match="delta_y must be positive"):
        NnsConfig(x=5, y=5, delta_x=1, delta_y=0)


def test_config_reserved_col_too_low() -> None:
    with pytest.raises(ValueError, match="reserved_col must be between 1 and"):
        NnsConfig(x=5, y=5, delta_x=1, delta_y=1, reserved_col=0)


def test_config_reserved_col_too_high() -> None:
    with pytest.raises(ValueError, match="reserved_col must be between 1 and"):
        NnsConfig(x=5, y=5, delta_x=1, delta_y=1, reserved_col=6)


def test_config_getattr_grid() -> None:
    cfg = NnsConfig(x=10, y=8, delta_x=2, delta_y=3)
    assert cfg.grid == (10, 8)


def test_config_getattr_delta() -> None:
    cfg = NnsConfig(x=10, y=8, delta_x=2, delta_y=3)
    assert cfg.delta == (2, 3)


def test_config_getattr_unknown() -> None:
    cfg = NnsConfig(x=10, y=8, delta_x=2, delta_y=3)
    with pytest.raises(AttributeError, match="NnsConfig.*no attribute 'foo'"):
        _ = cfg.foo


def test_config_properties() -> None:
    cfg = NnsConfig(x=10, y=8, delta_x=2, delta_y=3, reserved_col=5)
    assert cfg.grid == (10, 8)
    assert cfg.delta == (2, 3)
    assert cfg.reserved_col == 5


def test_config_default_reserved_col() -> None:
    cfg = NnsConfig(x=10, y=8, delta_x=2, delta_y=3)
    assert cfg.reserved_col == 27


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

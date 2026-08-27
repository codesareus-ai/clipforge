from app.services import reframe


def test_deadzone_holds_small_movements():
    centers = [{"x": 0.5, "y": 0.5}, {"x": 0.51, "y": 0.5}, {"x": 0.5, "y": 0.5}]
    out = reframe._deadzone_ema(centers)
    assert out[1]["x"] == 0.5  # sub-deadzone move ignored


def test_ema_moves_on_large_movement():
    centers = [{"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.5}]
    out = reframe._deadzone_ema(centers)
    assert out[1]["x"] > 0.5
    assert out[1]["x"] < 0.9


def test_clamp_bounds():
    assert reframe._clamp(1.4) == 1.0
    assert reframe._clamp(-0.2) == 0.0
    assert reframe._clamp(0.3) == 0.3

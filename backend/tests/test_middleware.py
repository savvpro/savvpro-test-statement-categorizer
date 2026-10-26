from app.middleware import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_allows_up_to_the_limit_then_blocks():
    clock = Clock()
    limiter = SlidingWindowLimiter(3, window=60, clock=clock)
    assert [limiter.check("a") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("a") > 0


def test_retry_after_counts_down_to_the_oldest_hit_expiring():
    clock = Clock()
    limiter = SlidingWindowLimiter(1, window=60, clock=clock)
    limiter.check("a")
    clock.now += 20
    assert round(limiter.check("a")) == 40
    clock.now += 40
    assert limiter.check("a") == 0.0


def test_window_slides_instead_of_resetting():
    clock = Clock()
    limiter = SlidingWindowLimiter(2, window=60, clock=clock)
    limiter.check("a")
    clock.now += 30
    limiter.check("a")
    clock.now += 31  # the first hit has expired, the second has not
    assert limiter.check("a") == 0.0
    assert limiter.check("a") > 0


def test_keys_are_independent():
    limiter = SlidingWindowLimiter(1, window=60, clock=Clock())
    assert limiter.check("a") == 0.0
    assert limiter.check("b") == 0.0
    assert limiter.check("a") > 0


def test_idle_keys_are_pruned_so_memory_stays_bounded():
    clock = Clock()
    limiter = SlidingWindowLimiter(1, window=60, clock=clock, max_keys=10)
    for i in range(10):
        limiter.check(f"client-{i}")
    clock.now += 120
    limiter.check("new")
    assert len(limiter._hits) == 1

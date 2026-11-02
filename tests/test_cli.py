

def test_retry_delay_backs_off_without_sdr_and_resets_after_data():
    from taggle_rx.cli import retry_delay
    delays, delay = [], 1
    for _ in range(8):
        delay = retry_delay(delay, False)
        delays.append(delay)
    assert delays == [2, 4, 8, 16, 32, 60, 60, 60]
    assert retry_delay(60, True) == 2

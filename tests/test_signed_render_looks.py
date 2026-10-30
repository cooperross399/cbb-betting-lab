"""Which count a receipt-pinned report was rendered at (decision 66)."""

from cbb_betting_lab.restatement import signed_render_looks


def _render(n):
    return f"report at {n}"


def test_the_record_count_when_the_receipts_cite_the_original_render():
    assert signed_render_looks(_render, "report at 133", record_looks=133, ledger_looks=143) == 133


def test_a_later_count_when_the_receipts_were_signed_again_against_a_re_render():
    assert signed_render_looks(_render, "report at 143", record_looks=133, ledger_looks=143) == 143
    assert signed_render_looks(_render, "report at 140", record_looks=133, ledger_looks=143) == 140


def test_bytes_that_are_no_render_fall_back_to_the_record_so_the_pin_check_fails():
    assert signed_render_looks(_render, "edited by hand", record_looks=133, ledger_looks=143) == 133
    assert signed_render_looks(_render, "report at 150", record_looks=133, ledger_looks=143) == 133

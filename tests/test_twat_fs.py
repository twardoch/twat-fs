"""Test suite for twat_fs."""
# this_file: tests/test_package.py

import twat_fs  # Moved from test_version


def test_version():
    """Verify package exposes version."""
    # import twat_fs # Moved to top

    assert twat_fs.__version__

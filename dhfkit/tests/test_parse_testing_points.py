"""Unit tests for dhfkit.testing_points.parse_testing_points."""

from __future__ import annotations

import pytest

from dhfkit.testing_points import parse_testing_points


def test_returns_empty_for_none():
    assert parse_testing_points(None) == []


def test_returns_empty_for_empty_string():
    assert parse_testing_points("") == []


def test_single_point():
    assert parse_testing_points("T1: Given X happens, do Y.") == ["T1"]


def test_multiple_points():
    text = "T1: Given a CT series is active.\nT2: Given the job succeeds.\nT3: Given modality is MR."
    assert parse_testing_points(text) == ["T1", "T2", "T3"]


def test_points_with_leading_whitespace():
    text = "  T1: Point one.\n  T2: Point two."
    assert parse_testing_points(text) == ["T1", "T2"]


def test_multi_digit_point_ids():
    text = "T10: Ten.\nT11: Eleven.\nT100: Hundred."
    assert parse_testing_points(text) == ["T10", "T11", "T100"]


def test_ignores_lines_without_colon_prefix():
    text = "Some preamble text.\nT1: First point.\nAnother non-point line.\nT2: Second point."
    assert parse_testing_points(text) == ["T1", "T2"]


def test_ignores_inline_t_references():
    """T1 appearing mid-sentence without leading 'T<digits>:' pattern is not a point ID."""
    text = "This test covers T1 and T2 from the spec.\nT3: Actual point."
    assert parse_testing_points(text) == ["T3"]


def test_returns_in_document_order():
    text = "T3: Third.\nT1: First.\nT2: Second."
    assert parse_testing_points(text) == ["T3", "T1", "T2"]


def test_whitespace_only_string():
    assert parse_testing_points("   \n  \n") == []

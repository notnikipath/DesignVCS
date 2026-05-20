from shared.designvcs_common import DiffMode, compare_versions, detect_mentions


def test_compare_versions_returns_valid_metrics() -> None:
    result = compare_versions(
        base_version_id="v1",
        target_version_id="v2",
        base_checksum="a" * 64,
        target_checksum="f" * 64,
        base_size=200_000,
        target_size=260_000,
        mode=DiffMode.FRAME,
    )
    assert 0 <= result.pixel_delta_pct <= 100
    assert 0 <= result.similarity_score <= 100
    assert result.changed_frames > 0


def test_detect_mentions_deduplicates_users() -> None:
    mentions = detect_mentions("Please check @alex and @john_doe, plus @alex again")
    assert mentions == ["alex", "john_doe"]
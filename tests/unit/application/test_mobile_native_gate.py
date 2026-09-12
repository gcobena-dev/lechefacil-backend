"""An OTA bundle must not be handed to a shell that cannot run it.

v096 shipped the Android back button fix as JS while the `@capacitor/app`
plugin it needs stayed out of the installed APK. The bundle installed cleanly,
nothing failed, and the back button silently kept closing the app. This gate is
what stops that from happening again.
"""

from __future__ import annotations

from src.interfaces.http.routers.mobile import _parse_version, needs_native_update

BUNDLE_NEEDING_NATIVE = {"version": "0.0.983", "minNativeBuild": 982}
PURE_WEB_BUNDLE = {"version": "0.0.983"}


def test_a_shell_older_than_the_floor_is_blocked():
    assert needs_native_update(BUNDLE_NEEDING_NATIVE, 1) is True


def test_a_shell_at_the_floor_is_allowed():
    assert needs_native_update(BUNDLE_NEEDING_NATIVE, 982) is False


def test_a_newer_shell_is_allowed():
    assert needs_native_update(BUNDLE_NEEDING_NATIVE, 1000) is False


def test_a_shell_that_cannot_report_its_build_counts_as_too_old():
    # Only the APKs predating the plugin that reports the build fail to report
    # it — exactly the ones that need replacing.
    assert needs_native_update(BUNDLE_NEEDING_NATIVE, None) is True


def test_a_bundle_with_no_floor_runs_anywhere():
    assert needs_native_update(PURE_WEB_BUNDLE, None) is False
    assert needs_native_update(PURE_WEB_BUNDLE, 1) is False


def test_a_malformed_floor_does_not_lock_everyone_out():
    # A typo in version.json must not brick updates for the whole fleet.
    assert needs_native_update({"minNativeBuild": "no"}, 1) is False


def test_a_floor_written_as_a_string_still_gates():
    assert needs_native_update({"minNativeBuild": "982"}, 1) is True


def test_two_part_versions_compare_against_three_part_ones():
    # The old parser raised IndexError on "1.0" and fell back to (0,0,0),
    # which made every release look newer than it.
    assert _parse_version("1.0") == (1, 0, 0)
    assert _parse_version("0.0.982") == (0, 0, 982)
    assert _parse_version("0.0.983") > _parse_version("0.0.982")


def test_an_unparseable_version_does_not_raise():
    assert _parse_version("beta") == (0, 0, 0)

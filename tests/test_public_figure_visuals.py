from scripts.public_figure_visuals import (
    annotate_scenes_with_public_figure_visuals,
    build_subject_visual_profile,
    extract_subject_from_topic,
    format_visual_profile_for_prompt,
    is_allowed_license,
    reference_from_commons_page,
    should_prepare_public_figure_visuals,
)


def _commons_page(license_name="CC BY-SA 4.0", usage_terms="Creative Commons Attribution-Share Alike 4.0"):
    return {
        "title": "File:Michael Jackson 1988.jpg",
        "imageinfo": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/example.jpg",
                "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/example.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Michael_Jackson_1988.jpg",
                "mime": "image/jpeg",
                "width": 1200,
                "height": 1600,
                "sha1": "abc123",
                "extmetadata": {
                    "LicenseShortName": {"value": license_name},
                    "UsageTerms": {"value": usage_terms},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                    "Artist": {"value": "Jane Photographer"},
                    "ImageDescription": {"value": "<p>Michael Jackson performing in 1988</p>"},
                },
            }
        ],
    }


def test_extract_subject_from_biography_topic_prefixes():
    assert extract_subject_from_topic("La vida de Michael Jackson", "agent_biografias.md") == "Michael Jackson"
    assert extract_subject_from_topic("Biografia de Nikola Tesla", "agent_biografias.md") == "Nikola Tesla"


def test_explicit_false_option_disables_public_figure_visuals():
    assert not should_prepare_public_figure_visuals(
        "La vida de Michael Jackson",
        "agent_biografias.md",
        {"publicFigureVisualsEnabled": "false"},
    )


def test_license_allowlist_accepts_commercial_reusable_cc_and_public_domain():
    assert is_allowed_license("CC BY 4.0")
    assert is_allowed_license("CC BY-SA 3.0")
    assert is_allowed_license("CC0")
    assert is_allowed_license("Public domain")


def test_license_allowlist_blocks_nc_nd_fair_use_and_unknown():
    assert not is_allowed_license("CC BY-NC 4.0")
    assert not is_allowed_license("CC BY-ND 4.0")
    assert not is_allowed_license("Fair use")
    assert not is_allowed_license("Unknown")


def test_reference_from_commons_page_extracts_license_and_attribution():
    ref = reference_from_commons_page(_commons_page())

    assert ref is not None
    assert ref["licenseFamily"] == "cc_by_sa"
    assert ref["author"] == "Jane Photographer"
    assert "Jane Photographer" in ref["attribution"]
    assert ref["downloadUrl"].endswith("example.jpg")


def test_reference_from_commons_page_rejects_blocked_license():
    assert reference_from_commons_page(_commons_page("CC BY-NC 4.0", "NonCommercial")) is None


def test_michael_jackson_profile_has_specific_visual_cues():
    ref = reference_from_commons_page(_commons_page())
    profile = build_subject_visual_profile(
        "La vida de Michael Jackson",
        "agent_biografias.md",
        references=[ref],
        entity={"label": "Michael Jackson", "description": "American singer, dancer and performer"},
    )
    context = format_visual_profile_for_prompt(profile).lower()

    assert profile["publicFigureConfidence"] >= 0.9
    assert "black fedora" in context
    assert "single white glove" in context
    assert "generic adult man" in context


def test_annotate_scenes_assigns_archive_references_and_context():
    ref = reference_from_commons_page(_commons_page())
    profile = build_subject_visual_profile("La vida de Michael Jackson", "agent_biografias.md", references=[ref])
    scenes = [
        {"scene_number": 1, "prompt": "scene one"},
        {"scene_number": 2, "prompt": "scene two"},
        {"scene_number": 3, "prompt": "scene three"},
    ]

    annotated = annotate_scenes_with_public_figure_visuals(
        scenes,
        {"detected": True, "subject": "Michael Jackson", "profile": profile, "references": [ref]},
        max_archive_images=1,
    )

    assert annotated[0]["visualSource"] == "licensed_archive"
    assert annotated[0]["archiveReference"]["license"] == "CC BY-SA 4.0"
    assert all(scene["public_figure_subject"] == "Michael Jackson" for scene in annotated)
    assert "Michael Jackson" in annotated[1]["public_figure_visual_context"]

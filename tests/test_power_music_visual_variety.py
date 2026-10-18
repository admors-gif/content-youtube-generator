"""Offline regressions for visual variety without changing an authored story."""

import copy
import json
import unittest

from scripts.power_music import build_generation_prompt, build_imported_song_package, fallback_package, normalize_package
from scripts.power_music_director import (
    build_beat_shot_recipe,
    build_music_video_director_plan,
    build_shot_recipe,
    director_scene_prompt,
    normalize_storyboard,
)
from scripts.power_music_story import STORY_SCHEMA, STORY_SYSTEM_PROMPT, prepare_music_story
from tests.test_power_music_story_planner import client_with


def song(treatment=None):
    video = {
        "storyboard": {
            "contentVersion": "music_storyboard_v1", "source": "composer",
            "premise": "A daughter returns to the home port and reunites with her mother.",
            "protagonist": "the adult daughter with curly hair and her grey-haired mother",
            "wardrobe": "daughter in a blue jacket; mother in a beige coat",
            "locations": ["the blue boat inside the home port", "the wooden pier beside the lighthouse"],
            "beats": [
                {"section": "Intro", "location": "the blue boat inside the home port", "action": "The daughter recognizes the lighthouse from the boat.", "emotion": "anticipation"},
                {"section": "Verse 1", "location": "the blue boat inside the home port", "action": "The daughter approaches the pier in the boat.", "emotion": "uncertainty"},
                {"section": "Chorus", "location": "the wooden pier beside the lighthouse", "action": "Mother and daughter embrace beside the boat.", "emotion": "relief"},
                {"section": "Bridge", "location": "the wooden pier beside the lighthouse", "action": "The mother rests her hand on her daughter's shoulder.", "emotion": "trust"},
                {"section": "Chorus", "location": "the wooden pier beside the lighthouse", "action": "Mother and daughter sit together looking at the boat.", "emotion": "belonging"},
                {"section": "Final", "location": "the wooden pier beside the lighthouse", "action": "Mother and daughter return home together.", "emotion": "calm"},
            ],
        },
    }
    if treatment:
        video["visualTreatment"] = treatment
    return {
        "title": "Regreso al puerto", "lyrics": "[Intro]\nVuelvo al puerto\n[Verso 1]\nMi madre me espera\n[Coro]\nVuelvo a tus brazos\n[Puente]\nEstoy en casa\n[Coro]\nAqui pertenezco\n[Final]\nVolvemos juntas",
        "videoConcept": video,
    }


class MusicVisualVarietyTests(unittest.TestCase):
    def test_new_creators_default_to_hybrid_and_keep_explicit_treatment(self):
        self.assertIn('"visualTreatment": "hybrid"', build_generation_prompt({"theme": "empezar de nuevo"}))
        for treatment in ["narrative", "hybrid", "abstract"]:
            with self.subTest(treatment=treatment):
                payload = {"title": "Empiezo", "lyrics": "[Chorus]\nDecido empezar", "visualTreatment": treatment}
                self.assertEqual(build_imported_song_package(payload)["videoConcept"]["visualTreatment"], treatment)
                self.assertEqual(fallback_package(payload)["videoConcept"]["visualTreatment"], treatment)
                self.assertEqual(normalize_package(song(), payload)["videoConcept"]["visualTreatment"], treatment)
        self.assertEqual(build_imported_song_package({"lyrics": "Respiro y empiezo"})["videoConcept"]["visualTreatment"], "hybrid")

    def test_old_authored_package_remains_narrative(self):
        package = normalize_package(song())
        self.assertEqual(package["videoConcept"]["visualTreatment"], "narrative")
        self.assertEqual(package["videoConcept"]["storyboard"], song()["videoConcept"]["storyboard"])

    def test_twelve_chorus_shots_have_real_visual_subject_variety(self):
        plan = build_music_video_director_plan(song("hybrid"))
        shots = [build_beat_shot_recipe("Coro - epico", "Vuelvo a tus brazos", index, plan, progress=.4) for index in range(12)]
        self.assertEqual({shot["shotType"] for shot in shots}, {"character", "environment", "detail", "abstract"})
        self.assertLessEqual(sum(shot["shotType"] == "character" for shot in shots), 4)
        signatures = [(shot["subject"], shot["action"], shot["location"]) for shot in shots]
        self.assertGreaterEqual(len(set(signatures)), 6)
        self.assertTrue(all(previous != current for previous, current in zip(signatures, signatures[1:])))
        self.assertTrue(all(shot["location"] == "the wooden pier beside the lighthouse" for shot in shots))
        for shot in shots:
            self.assertEqual(shot["authoredAction"], "Mother and daughter embrace beside the boat.")
            self.assertEqual(shot["storyPremise"], song()["videoConcept"]["storyboard"]["premise"])
            if shot["shotType"] != "character":
                self.assertEqual(shot["wardrobe"], "none")
                self.assertNotEqual(shot["subject"], plan["storyboard"]["protagonist"])
                self.assertIn("no visible people", shot["humanPolicy"])
                self.assertNotIn("rooftop", shot["subject"])
                self.assertNotIn("bedroom", shot["subject"])

    def test_authored_character_shot_is_not_repeated_through_the_whole_chorus(self):
        package = song("hybrid")
        for beat in package["videoConcept"]["storyboard"]["beats"]:
            beat.update(shotType="character", subject="the mother and daughter", function="preserve the reunion")
        plan = build_music_video_director_plan(package)
        shots = [build_shot_recipe("Chorus", "", index, plan) for index in range(12)]
        self.assertLessEqual(sum(shot["shotType"] == "character" for shot in shots), 4)
        self.assertTrue(all(shot["subject"] != "the mother and daughter" for shot in shots if shot["shotType"] != "character"))

    def test_consecutive_explicit_inserts_change_visual_focus(self):
        package = song("hybrid")
        for beat in package["videoConcept"]["storyboard"]["beats"]:
            beat.update(shotType="detail", subject="the existing wood of the pier")
        plan = build_music_video_director_plan(package)
        shots = [build_shot_recipe("Chorus", "", index, plan) for index in range(12)]
        signatures = [(shot["subject"], shot["action"], shot["composition"]) for shot in shots]
        self.assertTrue(all(previous != current for previous, current in zip(signatures, signatures[1:])))

    def test_explicit_task_detail_preserves_hands_subject_and_authored_action(self):
        package = song("hybrid")
        beat = package["videoConcept"]["storyboard"]["beats"][2]
        beat.update(
            shotType="detail", subject="the daughter's hands securing the boat's existing mooring rope",
            action="The daughter's hands tighten the mooring rope around the pier cleat.",
            function="make her decision visible through finishing a concrete task",
        )
        plan = build_music_video_director_plan(package)
        recipe = build_shot_recipe("Chorus", "", 2, plan)
        self.assertEqual(recipe["subject"], beat["subject"])
        self.assertEqual(recipe["action"], beat["action"])
        self.assertEqual(recipe["authoredAction"], beat["action"])
        self.assertIn("cropped hands", recipe["humanPolicy"])
        self.assertNotIn("no visible people or body parts", recipe["humanPolicy"])
        self.assertEqual(recipe["category"], "narrative_detail")
        prompt = director_scene_prompt("Chorus", "", 2, plan)
        self.assertIn(beat["subject"], prompt)
        self.assertIn(beat["action"], prompt)
        self.assertNotIn("keep the cast off screen", prompt)

    def test_environment_and_abstract_preview_do_not_order_the_authored_cast_back_in(self):
        for treatment, index in [("hybrid", 1), ("abstract", 2)]:
            package = song(treatment)
            package["videoConcept"]["userVisualDirection"] = "Mother and daughter embrace and return to the pier together."
            plan = build_music_video_director_plan(package)
            recipe = build_shot_recipe("Chorus", "", index, plan)
            self.assertTrue(recipe["authoredAction"])
            self.assertNotIn(recipe["authoredAction"], recipe["lyricMetaphor"])
            prompt = director_scene_prompt("Chorus", "", index, plan)
            self.assertNotIn(package["videoConcept"]["userVisualDirection"], prompt)
            self.assertNotIn(plan["storyboard"]["premise"], prompt)
            self.assertNotIn(plan["storyboard"]["protagonist"], prompt)
            self.assertNotIn(recipe["authoredAction"], prompt)
            self.assertIn(recipe["action"], prompt)
            self.assertIn("keep the cast off screen", prompt)

    def test_full_song_planner_requests_distinct_visual_situations_without_a_schema_minimum(self):
        for prompt in [STORY_SYSTEM_PROMPT, build_generation_prompt({"theme": "volver a empezar"})]:
            self.assertIn("12-18", prompt)
        self.assertIn("2-3 for a long", STORY_SYSTEM_PROMPT)
        self.assertIn("no son un limite de cantidad", build_generation_prompt({}))
        self.assertNotIn("minItems", STORY_SCHEMA["properties"]["beats"])

    def test_abstract_mode_overrides_old_character_shots_without_losing_context(self):
        package = song("abstract")
        for beat in package["videoConcept"]["storyboard"]["beats"]:
            beat.update(shotType="character", subject="the mother and daughter")
        plan = build_music_video_director_plan(package)
        shots = [build_shot_recipe("Chorus", "", index, plan) for index in range(9)]
        self.assertTrue(all(shot["shotType"] == "abstract" for shot in shots))
        self.assertTrue(all(shot["subject"] != "the mother and daughter" for shot in shots))
        self.assertGreaterEqual(len({shot["subject"] for shot in shots}), 3)
        self.assertTrue(all(shot["authoredAction"] in [beat["action"] for beat in plan["storyboard"]["beats"]] for shot in shots))

    def test_optional_v1_visual_fields_survive_normalization(self):
        board = copy.deepcopy(song()["videoConcept"]["storyboard"])
        board["beats"][0].update(shotType="environment", subject="the home port in morning mist", function="establish the return")
        self.assertEqual(normalize_storyboard(board), board)

    def test_visual_subject_cannot_smuggle_an_unrequested_gym_into_the_story(self):
        package = song("hybrid")
        package["videoConcept"]["storyboard"]["beats"][0].update(shotType="detail", subject="a dumbbell in a gym")
        plan = build_music_video_director_plan(package)
        self.assertFalse(plan["storyboard"])
        self.assertFalse(plan["athleticStory"])

    def test_section_names_match_across_languages_and_performance_suffixes(self):
        plan = build_music_video_director_plan(song())
        for section, index, action in [
            ("[Verso 1 - rap mas intenso]", 1, "The daughter approaches the pier in the boat."),
            ("Coro - melodico y pegajoso", 2, "Mother and daughter embrace beside the boat."),
            ("Puente - oscuro, poderoso", 3, "The mother rests her hand on her daughter's shoulder."),
            ("Coro final - epico", 5, "Mother and daughter return home together."),
        ]:
            self.assertEqual(build_shot_recipe(section, "", index, plan)["authoredAction"], action)

    def test_repeated_choruses_follow_timeline_without_modulo_cycling(self):
        plan = build_music_video_director_plan(song("hybrid"))
        early = build_beat_shot_recipe("Coro - epico", "", 12, plan, progress=.35)
        late = build_beat_shot_recipe("Coro - epico", "", 30, plan, progress=.85)
        self.assertIn("embrace", early["authoredAction"])
        self.assertIn("sit together", late["authoredAction"])
        unknown = [build_beat_shot_recipe("Instrumental", "", index, plan, progress=value)["storyBeatId"] for index, value in enumerate([0, .25, .5, .75, 1])]
        self.assertEqual(unknown, sorted(unknown))

    def test_nonhuman_preview_prompt_explicitly_keeps_cast_off_screen(self):
        plan = build_music_video_director_plan(song("hybrid"))
        prompt = director_scene_prompt("Chorus", "", 1, plan)
        self.assertIn("shot type: environment", prompt)
        self.assertIn("keep the cast off screen", prompt)

    def test_treatment_is_part_of_planner_input_and_cache_signature(self):
        package = song("hybrid")
        package["videoConcept"].pop("storyboard")
        client = client_with()
        planned, _ = prepare_music_story(package, client=client)
        request = json.loads(client.chat.completions.create.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(request["visualTreatment"], "hybrid")
        planned["videoConcept"]["visualTreatment"] = "abstract"
        prepare_music_story(planned, client=client)
        self.assertEqual(client.chat.completions.create.call_count, 2)


if __name__ == "__main__":
    unittest.main()

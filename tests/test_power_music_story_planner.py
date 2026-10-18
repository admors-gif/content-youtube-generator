import copy
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.power_music_story import prepare_music_story


def story(**overrides):
    return {
        "contentVersion": "music_storyboard_v1", "source": "composer",
        "premise": "A daughter returns by blue boat and reunites with her mother at their home port.",
        "protagonist": "The same adult daughter in her thirties and her mother in her sixties.",
        "wardrobe": "Daughter wears a blue cotton jacket; mother wears a cream cardigan.",
        "locations": ["the home port", "the wooden pier"],
        "beats": [
            {"section": "Intro", "location": "the home port", "action": "Daughter approaches in the blue boat.", "emotion": "anticipation"},
            {"section": "Verse 1", "location": "the wooden pier", "action": "Mother waits and recognizes her daughter.", "emotion": "recognition"},
            {"section": "Chorus", "location": "the wooden pier", "action": "Mother and daughter embrace.", "emotion": "relief"},
            {"section": "Final", "location": "the home port", "action": "They sit together near the blue boat.", "emotion": "belonging"},
        ],
        **overrides,
    }


def package():
    return {
        "title": "Regreso al puerto",
        "lyrics": "[Intro]\nVuelvo en mi barca azul al puerto\n[Verse 1]\nMama me espera en el muelle\n[Chorus]\nNos abrazamos despues de tanto tiempo\n[Final]\nVuelvo a mi hogar contigo",
        "videoConcept": {},
    }


def client_with(data=None, *, finish_reason="stop", refusal=None):
    response = SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(
            content=json.dumps(story() if data is None else data), refusal=refusal,
        ))],
        usage=SimpleNamespace(model_dump=lambda: {"prompt_tokens": 180, "completion_tokens": 250}),
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=Mock(return_value=response))))
    return client


class MusicStoryPlannerTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "CONTENT_FACTORY_MUSIC_STORY_MODEL": "gpt-6-luna",
            "CONTENT_FACTORY_MUSIC_STORY_PLANNING_ENABLED": "true",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_existing_composer_story_needs_no_extra_call(self):
        source = package()
        source["videoConcept"]["storyboard"] = story()
        client = client_with()
        planned, diagnostics = prepare_music_story(source, client=client)
        client.chat.completions.create.assert_not_called()
        self.assertEqual(diagnostics["source"], "composer")
        self.assertEqual(planned["videoConcept"]["storyboard"], source["videoConcept"]["storyboard"])

    def test_imported_song_gets_semantic_story_without_changing_lyrics(self):
        source = package()
        before = copy.deepcopy(source)
        client = client_with()
        planned, diagnostics = prepare_music_story(source, client=client)
        self.assertEqual(source, before)
        self.assertEqual(planned["lyrics"], source["lyrics"])
        board = planned["videoConcept"]["storyboard"]
        self.assertIn("blue boat", board["premise"])
        self.assertIn("embrace", board["beats"][2]["action"])
        self.assertEqual(board["source"], "openai_story_planner")
        self.assertEqual(diagnostics["usage"]["completion_tokens"], 250)
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertTrue(request["response_format"]["json_schema"]["strict"])
        self.assertNotIn("targetUse", request["messages"][1]["content"])

    def test_unchanged_openai_plan_is_reused_but_edited_lyrics_invalidate_it(self):
        client = client_with()
        planned, _ = prepare_music_story(package(), client=client)
        again, _ = prepare_music_story(planned, client=client)
        self.assertEqual(client.chat.completions.create.call_count, 1)
        again["lyrics"] += "\nAhora regreso con mi hermana"
        prepare_music_story(again, client=client)
        self.assertEqual(client.chat.completions.create.call_count, 2)

    def test_human_direction_is_given_to_planner(self):
        source = package()
        source["videoConcept"]["userVisualDirection"] = "La hija y su madre se reencuentran en un muelle."
        client = client_with()
        prepare_music_story(source, client=client)
        payload = json.loads(client.chat.completions.create.call_args.kwargs["messages"][1]["content"])
        self.assertEqual(payload["explicitVisualDirection"], source["videoConcept"]["userVisualDirection"])
        self.assertFalse(payload["athleticStory"])

    def test_real_retry_reuses_saved_story_from_an_unplanned_package(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "storyboard.json"
            client = client_with()
            planned, _ = prepare_music_story(package(), client=client, cache_path=cache_path)
            retried, diagnostics = prepare_music_story(package(), client=client, cache_path=cache_path)
            self.assertEqual(client.chat.completions.create.call_count, 1)
            self.assertTrue(diagnostics["cacheHit"])
            self.assertEqual(planned["videoConcept"]["storyboard"], retried["videoConcept"]["storyboard"])
            changed = package()
            changed["lyrics"] += "\nAhora vuelvo con mi hermana"
            prepare_music_story(changed, client=client, cache_path=cache_path)
            self.assertEqual(client.chat.completions.create.call_count, 2)

    def test_corrupted_disk_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "storyboard.json"
            cache_path.write_text("{invalid", encoding="utf-8")
            client = client_with()
            _, diagnostics = prepare_music_story(package(), client=client, cache_path=cache_path)
            self.assertFalse(diagnostics["fallback"])
            client.chat.completions.create.assert_called_once()

    def test_invalid_shape_is_visible_fallback(self):
        planned, diagnostics = prepare_music_story(package(), client=client_with({"premise": "missing fields"}))
        self.assertTrue(diagnostics["fallback"])
        self.assertTrue(diagnostics["warnings"])
        self.assertNotIn("storyboard", planned["videoConcept"])

    def test_unrelated_gym_is_rejected(self):
        planned, diagnostics = prepare_music_story(package(), client=client_with(story(
            premise="An athlete is weightlifting in a gym instead of returning to the port.",
        )))
        self.assertTrue(diagnostics["fallback"])
        self.assertEqual(diagnostics["error"], "story_planner_unauthorized_sport")
        self.assertNotIn("storyboard", planned["videoConcept"])

    def test_existing_composer_cannot_introduce_an_unrelated_sport(self):
        source = package()
        source["videoConcept"]["storyboard"] = story(premise="An athlete lifting weights in a gym.")
        client = client_with()
        planned, diagnostics = prepare_music_story(source, client=client)
        self.assertEqual(client.chat.completions.create.call_count, 1)
        self.assertEqual(diagnostics["source"], "openai_story_planner")
        self.assertIn("blue boat", planned["videoConcept"]["storyboard"]["premise"])

    def test_boxing_story_cannot_smuggle_in_weightlifting(self):
        source = package()
        source["lyrics"] = "[Intro]\nSoy boxeadora y vuelvo al ring\n[Chorus]\nPreparo mi combate de boxeo"
        client = client_with(story(premise="A boxer in a boxing gym lifting dumbbells and barbells."))
        _, diagnostics = prepare_music_story(source, client=client)
        self.assertEqual(diagnostics["error"], "story_planner_unauthorized_sport")
        self.assertTrue(diagnostics["fallback"])

    def test_incomplete_or_refused_response_is_fallback(self):
        for kwargs in [{"finish_reason": "length"}, {"refusal": "refused"}]:
            with self.subTest(**kwargs):
                _, diagnostics = prepare_music_story(package(), client=client_with(**kwargs))
                self.assertTrue(diagnostics["fallback"])

    def test_disabled_planner_makes_no_request(self):
        client = client_with()
        with patch.dict(os.environ, {"CONTENT_FACTORY_MUSIC_STORY_PLANNING_ENABLED": "false"}):
            _, diagnostics = prepare_music_story(package(), client=client)
        self.assertTrue(diagnostics["fallback"])
        client.chat.completions.create.assert_not_called()

    def test_sdk_failure_does_not_copy_provider_request_into_diagnostics(self):
        client = client_with()
        client.chat.completions.create.side_effect = RuntimeError("private request details")
        _, diagnostics = prepare_music_story(package(), client=client)
        self.assertEqual(diagnostics["error"], "RuntimeError")
        self.assertNotIn("private", json.dumps(diagnostics))


if __name__ == "__main__":
    unittest.main()

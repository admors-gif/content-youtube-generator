"""Zero-cost regressions for lyric-led music stories and prompt contamination."""

import copy
import unittest

from scripts.power_music import build_generation_prompt, build_imported_song_package, normalize_package
from scripts.power_music_director import (
    DIRECTOR_VERSION,
    build_music_video_director_plan,
    build_story_brief,
    build_shot_recipe,
    director_scene_prompt,
    enrich_package_with_director_plan,
    normalize_storyboard,
    prompt_gate_for_recipe,
    sports_in_text,
    storyboard_sports,
)


class MusicStoryDirectorTests(unittest.TestCase):
    def setUp(self):
        self.song = {
            "title": "Vuelvo a mi",
            "lyrics": "[Intro]\nMe levanto aunque pesa el pasado\n[Verse 1]\nMi palabra es de hierro\n[Chorus]\nEncuentro fuerza y vuelvo a mi\n[Final]\nSuelto la duda y elijo vivir",
            "style": "House para correr",
            "intention": "Disciplina imparable",
        }

    def test_listening_context_and_strength_metaphors_do_not_make_a_gym(self):
        for target_use in ["entrenar fuerza", "correr por la mañana", "gym", "trabajar profundo"]:
            with self.subTest(target_use=target_use):
                plan = build_music_video_director_plan(self.song, {"targetUse": target_use})
                self.assertFalse(plan["storyBrief"]["athleticStory"])
                self.assertNotEqual(plan["visualWorld"]["key"], "athletic_power")
                for index in range(24):
                    recipe = build_shot_recipe("Chorus", "Me levanto, mi palabra pesa, soy de hierro", index, plan)
                    positive_scene = " ".join(str(recipe[key]) for key in ["subject", "action", "wardrobe", "location", "lyricMetaphor", "motif"])
                    for irrelevant in ["weights", "training", "gym", "athlete", "stadium", "boxing"]:
                        self.assertNotIn(irrelevant, positive_scene.lower())

    def test_seed_and_world_do_not_depend_on_listening_context(self):
        first = build_music_video_director_plan(self.song, {"targetUse": "correr"})
        second = build_music_video_director_plan({**self.song, "style": "reggaeton workout"}, {"targetUse": "dormir"})
        self.assertEqual(first["songVisualSeed"], second["songVisualSeed"])
        self.assertEqual(first["visualWorld"], second["visualWorld"])

    def test_actual_weight_training_story_keeps_requested_equipment(self):
        song = {"title": "Mi entrenamiento", "lyrics": "[Verse 1]\nEntro al gimnasio y levanto las pesas\n[Chorus]\nCompleto mi serie con calma"}
        plan = build_music_video_director_plan(song)
        recipe = build_shot_recipe("Verse 1", "levanto las pesas", 0, plan)
        self.assertTrue(plan["athleticStory"])
        self.assertEqual(plan["storyBrief"]["sport"], "strength_training")
        self.assertEqual(recipe["id"], "grounded_training_still")
        self.assertIn("equipment", recipe["subject"])

    def test_running_story_does_not_import_other_sport_equipment(self):
        song = {"title": "Mi primera carrera", "lyrics": "Soy una corredora\nCorro por la pista antes de mi maraton"}
        plan = build_music_video_director_plan(song)
        self.assertTrue(plan["athleticStory"])
        self.assertEqual(plan["storyBrief"]["sport"], "running")
        for index in range(12):
            recipe = build_shot_recipe("Chorus", "Cruzo la pista", index, plan)
            scene = " ".join(str(recipe[key]) for key in ["subject", "location", "motif", "action"])
            self.assertNotIn("gym", scene)
            self.assertNotIn("boxing", scene)
            self.assertNotIn("weights", scene)

    def test_explicit_human_direction_survives_render_replanning(self):
        payload = {"visualBrief": "Una boxeadora prepara su combate en el mismo gimnasio de barrio"}
        enriched = enrich_package_with_director_plan(self.song, payload)
        rebuilt = enrich_package_with_director_plan(enriched)
        for package in [enriched, rebuilt]:
            plan = package["musicVideoDirector"]
            self.assertTrue(plan["athleticStory"])
            self.assertEqual(plan["storyBrief"]["sport"], "boxing")
            self.assertEqual(plan["storyBrief"]["explicitVisualDirection"], payload["visualBrief"])
        self.assertEqual(enriched["musicVideoDirector"]["songVisualSeed"], rebuilt["musicVideoDirector"]["songVisualSeed"])

    def test_human_story_theme_survives_render_replanning(self):
        first = enrich_package_with_director_plan(self.song, {"theme": "La historia de una corredora preparando su maraton"})
        rebuilt = enrich_package_with_director_plan(first)
        self.assertEqual(first["musicVideoDirector"]["visualWorld"], rebuilt["musicVideoDirector"]["visualWorld"])
        self.assertEqual(rebuilt["musicVideoDirector"]["storyBrief"]["sport"], "running")

    def test_negated_gym_in_human_direction_does_not_opt_into_athletics(self):
        plan = build_music_video_director_plan(self.song, {"visualBrief": "Historia de recuperacion emocional, sin gimnasio"})
        self.assertFalse(plan["storyBrief"]["athleticStory"])

    def test_legacy_generated_gym_identity_is_replaced_without_changing_lyrics(self):
        song = copy.deepcopy(self.song)
        song["musicVideoDirector"] = {"version": "power_music_director_v4_song_seed_lyric_metaphor"}
        song["videoConcept"] = {
            "visualIdentity": "gym energy, steel weights, stadium tunnels",
            "directorPlan": song["musicVideoDirector"],
            "scenes": [{"visualPrompt": "a man lifting weights in a gym"}],
        }
        updated = enrich_package_with_director_plan(song)
        self.assertEqual(updated["lyrics"], song["lyrics"])
        self.assertEqual(updated["musicVideoDirector"]["version"], DIRECTOR_VERSION)
        self.assertEqual(updated["videoConcept"]["userVisualDirection"], "")
        self.assertNotIn("gym", updated["videoConcept"]["visualIdentity"])
        self.assertTrue(all(scene["shotRecipe"]["id"] != "grounded_training_still" for scene in updated["videoConcept"]["scenes"]))

    def test_story_progression_retains_character_continuity(self):
        plan = build_music_video_director_plan(self.song)
        recipes = [build_shot_recipe(section, "Encuentro fuerza", index, plan) for index, section in enumerate(["Intro", "Chorus", "Final"])]
        self.assertEqual([recipe["storyStage"] for recipe in recipes], [0, 1, 2])
        self.assertEqual(len({recipe["continuityKey"] for recipe in recipes}), 1)
        self.assertTrue(all(recipe["continuity"] == plan["continuity"] for recipe in recipes))

    def test_image_prompt_uses_emotion_and_keeps_full_camera_instruction(self):
        plan = build_music_video_director_plan(self.song)
        recipe = build_shot_recipe("Chorus", "Me levanto, mi palabra pesa", 1, plan)
        prompt = director_scene_prompt("Chorus", "Me levanto, mi palabra pesa", 1, plan)
        self.assertNotIn("Me levanto", prompt)
        self.assertIn(plan["continuity"]["protagonist"], prompt)
        self.assertIn(recipe["camera"], prompt)
        self.assertTrue(prompt_gate_for_recipe(prompt, recipe)["passed"])

    def test_imported_song_does_not_need_generation_or_a_sporting_context(self):
        package = build_imported_song_package({**self.song, "targetUse": "entrenar fuerza"})
        self.assertEqual(package["lyrics"], self.song["lyrics"])
        self.assertEqual(package["source"], "external_song_import")
        self.assertFalse(package["musicVideoDirector"]["athleticStory"])
        self.assertNotIn("Comfy/Flux", " ".join(package["productionNotes"]))

    def test_composer_prompt_separates_listening_context_from_the_story(self):
        prompt = build_generation_prompt({"theme": "superar el pasado", "targetUse": "entrenar fuerza"})
        self.assertIn("targetUse describe cuando se escucha", prompt)
        self.assertIn("historia cinematografica", prompt)
        self.assertNotIn("pesas de acero", prompt)
        self.assertIn("Me levanto", prompt)

    def _harbor_storyboard(self):
        return {
            "contentVersion": "music_storyboard_v1",
            "source": "composer",
            "premise": "Una hija vuelve al puerto en una barca azul para reencontrarse con su madre.",
            "protagonist": "La hija adulta de pelo rizado y su madre de pelo canoso.",
            "wardrobe": "La hija viste una chaqueta azul y la madre lleva su abrigo beige.",
            "locations": ["La barca azul dentro del puerto", "El muelle junto al faro"],
            "beats": [
                {"section": "Intro", "location": "La barca azul dentro del puerto", "action": "La hija apoya una mano en la borda y reconoce el faro de su pueblo.", "emotion": "Nostalgia contenida"},
                {"section": "Chorus", "location": "El muelle junto al faro", "action": "La hija baja de la barca y abraza a su madre en el muelle.", "emotion": "Alivio y reencuentro"},
                {"section": "Final", "location": "El muelle junto al faro", "action": "Madre e hija permanecen abrazadas mientras miran la barca azul.", "emotion": "Pertenencia y calma"},
            ],
        }

    def test_authored_story_preserves_cast_place_and_action_through_normalization(self):
        storyboard = self._harbor_storyboard()
        song = {"title": "Regreso al puerto", "lyrics": "[Intro]\nRegreso en la barca azul\n[Chorus]\nMadre, vuelvo a tus brazos\n[Final]\nAqui esta mi hogar", "videoConcept": {"storyboard": storyboard}}
        package = normalize_package(song)
        self.assertEqual(package["videoConcept"]["storyboard"], storyboard)
        self.assertEqual(package["musicVideoDirector"]["visualWorld"]["key"], "authored_story")
        for scene, authored in zip(package["videoConcept"]["scenes"], storyboard["beats"]):
            self.assertEqual(scene["shotRecipe"]["location"], authored["location"])
            self.assertEqual(scene["shotRecipe"]["action"], authored["action"])
            self.assertEqual(scene["shotRecipe"]["subject"], storyboard["protagonist"])
            self.assertEqual(scene["shotRecipe"]["wardrobe"], storyboard["wardrobe"])
            self.assertIn(authored["action"], scene["visualPrompt"])
        rebuilt = enrich_package_with_director_plan(package)
        self.assertEqual(rebuilt["videoConcept"]["storyboard"], storyboard)
        self.assertEqual(rebuilt["musicVideoDirector"]["continuity"]["protagonist"], storyboard["protagonist"])

    def test_repeated_story_sections_preserve_authored_beat_order(self):
        storyboard = self._harbor_storyboard()
        storyboard["beats"][2]["section"] = "Chorus"
        plan = build_music_video_director_plan({**self.song, "videoConcept": {"storyboard": storyboard}})
        for index, beat in enumerate(storyboard["beats"]):
            recipe = build_shot_recipe(beat["section"], "", index, plan)
            self.assertEqual(recipe["action"], beat["action"])

    def test_human_direction_does_not_lock_a_hospital_story_to_an_apartment(self):
        direction = "Una hija y su madre se abrazan en la estacion antes de viajar al hospital. La hija lleva una maleta azul."
        package = build_imported_song_package({**self.song, "visualBrief": direction})
        plan = package["musicVideoDirector"]
        self.assertEqual(plan["visualWorld"]["key"], "human_direction")
        self.assertEqual(plan["storyBrief"]["narrativeSource"], "human_direction_fallback")
        self.assertTrue(plan["storyBrief"]["warnings"])
        recipe = build_shot_recipe("Chorus", "Encuentro fuerza", 2, plan)
        self.assertIn(direction, recipe["location"])
        for key in ["subject", "location", "motif", "action", "lyricMetaphor"]:
            for inferred_setting in ["apartment", "courtyard", "garden", "window"]:
                self.assertNotIn(inferred_setting, recipe[key].lower())

    def test_negated_sports_do_not_change_the_affirmative_swimming_story(self):
        package = {"title": "La nadadora", "lyrics": "Una nadadora encuentra su ritmo en la piscina"}
        plan = build_music_video_director_plan(package, {"visualBrief": "Una nadadora en piscina, sin boxeo ni gimnasio"})
        self.assertTrue(plan["athleticStory"])
        self.assertEqual(plan["storyBrief"]["sport"], "swimming")

    def test_storyboard_requires_version_provenance_and_known_locations(self):
        storyboard = self._harbor_storyboard()
        for key in ["contentVersion", "source"]:
            invalid = copy.deepcopy(storyboard)
            invalid.pop(key)
            self.assertEqual(normalize_storyboard(invalid), {})
        invalid = copy.deepcopy(storyboard)
        invalid["beats"][0]["location"] = "Un gimnasio que nadie pidio"
        self.assertEqual(normalize_storyboard(invalid), {})
        storyboard["inputSignature"] = "abc123"
        self.assertEqual(normalize_storyboard(storyboard)["inputSignature"], "abc123")

    def test_authored_sport_unsupported_by_lyrics_or_human_concept_is_rejected(self):
        storyboard = self._harbor_storyboard()
        storyboard["protagonist"] = "Un atleta en un gimnasio"
        package = enrich_package_with_director_plan({**self.song, "videoConcept": {"storyboard": storyboard}})
        self.assertEqual(package["videoConcept"]["storyboard"], {})
        self.assertEqual(package["musicVideoDirector"]["storyBrief"]["narrativeSource"], "heuristic_fallback")

    def test_spanish_and_english_tennis_are_the_same_authorized_sport(self):
        for lyrics in ["Hoy juego tenis en cancha", "I practice tennis on a tennis court"]:
            with self.subTest(lyrics=lyrics):
                plan = build_music_video_director_plan({"title": "Mi partido", "lyrics": lyrics})
                self.assertTrue(plan["athleticStory"])
                self.assertEqual(plan["storyBrief"]["sport"], "tennis")
                self.assertEqual(plan["storyBrief"]["authorizedSports"], ["tennis"])
                self.assertTrue(all("tennis court" in location for location in plan["visualWorld"]["locations"]))

    def test_boxing_gym_is_valid_but_added_weightlifting_is_separate_evidence(self):
        for text in ["Una boxeadora en un gimnasio de boxeo", "A boxer practicing in a boxing gym"]:
            self.assertEqual(sports_in_text(text), {"boxing"})
        self.assertEqual(sports_in_text("Una boxeadora levanta una barra olimpica junto a pesas"), {"boxing", "strength_training"})
        storyboard = self._harbor_storyboard()
        storyboard["premise"] = "A boxer prepares for a boxing match in a boxing gym."
        storyboard["protagonist"] = "The same boxer"
        storyboard["wardrobe"] = "The same boxing outfit"
        storyboard["locations"] = ["The boxing gym"]
        for beat in storyboard["beats"]:
            beat["location"] = "The boxing gym"
            beat["action"] = "The boxer practices simple footwork in the same gym."
        self.assertEqual(storyboard_sports(storyboard), {"boxing"})
        song = {"title": "Mi combate", "lyrics": "Soy una boxeadora preparando mi combate"}
        valid = build_story_brief({**song, "videoConcept": {"storyboard": storyboard}})
        self.assertEqual(valid["authorizedSports"], ["boxing"])
        self.assertTrue(valid["storyboard"])
        for equipment_action in ["The boxer lifts dumbbells.", "The boxer lifts a barbell.", "La boxeadora levanta una barra olimpica.", "La boxeadora usa maquinas de ejercicio."]:
            with self.subTest(action=equipment_action):
                invalid = copy.deepcopy(storyboard)
                invalid["beats"][0]["action"] = equipment_action
                self.assertEqual(storyboard_sports(invalid), {"boxing", "strength_training"})
                self.assertFalse(build_story_brief({**song, "videoConcept": {"storyboard": invalid}})["storyboard"])


if __name__ == "__main__":
    unittest.main()

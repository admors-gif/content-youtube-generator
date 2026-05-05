from scripts.generate_content import (
    _build_podcast_visual_scenes,
    _group_blocks_into_scenes,
)


def _dialogue_blocks(count=120):
    blocks = []
    for i in range(count):
        speaker = "A" if i % 2 == 0 else "B"
        name = "MATEO" if speaker == "A" else "LUCÍA"
        blocks.append({
            "speaker": speaker,
            "name": name,
            "text": f"Bloque {i + 1} con una idea clara para conservar el diálogo completo.",
        })
    return blocks


def test_podcast_dialogue_blocks_are_preserved_when_capped():
    blocks = _dialogue_blocks(120)

    scenes = _group_blocks_into_scenes(
        blocks,
        target_scene_count=12,
        max_scene_count=15,
    )

    preserved = []
    for scene in scenes:
        preserved.extend(scene["dialogue_blocks"])

    assert len(scenes) <= 15
    assert len(preserved) == len(blocks)
    assert [b["text"] for b in preserved] == [b["text"] for b in blocks]


def test_podcast_visual_prompts_avoid_faces_and_hands():
    grouped = _group_blocks_into_scenes(
        _dialogue_blocks(30),
        target_scene_count=12,
        max_scene_count=15,
    )

    scenes = _build_podcast_visual_scenes("autoconfianza y disciplina", grouped)
    prompts = [scene["prompt"].lower() for scene in scenes]

    assert scenes
    assert all("hands outside" in prompt for prompt in prompts)
    assert all("fingers not visible" in prompt for prompt in prompts)
    assert all("no readable text" in prompt for prompt in prompts)
    assert not any("human hands near" in prompt for prompt in prompts)
    assert not any("face not visible" in prompt for prompt in prompts)

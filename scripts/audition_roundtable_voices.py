"""
Auditions short ElevenLabs v3 samples for "Esto no es amor: Mesa redonda".

Default mode is a dry run, so it estimates the samples without spending
credits. Add --generate only when you are ready to create the MP3 files.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

DEFAULT_CONFIG = BASE_DIR / "config" / "podcast_mesa_redonda_voices.json"
DEFAULT_OUTPUT_ROOT = BASE_DIR / "output" / "auditions" / "mesa_redonda"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "")).strip("_") or "sample"


def _load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config: {path}")
    return data


def _candidate_names(character: dict) -> list[str]:
    candidates = character.get("candidate_voices") or []
    if isinstance(candidates, str):
        candidates = [item.strip() for item in candidates.split(",")]
    selected = character.get("selected_voice") or character.get("voice")
    names = []
    for item in [selected, *candidates]:
        if isinstance(item, dict):
            item = item.get("voice") or item.get("name") or item.get("voice_id")
        if isinstance(item, str) and item.strip() and item.strip() not in names:
            names.append(item.strip())
    return names


def _build_manifest(config: dict, only: set[str] | None = None) -> list[dict]:
    manifest = []
    for character in config.get("characters") or []:
        if not isinstance(character, dict):
            continue
        key = str(character.get("key") or character.get("name") or "").upper()
        if only and key not in only and _slug(key) not in only:
            continue
        sample_text = str(character.get("sample_text") or "").strip()
        if not key or not sample_text:
            continue
        for voice in _candidate_names(character):
            manifest.append({
                "character_key": key,
                "character_name": character.get("name") or key.title(),
                "role": character.get("role") or "",
                "voice": voice,
                "text": sample_text,
                "chars": len(sample_text),
                "model": config.get("model") or "eleven_v3",
            })
    return manifest


def _write_scorecard(out_dir: Path, manifest: list[dict]) -> None:
    lines = [
        "# Audiciones mesa redonda",
        "",
        "Califica cada voz del 1 al 5 en: identidad, naturalidad, emocion, claridad y fatiga.",
        "",
        "| Personaje | Voz | Archivo | Identidad | Naturalidad | Emocion | Claridad | Fatiga | Notas |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in manifest:
        filename = item.get("filename") or ""
        lines.append(
            f"| {item['character_name']} | {item['voice']} | {filename} |  |  |  |  |  |  |"
        )
    (out_dir / "scorecard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _estimate(manifest: list[dict]) -> dict:
    chars = sum(item["chars"] for item in manifest)
    return {
        "samples": len(manifest),
        "characters": chars,
        "note": "ElevenLabs bills by credits/model/voice. This is a character estimate only.",
    }


def _synthesize_sample(text: str, output_path: Path, voice: str, model: str, settings: dict) -> tuple[bool, str]:
    from elevenlabs_tts import _prepare_tts_text, get_voice_id

    voice_id = get_voice_id(voice)
    payload = {
        "text": _prepare_tts_text(text, model),
        "model_id": model,
        "voice_settings": {
            "stability": settings.get("stability", 0.45),
            "similarity_boost": settings.get("similarity_boost", 0.76),
            "style": settings.get("style", 0.0),
            "use_speaker_boost": False,
        },
    }
    if model == "eleven_multilingual_v2":
        payload["voice_settings"]["speed"] = settings.get("speed", 1.0)

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_192",
        data=body,
        headers={
            "xi-api-key": os.environ["ELEVENLABS_API_KEY"],
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            audio = response.read()
        output_path.write_bytes(audio)
        return True, f"{len(audio) // 1024} KB"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='ignore')[:200]}"
    except Exception as exc:
        return False, str(exc)[:200]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", default=None)
    parser.add_argument("--only", default="", help="Comma-separated character keys, e.g. MATEO,LUCIA")
    parser.add_argument("--generate", action="store_true", help="Actually generate MP3 files and spend ElevenLabs credits.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = _load_config(config_path)
    only = {item.strip().upper() for item in args.only.split(",") if item.strip()}
    manifest = _build_manifest(config, only=only or None)
    estimate = _estimate(manifest)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else DEFAULT_OUTPUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, item in enumerate(manifest, 1):
        item["filename"] = f"{index:02d}_{_slug(item['character_key'])}_{_slug(item['voice'])}.mp3"

    (out_dir / "manifest.json").write_text(
        json.dumps({"estimate": estimate, "samples": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_scorecard(out_dir, manifest)

    print(f"Config: {config_path}")
    print(f"Output: {out_dir}")
    print(f"Samples: {estimate['samples']}")
    print(f"Characters: {estimate['characters']}")

    if not args.generate:
        print("Dry run only. Add --generate to create MP3 auditions.")
        return 0

    _load_env_file(BASE_DIR / ".env")
    _load_env_file(BASE_DIR / "web" / ".env.local")
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("ERROR: ELEVENLABS_API_KEY is not configured.", file=sys.stderr)
        return 2

    from elevenlabs_tts import get_voice_settings

    ok_count = 0
    for index, item in enumerate(manifest, 1):
        output_path = out_dir / item["filename"]
        settings = get_voice_settings(item["voice"])
        print(f"[{index}/{len(manifest)}] {item['character_name']} / {item['voice']} -> {output_path.name}")
        ok, message = _synthesize_sample(
            item["text"],
            output_path,
            voice=item["voice"],
            model=item["model"],
            settings=settings,
        )
        print(f"    {'OK' if ok else 'FAIL'}: {message}")
        ok_count += 1 if ok else 0

    print(f"Generated: {ok_count}/{len(manifest)}")
    return 0 if ok_count == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())

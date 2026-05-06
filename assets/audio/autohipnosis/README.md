# Wellness audio beds

Put curated loopable background tracks here when the music library is ready.
This folder can serve both autohipnosis and long meditation formats.

Expected use:
- Keep files instrumental, calm, and free of sudden changes.
- Prefer loop-safe WAV or MP3 masters.
- Mix level is intentionally low by default (-28 to -30 dB) so voice remains primary.
- Only use tracks with clear rights for commercial YouTube use.

The production pipeline ignores this folder until a project explicitly enables a
track in `autohipnosis.background_music` or `longMeditation.background_music`.
Long meditation can also use a procedural ambient fallback generated locally by
FFmpeg, with no external music assets.

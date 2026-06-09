import os
import shutil
import subprocess
import time
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from scripts.media_validation import pick_valid_final_video, validate_media_file


TEST_TMP_ROOT = Path(os.environ.get("CONTENT_FACTORY_TEST_TMP", "C:/tmp/content-factory-tests"))
if "CONTENT_FACTORY_TEST_TMP" not in os.environ:
    TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class MediaValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_TMP_ROOT, ignore_errors=True)

    @contextmanager
    def _tempdir(self):
        path = TEST_TMP_ROOT / f"case-{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        try:
            yield str(path)
        finally:
            shutil.rmtree(path, ignore_errors=True)

    def _make_video(self, path: Path, seconds: float = 2.0) -> None:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s=320x180:r=30:d={seconds}",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=44100",
                "-t",
                str(seconds),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])

    def _make_silent_audio_video(self, path: Path, seconds: float = 2.0) -> None:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s=320x180:r=30:d={seconds}",
                "-f",
                "lavfi",
                "-i",
                "anullsrc=channel_layout=mono:sample_rate=44100",
                "-t",
                str(seconds),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])

    def _make_video_without_audio(self, path: Path, seconds: float = 2.0) -> None:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s=320x180:r=30:d={seconds}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])

    def test_empty_mp4_is_invalid(self):
        with self._tempdir() as tmp:
            empty = Path(tmp) / "FINAL_empty.mp4"
            empty.write_bytes(b"")

            ok, duration, error = validate_media_file(empty, min_duration_seconds=1)

            self.assertFalse(ok)
            self.assertEqual(duration, 0.0)
            self.assertIn("empty", error)

    def test_ffprobe_duration_must_meet_minimum(self):
        with self._tempdir() as tmp:
            video = Path(tmp) / "FINAL_short.mp4"
            self._make_video(video, seconds=2)

            ok, duration, error = validate_media_file(video, min_duration_seconds=1)
            self.assertTrue(ok, error)
            self.assertGreaterEqual(duration, 1)

            ok, duration, error = validate_media_file(video, min_duration_seconds=30)
            self.assertFalse(ok)
            self.assertLess(duration, 30)
            self.assertIn("below minimum", error)

    def test_audio_required_rejects_video_only_mp4(self):
        with self._tempdir() as tmp:
            video = Path(tmp) / "FINAL_no_audio.mp4"
            self._make_video_without_audio(video, seconds=2)

            ok, duration, error = validate_media_file(
                video,
                min_duration_seconds=1,
                require_audio=True,
            )

            self.assertFalse(ok)
            self.assertGreaterEqual(duration, 1)
            self.assertIn("audio", error)

    def test_audio_required_rejects_extremely_low_bitrate_audio(self):
        with self._tempdir() as tmp:
            video = Path(tmp) / "FINAL_silent_audio.mp4"
            self._make_silent_audio_video(video, seconds=2)

            ok, duration, error = validate_media_file(
                video,
                min_duration_seconds=1,
                require_audio=True,
            )

            self.assertFalse(ok)
            self.assertGreaterEqual(duration, 1)
            self.assertIn("bitrate", error)

    def test_picker_skips_newer_invalid_final(self):
        with self._tempdir() as tmp:
            folder = Path(tmp)
            valid = folder / "FINAL_podcast_valid.mp4"
            self._make_video(valid, seconds=2)
            time.sleep(0.05)
            invalid = folder / "FINAL_SUB_corrupt.mp4"
            invalid.write_bytes(b"not an mp4")

            picked, has_subtitles, invalid_candidates = pick_valid_final_video(
                folder,
                min_duration_seconds=1,
            )

            self.assertEqual(picked, valid)
            self.assertFalse(has_subtitles)
            self.assertEqual(invalid_candidates[0]["name"], invalid.name)

    def test_picker_skips_newer_final_without_audio(self):
        with self._tempdir() as tmp:
            folder = Path(tmp)
            valid = folder / "FINAL_podcast_valid.mp4"
            self._make_video(valid, seconds=2)
            time.sleep(0.05)
            no_audio = folder / "FINAL_SUB_no_audio.mp4"
            self._make_video_without_audio(no_audio, seconds=2)

            picked, has_subtitles, invalid_candidates = pick_valid_final_video(
                folder,
                min_duration_seconds=1,
            )

            self.assertEqual(picked, valid)
            self.assertFalse(has_subtitles)
            self.assertEqual(invalid_candidates[0]["name"], no_audio.name)
            self.assertIn("audio", invalid_candidates[0]["error"])


if __name__ == "__main__":
    unittest.main()

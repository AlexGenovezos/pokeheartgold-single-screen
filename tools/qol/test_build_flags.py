"""Exercise the real Makefile rules that invalidate objects on flag changes."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BuildFlagTests(unittest.TestCase):
    def test_flags_rebuild_once_and_identical_invocations_reuse_the_object(self):
        source = (ROOT / "Makefile").read_text()
        begin = "# BEGIN GAME DEFINE TRACKING\n"
        end = "# END GAME DEFINE TRACKING\n"
        self.assertIn(begin, source)
        rules = source.split(begin, 1)[1].split(end, 1)[0]
        self.assertIn("$(ALL_GAME_OBJS): | files_for_compile", source)
        make = shutil.which("gmake") or shutil.which("make")
        self.assertIsNotNone(make)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "build").mkdir()
            (root / "source.c").write_text("source\n")
            (root / "Makefile").write_text(
                "BUILD_DIR := build\nALL_GAME_OBJS := build/game.o\n"
                "DEFINES = $(CLI_DEFINES)\nall: $(ALL_GAME_OBJS)\n"
                + rules + "\n$(ALL_GAME_OBJS): source.c | files_for_compile\n"
                "\t@echo compiled >> count\n\t@touch $@\n"
                "files_for_compile:\n\t@:\n")
            for flag, expected in (("-DQOL_MODS=0", 1), ("-DQOL_MODS=0", 1),
                                   ("-DQOL_MODS=1", 2), ("-DQOL_MODS=1", 2)):
                run = subprocess.run([make, "--no-print-directory", "all", f"CLI_DEFINES={flag}"],
                                     cwd=root, text=True, capture_output=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(len((root / "count").read_text().splitlines()), expected)
                self.assertEqual((root / "build/game-defines.txt").read_text().strip(), flag)

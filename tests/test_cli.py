"""End-to-end CLI tests (local server only)."""

import io
import json
import pathlib
import unittest
from contextlib import redirect_stdout

from _server import start_server
from factfence.cli import main

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class CliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.port = start_server(FIXTURES)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def run_cli(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_clean_file_exits_zero(self):
        md = FIXTURES / "clean.md"
        md.write_text(f"Saw 73% here (http://127.0.0.1:{self.port}/source-a.html).\n")
        try:
            code, out = self.run_cli(["--no-color", str(md)])
        finally:
            md.unlink()
        self.assertEqual(code, 0)
        self.assertIn("SUPPORTED", out)

    def test_problems_exit_one(self):
        md = FIXTURES / "dirty.md"
        md.write_text("Saw 99.9% somewhere, trust me.\n")
        try:
            code, out = self.run_cli(["--no-color", "--quiet", str(md)])
        finally:
            md.unlink()
        self.assertEqual(code, 1)
        self.assertIn("1 need", out)

    def test_json_output(self):
        md = FIXTURES / "dirty2.md"
        md.write_text("Saw 42% somewhere, trust me.\n")
        try:
            code, out = self.run_cli(["--json", str(md)])
        finally:
            md.unlink()
        payload = json.loads(out)
        self.assertEqual(payload["summary"]["needs_review"], 1)
        self.assertEqual(payload["claims"][0]["verdict"], "UNCITED")

    def test_no_claims_exits_zero(self):
        code, out = self.run_cli(["--no-color", "--text", "Just a calm sentence."])
        self.assertEqual(code, 0)
        self.assertIn("No checkable claims", out)

    def test_missing_file_exits_two(self):
        code, _ = self.run_cli([str(FIXTURES / "nope.md")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

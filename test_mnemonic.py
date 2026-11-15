import getpass
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch
import warnings

import mnemonic


ROOT = Path(__file__).parent
OS_ENTROPY = bytes(range(32))
ROLLS = "655152231316521321611331544441236164664431121534415633526456254462245546236542364246312613322234612"
ELECTRUM_VECTORS = {
    (50, "segwit"): "wing quick glass soon way genre quiz scale ankle pole dutch decorate session",
    (50, "standard"): "seven talent indicate ordinary sound choice air raise damp sight broccoli mind twelve",
    (99, "segwit"): (
        "olive october cheap timber rifle drop idle order item coin then hill loud drift seed club share "
        "mansion deal toast visa neutral bleak naive economy"
    ),
    (99, "standard"): (
        "modify humble festival battle butter stay garment neglect tribe music upon stone mandate world "
        "regular royal endless amazing avocado rifle aisle scheme practice gown path"
    ),
}


class TestMnemonic(unittest.TestCase):
    def test_help_entropy(self) -> None:
        """Help distinguishes the supported roll counts, input entropy and output length."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "mnemonic.py"), "--help"],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        text = " ".join(result.stdout.split())
        for expected in (
            "fair, independent, private", "50 digits for about 129.25 input bits",
            "128-bit BIP39 value (12 words)", "99 digits for about 255.91 input bits",
            "256-bit BIP39 value (24 words)", "99 rolls are slightly below 256 bits",
            "32-byte OS randomness is mixed in by default",
        ):
            self.assertIn(expected, text)

    @staticmethod
    def run_prompt_cli(arguments: list[str], rolls: str, value: str) -> subprocess.CompletedProcess[str]:
        # Simulate only terminal input; keep parsing, validation and output real.
        # Test inputs travel over stdin rather than appearing in process arguments.
        launcher = (
            "import getpass, io, json, runpy, sys\n"
            "data = json.load(sys.stdin)\n"
            "sys.stdin = io.StringIO(data['rolls'])\n"
            "getpass.getpass = lambda prompt: data['extra']\n"
            "path = sys.argv.pop(1)\n"
            "runpy.run_path(path, run_name='__main__')\n"
        )
        return subprocess.run(
            [sys.executable, "-c", launcher, str(ROOT / "mnemonic.py"), "--extra-entropy", *arguments],
            input=json.dumps({"rolls": rolls, "extra": value}), text=True, capture_output=True, encoding="utf-8",
            env=os.environ | {"PYTHONIOENCODING": "ascii"}, timeout=30,
        )

    def test_dice_vectors(self) -> None:
        """Published SeedSigner vectors pin the digit encoding and truncation."""
        expected = {
            50: "hole luggage safe present express tragic orbit shed switch metal identify path",
            99: (
                "eyebrow obvious such suggest poet seven breeze blame virtual frown dynamic donor "
                "harsh pigeon express broccoli easy apology scatter force recipe shadow claim radio"
            ),
        }
        for count, phrase in expected.items():
            with self.subTest(count=count):
                self.assertEqual(mnemonic.bip39_mnemonic(mnemonic.dice_entropy(ROLLS[:count]), "english"), phrase)

    def test_bip39_vectors(self) -> None:
        """Upstream Trezor vectors cover every language at both supported lengths."""
        vectors = json.loads((ROOT / "bip39_vectors.json").read_text())
        self.assertEqual(set(vectors), set(mnemonic.WORDLISTS))
        for language, cases in vectors.items():
            for entropy, expected in cases:
                with self.subTest(language=language, entropy=entropy):
                    self.assertEqual(mnemonic.bip39_mnemonic(bytes.fromhex(entropy), language), expected)

    def test_invalid_rolls(self) -> None:
        """Reject malformed input rather than silently hashing or filtering it."""
        for rolls in ("", "1" * 49, "1" * 51, "1" * 98, "1" * 100, "0" * 50,
                      "7" * 50, "１" * 50, "1" * 49 + " ", "1" * 49 + "\n"):
            with self.subTest(rolls=rolls):
                with self.assertRaises(ValueError):
                    mnemonic.dice_entropy(rolls)

    def test_electrum_vectors(self) -> None:
        """Pin the first accepted candidate, not just any valid Electrum phrase."""
        for (count, seed_type), expected in ELECTRUM_VECTORS.items():
            with self.subTest(count=count, seed_type=seed_type):
                entropy = mnemonic.dice_entropy(ROLLS[:count])
                self.assertEqual(mnemonic.electrum_mnemonic(entropy, seed_type, "english"), expected)
                self.assertEqual(len(expected.split()), 13 if count == 50 else 25)

    def test_candidate_encoding(self) -> None:
        """Independently specify bytes, bit direction and leading zero word padding."""
        words = mnemonic.WORDLISTS["english"]
        for size in (16, 32):
            for seed_type in ("standard", "segwit"):
                for counter in (0, 1, 256, 2**64 - 1):
                    payload = (
                        b"dice-mnemonic/electrum/v1\0" + seed_type.encode() + b"\0"
                        + bytes(size) + counter.to_bytes(8, "big")
                    )
                    bits = "".join(f"{byte:08b}" for byte in hashlib.sha512(payload).digest())
                    length = 143 if size == 16 else 275
                    expected = " ".join(words[int(bits[i:i + 11], 2)] for i in range(0, length, 11))
                    self.assertEqual(mnemonic.electrum_candidate(bytes(size), seed_type, counter, "english"), expected)

    def test_version_check(self) -> None:
        """Accept the intended version and reject the other version and invalid phrases."""
        for (_, seed_type), phrase in ELECTRUM_VECTORS.items():
            digest = hmac.new(b"Seed version", phrase.encode(), hashlib.sha512).hexdigest()
            self.assertTrue(digest.startswith("100" if seed_type == "segwit" else "01"))
            self.assertTrue(mnemonic.electrum_matches(phrase, seed_type))
            other = "standard" if seed_type == "segwit" else "segwit"
            self.assertFalse(mnemonic.electrum_matches(phrase, other))
        self.assertFalse(mnemonic.electrum_matches("abandon " * 12 + "abandon", "segwit"))

    def test_invalid_options(self) -> None:
        for size in (0, 15, 17, 31, 33):
            with self.assertRaises(ValueError):
                mnemonic.bip39_mnemonic(bytes(size), "english")
            with self.assertRaises(ValueError):
                mnemonic.electrum_mnemonic(bytes(size), "segwit", "english")
        with self.assertRaises(ValueError):
            mnemonic.electrum_mnemonic(bytes(16), "2fa", "english")

    def test_normalization(self) -> None:
        cases = {
            "  ÁRBOL\tÉcole  ": "arbol ecole",
            "あいこくしん\u3000あいさつ": "あいこくしんあいさつ",
            "的 一": "的一",
            "가 나": "가나",
            "hello 的 一 world": "hello 的一 world",
            "": "",
        }
        for phrase, expected in cases.items():
            self.assertEqual(mnemonic.normalize_electrum(phrase), expected)

    def test_multilingual_electrum(self) -> None:
        """Externally verified fixtures pin each language, type and input length."""
        vectors = json.loads((ROOT / "electrum_vectors.json").read_text())
        self.assertEqual(len(vectors), 40)
        for count, kind, language, expected in vectors:
            with self.subTest(count=count, kind=kind, language=language):
                entropy = mnemonic.dice_entropy(ROLLS[:count])
                self.assertEqual(mnemonic.electrum_mnemonic(entropy, kind, language), expected)
                self.assertEqual(len(expected.split()), 13 if count == 50 else 25)
                self.assertTrue(set(expected.split()) <= set(mnemonic.WORDLISTS[language]))

    def test_cli(self) -> None:
        """The default and explicit selections emit only labeled output, with no partial errors."""
        for flags, expected in (([], ["segwit"]), (["--electrum-type", "standard"], ["standard"]),
                                (["--electrum-type", "standard", "--electrum-type", "segwit",
                                  "--electrum-type", "standard"], ["standard", "segwit"])):
            result = self.run_prompt_cli(flags, ROLLS[:50] + "\n", OS_ENTROPY.hex())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 2 * (2 + len(expected)))
            labels = lines[::2]
            expected_labels = ["entropy/extra", "bip39/english"] + [f"electrum/{kind}/english" for kind in expected]
            self.assertEqual(labels, expected_labels)
            self.assertEqual(lines[1], OS_ENTROPY.hex())
        result = subprocess.run(
            [sys.executable, str(ROOT / "mnemonic.py")], input="123\n", text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("expected exactly 50 or 99", result.stderr)

    def test_cli_language(self) -> None:
        """Language selection controls both phrases derived from the mixed entropy."""
        entropy = bytes.fromhex("23a364918d4a9ea38f9b571edb6bc427")
        for language in mnemonic.WORDLISTS:
            result = self.run_prompt_cli(["--language", language], ROLLS[:50] + "\n", OS_ENTROPY.hex())
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(result.stdout.splitlines(), [
                "entropy/extra", OS_ENTROPY.hex(),
                f"bip39/{language}", mnemonic.bip39_mnemonic(entropy, language),
                f"electrum/segwit/{language}", mnemonic.electrum_mnemonic(entropy, "segwit", language),
            ])
        result = subprocess.run(
            [sys.executable, str(ROOT / "mnemonic.py"), "--language", "invalid"],
            input=ROLLS[:50], text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid choice", result.stderr)

    def test_mixed_vectors(self) -> None:
        """Pin the domain, concatenation order and truncation for both dice lengths."""
        expected = {
            50: "23a364918d4a9ea38f9b571edb6bc427",
            99: "9a5f395639028e54ff290c814b753b495a729d05350970998d984bf0a65936ca",
        }
        for count, value in expected.items():
            dice = mnemonic.dice_entropy(ROLLS[:count])
            self.assertEqual(mnemonic.mix_entropy(dice, OS_ENTROPY).hex(), value)
        for dice_size, os_size in ((15, 32), (16, 31), (32, 33)):
            with self.assertRaises(ValueError):
                mnemonic.mix_entropy(bytes(dice_size), bytes(os_size))

    @patch("mnemonic.secrets.token_bytes")
    def test_os_source(self, random_bytes: MagicMock) -> None:
        """Draw 32 CSPRNG bytes only when the caller has not supplied a value."""
        random_bytes.return_value = OS_ENTROPY
        self.assertEqual(mnemonic.get_os_entropy(None), OS_ENTROPY)
        random_bytes.assert_called_once_with(32)
        random_bytes.reset_mock()
        self.assertEqual(mnemonic.get_os_entropy(bytes(32)), bytes(32))
        random_bytes.assert_not_called()
        random_bytes.side_effect = OSError("RNG unavailable")
        with self.assertRaises(OSError):
            mnemonic.get_os_entropy(None)

    def test_os_replay(self) -> None:
        """The reported source exactly reproduces an initially OS-random run."""
        command = [sys.executable, str(ROOT / "mnemonic.py")]
        for count in (50, 99):
            initial = subprocess.run(command, input=ROLLS[:count], text=True, capture_output=True)
            self.assertEqual(initial.returncode, 0, initial.stderr)
            lines = initial.stdout.splitlines()
            self.assertEqual(lines[0], "entropy/extra")
            self.assertEqual(len(bytes.fromhex(lines[1])), 32)
            replay = self.run_prompt_cli([], ROLLS[:count], lines[1])
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertEqual(replay.stdout, initial.stdout)
            self.assertEqual(replay.stderr, "")

    def test_prompt_validation(self) -> None:
        for value in ("", "00" * 31, "00" * 33, "gg" * 32, "  " * 32):
            result = self.run_prompt_cli([], ROLLS[:50], value)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("exactly 64 hexadecimal", result.stderr)
        self.assertEqual(mnemonic.parse_os_entropy(OS_ENTROPY.hex().upper()), OS_ENTROPY)

    def test_cli_rejects_secret_argument(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "mnemonic.py"), "--extra-entropy", OS_ENTROPY.hex()],
            input=ROLLS[:50], text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("unrecognized arguments", result.stderr)

    @staticmethod
    def visible_fallback(_prompt: str) -> str:
        warnings.warn("Can not control echo on the terminal.", getpass.GetPassWarning)
        return OS_ENTROPY.hex()

    @patch("mnemonic.getpass.getpass")
    def test_prompt_requires_hidden_input(self, prompt: MagicMock) -> None:
        """A getpass fallback warning aborts even if other code suppresses warnings."""
        prompt.side_effect = self.visible_fallback
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", getpass.GetPassWarning)
            with self.assertRaisesRegex(RuntimeError, "interactive terminal"):
                mnemonic.prompt_extra_entropy()

    @patch("mnemonic.getpass.getpass", side_effect=EOFError)
    def test_prompt_eof(self, _prompt: MagicMock) -> None:
        with self.assertRaisesRegex(RuntimeError, "interactive terminal"):
            mnemonic.prompt_extra_entropy()

    @unittest.skipUnless(os.name == "posix", "requires a POSIX session without a controlling terminal")
    def test_no_terminal(self) -> None:
        """Redirected dice input must never become a visible fallback for secrets."""
        result = subprocess.run(
            [sys.executable, str(ROOT / "mnemonic.py"), "--extra-entropy"],
            input=ROLLS[:50], text=True, capture_output=True, start_new_session=True, timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("hidden entropy input requires an interactive terminal", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("Password input may be echoed", result.stderr)


if __name__ == "__main__":
    unittest.main()

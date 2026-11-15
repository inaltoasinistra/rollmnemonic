# Rollmnemonic

`mnemonic.py` is a self-contained Python 3.10+ CLI combining physical dice with OS cryptographic randomness.
Copy that file alone to run it;
there are no third-party dependencies, external data files or runtime network requests.

## Usage

Provide exactly 50 or 99 ASCII dice digits (`1`–`6`) on standard input, without spaces.
The tool reads until EOF. With terminal input, finish with Ctrl-D on Unix or Ctrl-Z then Enter on Windows.

```bash
python3 mnemonic.py < rolls.txt
python3 mnemonic.py --language italian < rolls.txt
python3 mnemonic.py --electrum-type standard < rolls.txt
python3 mnemonic.py --electrum-type segwit --electrum-type standard < rolls.txt
```

Every run prints the 32-byte extra contribution as hex under `entropy/extra`, followed by BIP39 and the requested
Electrum types in the selected language. Each identifier occupies its own line, followed by its value on the next.
English and SegWit are the defaults (six output lines).
Repeated types are deduplicated in request order.
Use `--language` with a BIP39 list name: `chinese_simplified`, `chinese_traditional`, `czech`, `english`,
`french`, `italian`, `japanese`, `korean`, `portuguese`, or `spanish`.
There is no progress output; errors go to stderr with a nonzero exit status.
Mnemonic output is always UTF-8, including when redirected on Windows.
Rolls, input files and output phrases are wallet secrets. Use public test inputs for experimentation.

Fresh OS randomness is obtained through Python's `secrets.token_bytes(32)` on every normal run.
Failures abort generation; there is no fallback to a weaker generator.
To reproduce a run, use `--extra-entropy` without a value, then enter the printed contribution
(exactly 64 hex characters) at the hidden terminal prompt:

```bash
python3 mnemonic.py --extra-entropy --language italian < rolls.txt
```

The prompt reads from the terminal while dice input remains on stdin. The value is not echoed or passed as a
command-line argument. If hidden terminal input is unavailable, the tool fails instead of reading visibly.
The same rolls, OS contribution, language and Electrum type reproduce the same output.
An explicitly supplied contribution is used as-is; its encoding is validated, not its randomness.
Treat the printed contribution as secret: revealing it removes its protection against someone who can guess
the dice. It is sufficient to keep the usual mnemonic backup for wallet recovery; replay additionally requires
both original inputs. The contribution is still printed in the output, so captured output remains sensitive.

Different languages and formats create different wallets, not equivalent backups.
All outputs derive from the same secret input and are not independent secrets suitable for separate multisig signers.
Wallet support for BIP39 languages varies. This tool generates mnemonic phrases, not addresses or binary wallet seeds.

## Deterministic specification, version 1

### BIP39

Hash the ASCII dice digits with SHA-256. For 50 rolls use the first 16 digest bytes;
for 99 rolls use all 32 bytes. This first stage matches the Coldcard/SeedSigner dice-only convention.

Then compute `SHA256(b"dice-mnemonic/mixed/v1\x00" || dice_entropy || os_entropy)`.
The OS contribution is exactly 32 bytes. Truncate the digest to 16 bytes for 50 rolls, or keep all 32 for 99 rolls.
Append the BIP39 checksum to this mixed entropy and encode with the selected official ordered wordlist.
This gives 12 or 24 words. Final phrases differ from dice-only tools because they include the second source.
Even an all-zero explicit OS contribution uses this mixed construction; it does not select a dice-only mode.
Japanese output uses ideographic spaces; wordlists retain their NFKD spelling.

### Electrum

Start with those same 16/32 mixed entropy bytes. For counters starting at zero:

1. Concatenate `b"dice-mnemonic/electrum/v1\x00"`, the ASCII type (`segwit` or `standard`),
   a zero byte, the entropy bytes, and the unsigned counter encoded as eight big-endian bytes.
2. SHA-512 the concatenated bytes.
3. Take the leading 143 bits for a 16-byte input, or 275 bits for a 32-byte input.
4. Split those bits left-to-right into 11-bit indices into the selected BIP39 wordlist.
   Keep leading zero indices. Join the resulting 13/25 words with single spaces (ideographic for Japanese).
5. Normalize using Electrum's rules: NFKD, lowercase, remove combining accents, collapse whitespace,
   and remove spaces between characters in Electrum's CJK intervals.
6. HMAC-SHA512 the UTF-8 normalized phrase with key `b"Seed version"`. Accept the first candidate whose hex digest
   starts with `100` for SegWit or `01` for Standard. Otherwise increment the counter and repeat.

Exhausting the 64-bit counter is an error; it never wraps. The counter adds no randomness.
The candidate encoding is this tool's convention, not Electrum's built-in random seed generator.
The resulting phrases follow Electrum's native seed-version rules.

Each language starts its own search at counter zero. Candidate indices are shared across languages,
but the accepted counters generally differ because version checks hash the normalized text.
The displayed phrases retain their wordlist spelling; normalization is only used for Electrum's hash.
Their 13/25-word lengths exclude BIP39 checksum-valid phrases and legacy Electrum seeds,
avoiding ambiguous recovery classification.
TrustedCoin 2FA types are not supported.

Electrum's version check does not depend on a wordlist, so its native recovery can recognize these phrases
even for languages not offered by its built-in generator. These are the ten BIP39 lists, not Electrum's
own language-specific lists (its Portuguese list, for example, differs).

Those lengths provide sufficient candidate-space capacity after version filtering: approximately
131/263 bits for SegWit. This is not a proof of an injective mapping or exact entropy preservation.
Under the hash assumptions and correct execution, one sufficiently unpredictable, secret input can protect
against a weak other source. This is entropy mixing, not Trezor's two-device commitment/audit protocol:
this process knows both inputs and every resulting mnemonic.
99 fair independent rolls supply approximately 255.91 bits, not exactly 256.

## Sources and verification

- BIP39 wordlists: `bitcoin/bips`, commit `b34d9f751791d4feb22feff4f2ed00bcac83961b`, directory `bip-0039`.
  The module embeds the ordered lists, source-file SHA-256 hashes, attribution and MIT license.
- Electrum acceptance rules: `spesmilo/electrum`, commit
  `b5b81ab344f39cdeb00ba77c875a4b1a14097469`, `electrum/mnemonic.py` and `electrum/version.py`.
- `bip39_vectors.json` contains the entropy/phrase pairs from Trezor's `python-mnemonic/vectors.json`
  at commit `b57a5ad77a981e743f4167ab2f7927a55c1e82a8`, for the supported entropy lengths and official BIP39
  languages. It is test data, not a runtime dependency. See `TEST-DATA-LICENSE` for its MIT license.
- Dice reference vectors: SeedSigner's `docs/dice_verification.md`.
- `electrum_vectors.json`: local deterministic outputs independently checked with the Electrum source above.
  These exercise the Electrum stage directly with the original dice-derived bytes; CLI runs now supply mixed bytes.

Run the dependency-free regression suite:

```bash
python3 -m unittest -v
```

Tests cover all languages, both entropy lengths, malformed input, deterministic Electrum search vectors,
candidate serialization, version checks, OS mixing, replay, and CLI output.
Cross-checking one vector is evidence of agreement,
not proof of correctness for every possible input.

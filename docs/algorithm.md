# Algorithm specification

This describes Rollmnemonic's deterministic construction, version 1.
The same dice results, extra entropy, language and Electrum type produce identical output.

## Inputs and output

Supply exactly 50 or 99 ASCII dice digits (`1`–`6`) on stdin, without spaces. A trailing newline is accepted.
The tool reads until EOF: Ctrl-D on Unix, or Ctrl-Z then Enter on Windows when entering rolls directly.

The extra entropy is 32 bytes from Python's `secrets.token_bytes(32)` unless `--extra-entropy` is selected.
That flag opens a hidden terminal prompt for exactly 64 hexadecimal characters while dice input remains on stdin.
Failure to obtain OS randomness or hidden terminal input stops generation; there is no weaker fallback.
An explicitly supplied value is validated for encoding and length, not randomness.

Output uses UTF-8 and alternates identifiers with values on the following line:
extra entropy, BIP39, then the requested Electrum types. Repeated types are deduplicated in request order.
Errors go to stderr with a nonzero exit status; no progress is printed.

## BIP39

1. SHA-256 the ASCII dice digits. Keep the first 16 bytes for 50 rolls, or all 32 bytes for 99 rolls.
   This first stage matches the Coldcard/SeedSigner dice-only convention.
2. Compute `SHA256(b"dice-mnemonic/mixed/v1\x00" || dice_entropy || extra_entropy)`.
   Keep the first 16 bytes for 50 rolls, or all 32 bytes for 99 rolls.
3. Append the BIP39 checksum and encode with the selected official ordered wordlist, giving 12 or 24 words.

Final phrases differ from dice-only tools because they include the second source.
Even an all-zero extra contribution uses the mixed construction; it does not select a dice-only mode.
Japanese output uses ideographic spaces; wordlists retain their NFKD spelling.

## Electrum

Start with the same 16/32 mixed entropy bytes. For counters starting at zero:

1. Concatenate `b"dice-mnemonic/electrum/v1\x00"`, the ASCII type (`segwit` or `standard`),
   a zero byte, the mixed entropy bytes, and the unsigned counter encoded as eight big-endian bytes.
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

Each language starts its search at counter zero. Candidate indices are shared across languages,
but accepted counters generally differ because version checks hash the normalized text.
Displayed phrases retain their wordlist spelling; normalization is only used for Electrum's hash.
The 13/25-word lengths exclude BIP39 checksum-valid phrases and legacy Electrum seeds,
avoiding ambiguous recovery classification. TrustedCoin 2FA types are not supported.

Electrum's version check does not depend on a wordlist, so native recovery can recognize these phrases
even for languages not offered by its built-in generator. These are the ten BIP39 lists, not Electrum's
own language-specific lists (its Portuguese list, for example, differs).

## Entropy and recovery

Fair, independent, private six-sided rolls supply approximately 2.585 bits each:
50 rolls provide about 129.25 bits; 99 provide about 255.91 bits, not exactly 256.
The Electrum lengths allow approximately 131/263 bits of candidate-space capacity after SegWit version filtering.
This is not a proof of an injective mapping or exact entropy preservation.

Under the hash assumptions and correct execution, one sufficiently unpredictable, secret input can protect
against a weak other source. This is entropy mixing, not Trezor's two-device commitment/audit protocol:
this process knows both inputs and every resulting mnemonic.

Keep rolls, input files, the extra contribution and output phrases private. Revealing the extra contribution
removes its protection against someone who can guess the dice. The usual mnemonic backup is sufficient for
wallet recovery; reproducing the generation process additionally requires both original inputs.

Different languages and formats create different wallets, not equivalent backups. All outputs derive from
the same secret input and are not independent secrets suitable for separate multisig signers.
Wallet support for BIP39 languages varies. This tool generates phrases, not addresses or binary wallet seeds.

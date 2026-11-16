# Sources and verification

## Run the tests

From the repository root, run the dependency-free suite:

```bash
python3 -m unittest -v
```

Tests cover all languages, both entropy lengths, malformed input, deterministic Electrum search vectors,
candidate serialization, version checks, OS mixing, hidden input, replay, and CLI output.
Cross-checking vectors establishes agreement for those inputs, not proof of correctness for every possible input.

## Reference sources

- **BIP39 wordlists:** `bitcoin/bips`, commit `b34d9f751791d4feb22feff4f2ed00bcac83961b`, directory `bip-0039`.
  The module embeds the ordered lists, source-file SHA-256 hashes, attribution and MIT license.
- **Electrum acceptance rules:** `spesmilo/electrum`, commit
  `b5b81ab344f39cdeb00ba77c875a4b1a14097469`, `electrum/mnemonic.py` and `electrum/version.py`.
- **BIP39 vectors:** [`bip39_vectors.json`](../bip39_vectors.json) contains entropy/phrase pairs from
  Trezor's `python-mnemonic/vectors.json` at commit `b57a5ad77a981e743f4167ab2f7927a55c1e82a8`,
  for the supported entropy lengths and official BIP39 languages.
  See [TEST-DATA-LICENSE](../TEST-DATA-LICENSE) for the MIT license.
- **Dice reference vectors:** SeedSigner's `docs/dice_verification.md`.
- **Electrum vectors:** [`electrum_vectors.json`](../electrum_vectors.json) contains deterministic outputs
  independently checked with the Electrum source above. These exercise the Electrum stage directly with
  the original dice-derived bytes; CLI runs supply mixed bytes.

The fixture files are test data, not runtime dependencies. Only `mnemonic.py` is needed to run the tool.
See the [algorithm specification](algorithm.md) for the exact transformations to reproduce independently.

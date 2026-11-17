# Rollmnemonic

Generate BIP39 and Electrum mnemonics from physical dice rolls and OS randomness.
A single Python 3.10+ script, with no dependencies. Supports all ten BIP39 languages.

## Usage

Save your dice results in `rolls.txt`: digits `1`–`6`, in order, without spaces.

- **50 rolls:** 12-word BIP39 and 13-word Electrum phrases.
- **99 rolls:** 24-word BIP39 and 25-word Electrum phrases.

```bash
python3 mnemonic.py < rolls.txt
python3 mnemonic.py --language italian < rolls.txt
python3 mnemonic.py --language english --language italian < rolls.txt
python3 mnemonic.py --electrum-type standard < rolls.txt
```

Defaults to English and Electrum SegWit. Each run prints YAML with `entropy.rolls`, `entropy.extra` and a
`wallets` list. For example:

```yaml
entropy:
  rolls: "123456..."
  extra: "0123456789abcdef..."
wallets:
  - format: bip39
    language: english
    mnemonic: abandon ability ...
  - format: electrum
    seed_type: segwit
    language: english
    mnemonic: wing quick ...
```

Repeat `--electrum-type` to include both `segwit` and `standard` in the list.
Repeat `--language` to generate wallets in multiple languages. Each requested language has a BIP39 entry
followed by its Electrum entries; repeated languages and Electrum types are included only once.

See `python3 mnemonic.py --help` for languages, options and dice-entropy guidance.

## Reproduce a result

Fresh OS randomness makes each normal run different. To reproduce a previous result, use the same dice input
and enter its printed `entropy.extra` value at the hidden prompt:

```bash
python3 mnemonic.py --extra-entropy < rolls.txt
```

Use the same languages and Electrum types too. The extra value is entered privately, not as a command-line argument.

**Keep your rolls and all output private.** Different formats and languages represent different wallets,
not interchangeable backups.

## Further reading

- [Algorithm specification](docs/algorithm.md)
- [Sources and verification](docs/verification.md)

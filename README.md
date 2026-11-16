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
python3 mnemonic.py --electrum-type standard < rolls.txt
```

Defaults to English and Electrum SegWit. Each run prints the extra entropy, a BIP39 phrase and an Electrum phrase,
each preceded by its identifier. Repeat `--electrum-type` to include both `segwit` and `standard`.

See `python3 mnemonic.py --help` for languages, options and dice-entropy guidance.

## Reproduce a result

Fresh OS randomness makes each normal run different. To reproduce a previous result, use the same dice input
and enter its printed `entropy/extra` value at the hidden prompt:

```bash
python3 mnemonic.py --extra-entropy < rolls.txt
```

Use the same language and Electrum type too. The extra value is entered privately, not as a command-line argument.

**Keep your rolls and all output private.** Different formats and languages represent different wallets,
not interchangeable backups.

## Further reading

- [Algorithm specification](docs/algorithm.md)
- [Sources and verification](docs/verification.md)

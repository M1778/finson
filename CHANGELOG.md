# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-10-19

### Added
- Initial release: JSON parser (string to `JsonValue` tree), serializer
  (compact and pretty-printed), and programmatic value builders.
- Recoverable parse errors with 1-based line/column and message (`ParseResult`).
- Full RFC 8259 string escapes including `\uXXXX` and surrogate pairs.
- Duplicate object keys: last wins.
- `examples/basic.fin`, test suite in `tests/test_lib.fin`, GitHub Actions CI,
  `finn.toml` manifest, MIT license.

### Verification
- ✅ VERIFIED 2026-10-19: built with `finc 0.4.0` (contract 3); the full test
  suite passes (`finc -I src tests/test_lib.fin -o test_finson && ./test_finson`,
  ~50 assertions) and `examples/basic.fin` runs correctly.

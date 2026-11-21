# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `finn add` produced a package no consumer could import: `import ... from
  finson::fin` failed with `module not found: finson`, because the module lived
  under `src/` and `finn` puts the package root on the compiler's search path.
  The module is now `finson.fin` at the package root. Verified end to end from a
  fresh consumer project.
- `json_object_get`, `json_object_set` and `json_object_has` segfaulted on a null
  key, and `json_str` segfaulted on a null string, because the key reached
  `strcmp` and the string reached `strlen`. All four now `blame` with a named
  message. `tests/probe_failures.py` requires the named abort and fails on
  `SIGSEGV`.
- `json_free` recursed once per nesting level. A deep tree built through the
  builder API — which has no depth ceiling — crashed inside its own free (about
  300k levels on an 8 MiB stack, far fewer on Windows' 1 MiB). Freeing now uses an
  explicit stack, so it is constant in call depth. Regression: 400k-deep array
  and object trees.

### Added

- `tests/probe_failures.py`: negative tests for the builder diagnostics, which
  `blame` makes impossible to assert in-process.
- Integer-boundary regressions: past 2^53 a JSON number is the nearest double,
  2^64 is exactly representable, and `json_num_int` round-trips `INT_MIN` and
  `INT_MAX`.
- `FINC_VERSION` and `.github/scripts/install_finc.py`: CI installs the pinned
  `finc` release, verifies the archive sha256, and refuses a compiler whose
  `--version` does not report a contract.
- CI jobs for macOS and Windows that compile **and execute** the suite, an
  AddressSanitizer lane on Linux (leak and memory-error checking, including the
  differential suite), an `-O2` lane, and the differential lane.
- `scripts/fin_header.py`: applies and checks the project's SPDX header. Every
  source file now carries one.

### Changed

- README rewritten to state what the library does and does not do, the verified
  compiler version, the budgets and their hard ceilings, the crash-versus-
  diagnostic boundary, and the platforms CI actually runs on. Removed the
  unprovable "leak-checked" and `finc 0.4.0` claims and the claim that CI covered
  three platforms when it covered one.
- `examples/basic.fin` checks for absent keys and a null serialization result
  instead of dereferencing them, and no longer claims a `finc 0.4.0` limitation
  that current `finc` does not have.
- `finn.toml` no longer sets an `entrypoint` this library cannot satisfy, and its
  `test` script no longer passes a stale `-I src`.

### Removed

- `exports.fin`: not valid Fin (`export * from` is a syntax error) and unreferenced.
- The committed x86-64 Linux executable that had been checked in as
  `example_basic`; build outputs are ignored instead.

## [0.1.0] - 2026-10-19

### Added

- Initial release: JSON parser (string to `JsonValue` tree), serializer
  (compact and pretty-printed), and programmatic value builders.
- Recoverable parse errors with 1-based line/column and message (`ParseResult`).
- Full RFC 8259 string escapes including `\uXXXX` and surrogate pairs.
- Duplicate object keys: last wins; strict mode rejects them.
- Configurable budgets on input bytes, depth, nodes, container width and output.
- `examples/basic.fin`, test suite in `tests/test_lib.fin`, `finn.toml`
  manifest, MIT license.

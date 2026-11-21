# =============================================================================
# Fin Programming Language
#
# Made with ❤️ for someone special.
#
# This project is genuinely built on love and dedication, a way to express your love can be done through Fin.
# Fin is a semi-object-orientated programming language that specialized in control, giving so much control to the user while asking for the bare minimum.
# Fin is the name of the Angel from BlackNightmare-Stories not yet published.
# “Love is the reason this project exists”
# -----------------------------------------------------------------------------
# Author: M1778
# Repository: https://github.com/M1778/finson
# Profile: https://github.com/M1778M/
# -----------------------------------------------------------------------------
# Copyright (C) 2027 M1778
#
# This file is part of finson, a project for the Fin Programming Language.
#
# Licensed under the MIT License. See LICENSE in the repository root.
#
# SPDX-License-Identifier: MIT
# =============================================================================

"""Negative tests for finson's builder diagnostics.

`blame` aborts the process, so these cannot live in tests/test_lib.fin's normal
assertion flow. Each case runs the compiled suite in a probe mode and requires:

  * a nonzero exit -- the guard fired, and
  * the expected message on stderr -- the right guard fired,
  * never a signal (segfault), which is what the pre-guard code did.

Run: python3 -I tests/probe_failures.py ./test_finson
"""

import os
import subprocess
import sys

# mode -> the message the guard must print on stderr.
CASES = {
    "null_key_get": "json_object_get: null key",
    "null_key_set": "json_object_set: null key",
    "null_key_has": "json_object_get: null key",
    "null_string": "json_str: null string",
}


def main() -> int:
    exe = os.path.abspath(sys.argv[1])
    failures = []
    for mode, expected in CASES.items():
        env = dict(os.environ, FINSON_PROBE=mode)
        env.pop("FINSON_TEST_LOCALE", None)
        env.pop("FINSON_DIFFERENTIAL", None)
        run = subprocess.run([exe], env=env, capture_output=True, text=True)
        if run.returncode == 0:
            failures.append(f"{mode}: exited 0; the guard did not fire")
            continue
        # `blame` aborts, so SIGABRT (-6) is the expected way to die. Any other
        # signal -- SIGSEGV (-11) above all -- is the crash this guard prevents.
        if run.returncode < 0 and run.returncode != -6:
            failures.append(
                f"{mode}: died on signal {-run.returncode} instead of blaming; "
                "a null key or string is being read"
            )
            continue
        if expected not in run.stderr:
            failures.append(
                f"{mode}: blamed without the expected message {expected!r}; "
                f"stderr was {run.stderr.strip()[:200]!r}"
            )
    if failures:
        print("finson probe failures:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"finson probes: {len(CASES)} builder diagnostics fired as named")
    return 0


if __name__ == "__main__":
    sys.exit(main())

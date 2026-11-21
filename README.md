# finson

JSON parsing and serialization for [Fin](https://github.com/M1778/Fin). Parse JSON
text into a `JsonValue` tree, build values programmatically, and serialize back to
compact or pretty-printed JSON.

finson is written for the path untrusted input takes: it bounds the work a hostile
document can request, rejects malformed input with a positioned error, and never
silently truncates a value it cannot represent.

> **Verification status:** built and executed with `finc 1.0.1` and the published
> `finc 1.0.0` (contract 3) release on Linux. The test suite, a Python differential
> oracle, and AddressSanitizer leak checks pass at `-O0` and `-O2`. CI runs the
> compiled tests and the same differential suite on Linux, macOS and Windows;
> see [Platform support](#platform-support).

## What it does

- RFC 8259 JSON parsing into an owned tree, with recoverable, positioned errors.
- Serialization to compact and pretty-printed JSON.
- Programmatic construction and mutation of values.
- Configurable budgets on input bytes, nesting depth, node count, container
  width, and output bytes.
- Strict UTF-8 validation, surrogate-pair decoding, and finite-double numbers.

## What it does not do

- No JSON5, JSONC, YAML, TOML, or comments. The grammar is RFC 8259 only.
- No streaming or incremental parser. `json_parse` takes a complete document.
- No schema or type validation. It tells you whether the text is JSON, not
  whether it is the JSON you expected.
- No embedded NUL. A Fin `string` is NUL-terminated, so `\u0000` is a diagnosed
  parse error rather than a value silently truncated at the NUL.
- No integer type. Every number is a finite `double`; integers beyond 2^53 lose
  precision, and that is a documented limit rather than a bug.
- No automatic memory management. Every value you create or parse is yours to
  `json_free`.

## Install

Requires the `finn` package manager (https://github.com/M1778/finn) and a
`finc` with a working LLVM backend and a C linker driver.

```sh
finn add https://github.com/M1778/finson
```

The package root carries the module, so `import ... from finson::fin` resolves
once finn has installed it. Without finn, compile with the package root on the
search path:

```sh
finc -I /path/to/finson your_program.fin -o your_program
```

## Complete example

This is `examples/basic.fin`, unchanged. Run it from a checkout with
`finc examples/basic.fin -o example_basic && ./example_basic`.

```fin
import {
    JsonValue, ParseResult,
    json_parse, json_stringify_pretty,
    json_object_get, json_array_get, json_array_len,
    json_object_set, json_str, json_num, json_free_result
} from "../finson.fin";
import { free_str } from strings::std;

fun main() <noret> {
    let doc <string> = "{\"name\": \"finson\", \"stars\": 0, \"tags\": [\"json\", \"fin\"]}";

    let r <ParseResult> = json_parse(doc);
    if (!r.ok) {
        printf("parse failed at %d:%d: %s\n", r.err.line, r.err.col, r.err.message);
        json_free_result(&r);
        return;
    }

    // Accessors return borrowed pointers, and a key that is absent gives null.
    // Check before reading a field: `name.s` on null is not a JSON error.
    let name <&JsonValue> = json_object_get(r.value, "name");
    if (name == null) { printf("missing name\n"); json_free_result(&r); return; }
    printf("name: %s\n", name.s);

    let tags <&JsonValue> = json_object_get(r.value, "tags");
    if (tags != null) {
        printf("tags: %d\n", json_array_len(tags));
        for (let i <int> = 0; i < json_array_len(tags); i++) {
            printf("  - %s\n", json_array_get(tags, i).s);
        }
    }

    // Modify: bump the star count and add a field. json_object_set takes
    // ownership of the value it is given and frees the one it replaces.
    let stars <&JsonValue> = json_object_get(r.value, "stars");
    let next <double> = cast<double>(0);
    if (stars != null) { next = stars.num + cast<double>(1); }
    json_object_set(r.value, "stars", json_num(next));
    json_object_set(r.value, "lang", json_str("fin"));

    let pretty <string> = json_stringify_pretty(r.value, 2);
    if (pretty != null) {
        printf("%s\n", pretty);
        free_str(pretty);
    } else {
        printf("serialization failed\n");
    }

    json_free_result(&r);
}
```

```output
name: finson
tags: 2
  - json
  - fin
{
  "name": "finson",
  "stars": 1,
  "tags": [
    "json",
    "fin"
  ],
  "lang": "fin"
}
```

A program outside this repository imports the installed module instead of the
relative file:

```fin fragment
import {
    JsonValue, ParseResult,
    json_parse, json_object_get, json_free_result
} from finson::fin;

fun main() <noret> {
    let r <ParseResult> = json_parse("{\"name\": \"fin\"}");
    if (!r.ok) {
        printf("parse failed at %d:%d: %s\n", r.err.line, r.err.col, r.err.message);
        json_free_result(&r);
        return;
    }
    let name <&JsonValue> = json_object_get(r.value, "name");
    if (name != null) { printf("%s\n", name.s); }
    json_free_result(&r);
}
```

## API

### Types

| Type | Fields |
| ---- | ------ |
| `JsonValue` | `kind` (`int`: 0 null, 1 bool, 2 number, 3 string, 4 array, 5 object), `b`, `num`, `s` |
| `ParseResult` | `ok`, `value`, `err` |
| `ParseError` | `line`, `col`, `message` — 1-based byte position, owned message |
| `JsonLimits` | `max_bytes`, `max_depth`, `max_nodes`, `max_container`, `max_output`, `reject_duplicates` |
| `StringifyResult` | `ok`, `text`, `message` |

`kind` is a plain `int` rather than an enum because `finc` does not lower
enum-typed struct fields from an imported module. Use `json_kind_name` to turn a
kind into a readable name. The child arrays on `JsonValue` are implementation
storage: use the accessors, not their contents.

### Parsing

```fin
fun json_parse(text: string) <ParseResult>            // duplicate keys: last wins
fun json_parse_strict(text: string) <ParseResult>      // duplicate keys: rejected
fun json_default_limits() <JsonLimits>
fun json_parse_with_limits(text: string, limits: JsonLimits) <ParseResult>
```

Errors are recoverable: check `r.ok`, read `r.err.line`, `r.err.col` and
`r.err.message`, and release with `json_free_result(&r)`. Duplicate comparison in
strict mode happens after escape decoding, so `{"a":1,"\u0061":2}` is a duplicate.

| Field | Default | Accepted range |
| --- | ---: | ---: |
| `max_bytes` | 1,048,576 | 0 – 67,108,864 |
| `max_depth` | 128 | 0 – 256 |
| `max_nodes` | 65,536 | 0 – 1,048,576 |
| `max_container` | 16,384 | 0 – 1,048,576 |
| `max_output` | 8,388,608 | 0 – 67,108,864 |
| `reject_duplicates` | false | boolean |

Zero is a valid budget. Negative values and configurations above the hard
ceiling are rejected with `ok == false`. Depth counts open containers, so a
scalar root has depth zero and `[0]` needs a depth of one. `max_bytes` is checked
before any copying, so an oversized document costs one bounded `strnlen`.

Object lookup and duplicate detection scan linearly per member, which is
quadratic for a wide object. Lower `max_container` if that matters for your
traffic.

A literal NUL byte must be rejected **before** calling `json_parse`: the API takes
a NUL-terminated `string` and cannot see past the first NUL.

### Serialization

```fin
fun json_stringify(v: &JsonValue) <string>                      // null on failure
fun json_stringify_pretty(v: &JsonValue, indent: int) <string>  // null on failure
fun json_stringify_strict(v: &JsonValue) <StringifyResult>
fun json_stringify_with_limits(v: &JsonValue, limits: JsonLimits,
                               pretty: bool, indent: int) <StringifyResult>
fun json_free_stringify_result(r: &StringifyResult) <noret>
```

The compatibility wrappers return freshly allocated text on success — free it
with `strings::std.free_str` — or `null` on failure. They never return partial or
invalid JSON. Nonfinite numbers, invalid UTF-8, a negative or over-budget indent,
and exhausted budgets are all diagnosed, with the reason in `message`.

Serializers enforce the depth, node and container budgets too, so a tree that was
built programmatically past `max_depth` is refused rather than written as
unbounded recursion. Do not pass cycles or shared children to `json_free`; they
are invalid ownership graphs that no budget can make correct.

Strings are escaped per RFC 8259. Finite doubles are written with libc `strtod`
and `%.17g`, so subnormals, negative zero and the extremes survive a round trip.
Decimal output is the shortest exact form `%.17g` gives (`0.4` becomes
`0.40000000000000002`).

JSON output requires a dot-decimal numeric locale. A non-dot locale returns an
explicit error; the library never changes the process or thread locale, so an
application must not call `setlocale` concurrently with JSON work.

### Builders

```fin
fun json_null() <&JsonValue>
fun json_bool(b: bool) <&JsonValue>
fun json_num(n: double) <&JsonValue>
fun json_num_int(n: int) <&JsonValue>
fun json_str(s: string) <&JsonValue>   // copies s; null is refused
fun json_array() <&JsonValue>
fun json_object() <&JsonValue>
```

### Access and mutation

```fin
fun json_array_push(v: &JsonValue, item: &JsonValue) <noret>
fun json_array_len(v: &JsonValue) <int>
fun json_array_get(v: &JsonValue, i: int) <&JsonValue>
fun json_object_set(v: &JsonValue, key: string, item: &JsonValue) <noret>
fun json_object_get(v: &JsonValue, key: string) <&JsonValue>
fun json_object_has(v: &JsonValue, key: string) <bool>
fun json_object_len(v: &JsonValue) <int>
fun json_kind_name(k: int) <string>   // static string; do not free
```

Wrong kind, null value, null key and out-of-bounds index are diagnosed with
`blame`, which aborts the process. That is this language's assertion mechanism:
Fin does not yet recover from `blame`, so these are programmer errors rather than
recoverable ones. Input text is the recoverable surface; check `r.ok`.

### Memory

```fin
fun json_free(v: &JsonValue) <noret>
fun json_free_result(r: &ParseResult) <noret>
```

Every `JsonValue` you create or receive is yours to free exactly once.
`json_array_push` and `json_object_set` take ownership of the value they are
given; replacing a key frees the old value, and setting a key to its current
pointer is a no-op. Accessors return borrowed pointers that you must not free.

Each child must have exactly one owner. Inserting a value into itself or into two
parents is an invalid graph, not a supported alias.

`json_free` walks the tree with an explicit stack instead of recursing, so a
deep tree built through the builder API is freed without exhausting the call
stack. `json_free_result` and `json_free_stringify_result` clear what they freed
and are safe to call twice.

Allocation failure inside Fin's `new` and the standard library remains a runtime
limitation. Budgets bound the work a document can request; they are not a general
out-of-memory recovery API.

## Platform support

Tested and required to pass in CI:

| Platform | Compiler artifact | Tests execute |
| --- | --- | --- |
| Linux x86-64 (glibc) | `finc` release, musl build | yes |
| Linux x86-64 (musl) | `finc` release, musl build | yes |
| macOS 14 (arm64) | `finc` release, darwin build | yes |
| Windows Server 2022 (x86-64, MSVC) | `finc` release, msvc build | yes |

The library depends on the C runtime for `calloc`, `free`, `strtod`, `snprintf`
and `strnlen`. Those are C89/C99 functions available on every target above; no
POSIX-only call is used, so there is no POSIX/Windows split to declare. Building
an executable does need a linker driver: `cc` on Unix and `clang` on Windows, or
whatever `FIN_CC` names.

The AddressSanitizer lane is Linux-only, because that is where the toolchain is
cheap to set up; on other platforms the ordinary build still runs the full suite.

## Development

```sh
finc tests/test_lib.fin -o test_finson && ./test_finson
python3 -I tests/differential.py ./test_finson
python3 -I tests/probe_failures.py ./test_finson
```

The probe script runs the suite in probe modes and requires each builder guard to
abort with its named message; a segfault fails it.

Leak-checked run on Linux:

```sh
finc -O0 -c tests/test_lib.fin -o test_finson.o
cc -fsanitize=address -g test_finson.o -o test_finson_asan
./test_finson_asan
python3 -I tests/differential.py ./test_finson_asan
```

`FINSON_TEST_LOCALE` selects an installed non-dot locale to check the explicit
locale rejection. `python3 scripts/fin_header.py --repo finson --license MIT
--check .` verifies the source headers.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

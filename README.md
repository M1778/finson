# finson

JSON parsing and serialization for [Fin](https://github.com/M1778/Fin). Parse JSON
text into a `JsonValue` tree, build values programmatically, and serialize back to
compact or pretty-printed JSON.

> **Verification status:** built with the frozen `finc 0.4.0` (contract 3)
> toolchain on Linux at `-O0` and `-O2`; native regression and Python differential
> suites pass, including leak-checked repeated parse/serialize/free loops.

## Install

Requires the `finn` package manager (https://github.com/M1778/finn):

```sh
finn add M1778/finson
```

## Quick Example

```fin
import {
    JsonValue, ParseResult,
    json_parse, json_stringify_pretty,
    json_object_get, json_object_set, json_str, json_free_result
} from finson::fin;
import { free_str } from strings::std;

fun main() <noret> {
    let r <ParseResult> = json_parse("{\"name\": \"fin\", \"stars\": 41}");
    if (!r.ok) {
        printf("parse failed at %d:%d: %s\n", r.err.line, r.err.col, r.err.message);
        json_free_result(&r);
        return;
    }
    let name <&JsonValue> = json_object_get(r.value, "name");
    printf("name: %s\n", name.s);

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

## API Reference

### Types

| Type | Description |
| ---- | ----------- |
| `JsonValue` | Tagged JSON value (heap-allocated, owned by caller). `kind` is an `int`: 0=null, 1=bool, 2=number, 3=string, 4=array, 5=object |
| `ParseResult` | `{ ok, value, err }` — result of `json_parse` |
| `ParseError` | `{ line, col, message }` — present when `ok` is false |

> `kind` is a plain `int`, not an enum: finc 0.4.0 does not lower
> enum-typed struct fields or `const` declarations from an imported module.
> Use `json_kind_name()` for a readable name.

### Parsing

```fin
fun json_parse(text: string) <ParseResult> // bounded, duplicate keys: last wins
fun json_parse_strict(text: string) <ParseResult> // bounded, duplicate keys rejected
fun json_default_limits() <JsonLimits>
fun json_parse_with_limits(text: string, limits: JsonLimits) <ParseResult>
```

Parses a complete NUL-terminated JSON document. Errors are recoverable: check
`r.ok`; `r.err` carries 1-based byte `line`/`col` and an owned diagnostic.
Release success or failure with `json_free_result(&r)`. For security-sensitive
claims use `json_parse_strict`: duplicate names are compared after escape decoding
at every nesting level. `json_parse` retains last-wins compatibility.

`JsonLimits` is a value struct with configurable budgets:

| Field | Default | Maximum accepted configuration |
| --- | ---: | ---: |
| `max_bytes` | 1,048,576 | 67,108,864 |
| `max_depth` | 128 | 256 |
| `max_nodes` | 65,536 | 1,048,576 |
| `max_container` | 16,384 | 1,048,576 |
| `max_output` | 8,388,608 | 67,108,864 |
| `reject_duplicates` | false | boolean |

Zero budgets are valid; negatives and configurations above hard ceilings return
errors. Depth counts open containers (a scalar root has depth zero). Nodes count
values, including the root and replaced duplicate values; container budgets count
input members including duplicate names. `max_bytes` is checked before copying
input. `max_output` applies to serialization, not parsing. Serializers also enforce
depth/node/container budgets. Object lookup and duplicate detection remain linear
per member (quadratic for a wide object); lower `max_container` for hostile traffic.

Because Fin strings carry no length, escaped U+0000 is rejected in values and keys
instead of being silently truncated. Callers holding raw bytes must reject literal
NUL **before** converting them to `string`: a NUL-terminated API cannot inspect the
suffix. Invalid UTF-8, unpaired surrogates and overflow to nonfinite doubles are
recoverable errors. Allocation failure in Fin's `new`/stdlib remains a runtime
limitation; budgets bound requested work but are not a general OOM recovery API.

### Serialization

```fin
fun json_stringify(v: &JsonValue) <string> // compact, null on failure
fun json_stringify_pretty(v: &JsonValue, indent: int) <string> // null on failure
fun json_stringify_strict(v: &JsonValue) <StringifyResult>
fun json_stringify_with_limits(v: &JsonValue, limits: JsonLimits,
                              pretty: bool, indent: int) <StringifyResult>
fun json_free_stringify_result(r: &StringifyResult) <noret>
```

`StringifyResult` has `ok`, `text`, and `message`; successful text or failed
message is owned. Release either outcome with `json_free_stringify_result(&r)`.
Compatibility wrappers return freshly allocated text on success (free with
`strings::std.free_str`) or **null** on failure, never partial/invalid JSON.
Invalid UTF-8, nonfinite numbers, negative/over-budget indentation and exhausted
budgets return errors. Programmatically built cycles are rejected by the depth
budget during serialization, but remain invalid ownership graphs: do not pass
cycles or shared children to `json_free`.

Strings are escaped per RFC 8259. Finite doubles use libc `strtod` and `%.17g`:
subnormal values and negative zero survive round trips; integers beyond 2^53 may
lose precision; underflow below representable doubles rounds to zero. Decimal
output can be longer than before (`0.4` may become `0.40000000000000002`).
JSON operations require a **dot-decimal numeric locale** (the process default C
locale works). A non-dot locale returns an explicit error; the library never
changes global or thread locale. Applications must not concurrently call
`setlocale` while using JSON. Native Linux libc ABI is tested; `strnlen` and the
C conversion/formatting functions must be available on other targets.

### Building values

```fin
fun json_null() <&JsonValue>
fun json_bool(b: bool) <&JsonValue>
fun json_num(n: double) <&JsonValue>
fun json_num_int(n: int) <&JsonValue>
fun json_str(s: string) <&JsonValue>   // copies s
fun json_array() <&JsonValue>
fun json_object() <&JsonValue>
```

### Access and mutation

```fin
fun json_array_push(v: &JsonValue, item: &JsonValue) <noret>
fun json_array_len(v: &JsonValue) <int>
fun json_array_get(v: &JsonValue, i: int) <&JsonValue>
fun json_object_set(v: &JsonValue, key: string, item: &JsonValue) <noret>  // insert or replace
fun json_object_get(v: &JsonValue, key: string) <&JsonValue>               // null if missing
fun json_object_has(v: &JsonValue, key: string) <bool>
fun json_object_len(v: &JsonValue) <int>
fun json_kind_name(k: int) <string>  // "null"/"bool"/"number"/"string"/"array"/"object"; static string, do NOT free
```

### Memory

```fin
fun json_free(v: &JsonValue) <noret>          // recursive free of a value tree
fun json_free_result(r: &ParseResult) <noret> // frees whichever side is live
```

Ownership rule: every `JsonValue` you create or receive from `json_parse` is
yours — free it exactly once. `json_object_set` copies keys and takes ownership
of the inserted value; replacing a key frees the old value. `json_object_get`
and `json_array_get` return borrowed pointers (do not free them separately).

`json_array_push` also takes ownership. All children must be distinct allocations
with one owner; inserting a value into itself or into multiple parents is invalid.
Setting an existing key to its current pointer is a no-op. Constructors/accessors
and scalar `kind`/`b`/`num`/`s` fields retain their signatures, but `JsonValue`
storage changed: `items`, `keys`, and `vals` are now explicitly freed arrays with
`count`/`capacity`, not `Collection` pointers. Direct storage access is unsupported;
rebuild consumers and use the accessors. Result cleanup clears owned pointers and
can safely be repeated.

## Supported JSON

- RFC 8259 grammar within documented budgets, excluding U+0000 which cannot be
  represented by this API; strict valid UTF-8 is required.
- Duplicate object keys: last wins by default, rejected by strict mode.
- Numbers are finite `double`; very large integers lose precision past 2^53.
- Surrogate-pair escapes combine; lone surrogates are parse errors.

## Dependencies

- Fin standard library (`strings::std`, `testing::std` for tests).
- C runtime (`strtod`, `snprintf`, `strnlen`, `calloc`, `free`).
- Python 3 standard library for differential tests. No third-party packages.

## Development

```sh
finc -O0 -I src tests/test_lib.fin -o test_finson && ./test_finson
python3 -I tests/differential.py ./test_finson
finc -O2 -I src tests/test_lib.fin -o test_finson && ./test_finson
python3 -I tests/differential.py ./test_finson
```

Pin the intended standard library with `--fin-libs /path/to/lib/std` when using a
frozen compiler. To check ownership on Linux, compile with `-c`, then link the
object using `cc -fsanitize=leak test_finson.o -o test_finson` and run both suites.
The native suite includes 2,000 successful parse/serialize/free cycles plus 6,000
failed-parse cleanup cycles. The differential suite compares generated Unicode,
nested values and binary64 numbers against Python JSON. `FINSON_TEST_LOCALE`
selects an installed non-dot locale for an explicit rejection test.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

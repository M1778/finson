# finson

JSON parsing and serialization for [Fin](https://github.com/M1778/Fin). Parse JSON
text into a `JsonValue` tree, build values programmatically, and serialize back to
compact or pretty-printed JSON.

>
> **Verification status:** ✅ VERIFIED — built with `finc 0.4.0` (contract 3);
> full test suite passes. CI also builds finc from source and re-runs everything.

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
        json_free_result(r);
        return;
    }
    let name <&JsonValue> = json_object_get(r.value, "name");
    printf("name: %s\n", name.s);

    json_object_set(r.value, "lang", json_str("fin"));
    let pretty <string> = json_stringify_pretty(r.value, 2);
    printf("%s\n", pretty);
    free_str(pretty);
    json_free_result(r);
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
fun json_parse(text: string) <ParseResult>
```

Parses a complete JSON document. Errors are recoverable: check `r.ok`, and on
failure `r.err` carries 1-based `line`/`col` and a human-readable `message`.
Release with `json_free_result(r)`.

### Serialization

```fin
fun json_stringify(v: &JsonValue) <string>              // compact
fun json_stringify_pretty(v: &JsonValue, indent: int) <string>  // pretty, N spaces
```

Both return a freshly allocated string — free it with `strings::std.free_str`
(or C `free`). Strings are escaped per RFC 8259 (`\"`, `\\`, `\n`, `\u00XX`,
...); non-ASCII UTF-8 bytes pass through unchanged.

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

## Supported JSON

- Full RFC 8259 grammar: objects, arrays, strings with escapes (including
  `\uXXXX` with surrogate-pair handling), numbers (int/frac/exp), literals.
- Duplicate object keys: last one wins (documented behavior).
- Numbers are `double`; very large integers lose precision past 2^53.
- `\u` escapes outside the Basic Multilingual Plane combine surrogate pairs;
  lone surrogates are parse errors.

## Dependencies

- Fin standard library only (`collection::std`, `strings::std`, `testing::std`
  for tests). No third-party packages.

## Development

```sh
finn test          # type-check tests/ (once finn codegen lands)
finc -I src tests/test_lib.fin -o test_finson && ./test_finson
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

Official CycloneDX schemas, vendored from
https://github.com/CycloneDX/specification/tree/master/schema

Vendored rather than fetched so the validation runs offline and in CI. A test
that silently skips when a network call fails is not a test — and this one
backs the claim `"bomFormat": "CycloneDX"` in a file a project may submit to a
regulator.

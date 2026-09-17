# Phase 3: LaTeX template system

## Protocol

Template identity is immutable `(id, version)`. A published version is never overwritten; changes require a new semantic version. Every bundle contains `template.json`, the Jinja2 entry file, and any referenced resources. Import stores every byte plus SHA-256 digests.

Protocol `1.0` has seven fixed roots:

- `basic_info`: personal information
- `education`: education entries
- `skills`: professional skill groups
- `work`: work and internship entries
- `projects`: project entries
- `certificates`: certificates and intellectual property
- `competitions`: awards and competitions

`options.show_avatar` is the only option root. Request data is parsed by strict Pydantic models; unknown fields are rejected. Template source is parsed as a Jinja AST before use. Includes, imports, inheritance, macros, function/method calls, unknown roots and dynamic output without `latex_escape` are rejected. Rendering uses an immutable sandbox, `StrictUndefined`, and deterministic LaTeX character escaping. It does not use string replacement.

## Built-ins and versions

The initial repository templates remain byte-for-byte unchanged at `1.0.0` so historical snapshots remain valid. Two protocol-compliant versions are added and enabled after import:

- `tpl-billryan-classic@1.1.0`
- `tpl-modern-twocol@1.1.0`

All other legacy bundles import as `INVALID` and disabled until they receive a new protocol-compliant version. Importing changed bytes under an existing `(id, version)` fails with `TemplateVersionConflict`.

Generation jobs already freeze `template_snapshot`, including metadata, entry source, all resources and content digest. Resume documents copy that snapshot from the completed job. Retries and historical rendering therefore use the frozen version, even when a newer version is enabled or the original version is later disabled.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/resume-templates` | List validated, enabled versions |
| `GET` | `/api/resume-templates/{id}` | Latest available detail and all version numbers |
| `GET` | `/api/resume-templates/{id}/versions` | List every retained version and its status |
| `GET` | `/api/resume-templates/{id}/versions/{version}` | Exact immutable version detail |
| `GET` | `/api/resume-templates/{id}/versions/{version}/validate` | Re-run placeholder and AST validation |
| `POST` | `/api/resume-templates/{id}/versions/{version}/compatibility` | Check language, page count, avatar and modules |
| `POST` | `/api/resume-templates/{id}/versions/{version}/preview` | Render deterministic LaTeX source from structured data |

The preview response returns `content_digest` and `source_sha256`, allowing callers to cache and audit exact output. PDF compilation remains a separate sandboxed generation stage; Phase 3 preview intentionally does not execute XeLaTeX inside the API process.

## Initialization

Run migrations first, then import bundles inside an explicit transaction:

```powershell
$env:RESUME_DATABASE_URL = 'mysql+aiomysql://...'
python -m app.infrastructure.resume_template_store
```

Run protocol and API tests with:

```powershell
pytest tests/test_resume_templates.py tests/test_resume_template_routes.py tests/test_storage_boundaries.py
```

An optional provisioned TeX runtime check is available with `RUN_LATEX_INTEGRATION=1`.

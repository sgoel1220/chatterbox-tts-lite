# Python Typing Standards

All Python code MUST be statically typed. Run `python3 -m mypy path/to/module.py --strict` before committing — zero errors required.

## Rules

- All functions must have type hints on all params and return type (include `-> None`)
- No `Any` without an explanatory comment; no `# type: ignore` without a specific reason
- Use Python 3.9+ built-in generics: `list[str]`, `dict[str, int]` — not `List`, `Dict` from `typing`
- Validate all external input with Pydantic; never trust raw dicts from API boundaries

## Pydantic — NEVER return `dict`

**NEVER use `dict` as a return type. ALWAYS create a Pydantic model.**

```python
# ❌ BAD
async def get_status() -> dict[str, str]:
    return {"status": "ok"}

# ✅ GOOD
class StatusResponse(BaseModel):
    status: str

async def get_status() -> StatusResponse:
    return StatusResponse(status="ok")
```

Model requirements: use `BaseModel`, `Field()` for validation, enums for constrained strings, `ConfigDict` for config.

## Make impossible states unrepresentable

```python
class JobComplete(BaseModel):
    status: Literal[JobStatus.COMPLETE]
    result: AudioResult

class JobFailed(BaseModel):
    status: Literal[JobStatus.FAILED]
    error: str

JobResult = JobComplete | JobFailed
```

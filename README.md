# Assignment 3 — Integration and System Testing (Starter Code)

This is the starter code for SE 413/513 Assignment 3. The **Course
Registration System** from Assignments 1–2 is now a small, complete
system: an HTTP API, a service, and a SQLite database, built on the same
`can_register()` and `calculate_registration_fee()` you tested before.
Everything in `src/` and `serve.py` is provided and **must not be
modified**. `SPEC.md` is the specification your tests check against.

## Project layout

```
assignment-3/
|-- src/
|   |-- registration.py      can_register(), calculate_registration_fee() (Assignments 1-2)
|   |-- db.py                schema, connect(), seed data
|   |-- repository.py        all SQL (RegistrationRepository)
|   |-- service.py           RegistrationService: enroll(), withdraw(), schedule()
|   |-- notifier.py          OutboxNotifier (used by serve.py)
|   |-- errors.py            exceptions shared by the components
|   `-- api.py               Flask HTTP API
|-- serve.py                 runs the whole system as one process
|-- SPEC.md                  requirements REQ-1..8, HTTP API, seed data
|-- tests/
|   |-- integration/conftest.py       (implement your fixtures here)
|   |-- integration/test_integration.py (implement your tests here)
|   |-- system/conftest.py            (PROVIDED: starts serve.py for each test)
|   `-- system/test_system.py         (implement your tests here)
|-- pyproject.toml
|-- requirements.txt
`-- README.md
```

## Setup

1. (Recommended) Create and activate a virtual environment:

   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

## Running the system by hand

```
python serve.py
```

prints `READY url=http://127.0.0.1:8000 outbox=...`. In a second terminal:

```
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/enrollments -H 'X-API-Key: registrar-key' \
     -H 'Content-Type: application/json' -d '{"student_id": "S01", "course_code": "SE413"}'
curl http://127.0.0.1:8000/students/S01/schedule -H 'X-API-Key: registrar-key'
```

(On Windows PowerShell, use `curl.exe` and escape the inner quotes, or
use Python's `requests`.) Every start uses a fresh database seeded as in
`SPEC.md`, unless you pass `--db <file>`.

## Running the tests

From the project root:

```
pytest                    # everything
pytest -m integration     # integration tests only
pytest -m system          # system tests only (each starts its own server)
```

## Notes

- Do not modify `src/` or `serve.py`. The starter contains **one known
  defect** (Section 4(d) of the assignment): document it with a test, do
  not fix it.
- Modules in `src/` are importable directly in your tests (no `src.`
  prefix), e.g. `from repository import RegistrationRepository`.
- `xfail_strict = true` is set in `pyproject.toml`: an `xfail` test that
  unexpectedly passes is reported as a failure.
- System tests must not import from `src/`: they see only HTTP and the
  outbox, through the provided `system` fixture.
  ## Integration Points (Section 4a)

| Integration Point | Components | Communication | Possible Disagreement |
|---|---|---|---|
| IP1 | HTTP Client and API | HTTP requests and JSON responses | The client may send invalid data or omit the required API key. |
| IP2 | API and RegistrationService | Python method calls and exceptions | The service may reject enrollment, and the API must translate the exception into the correct HTTP status. |
| IP3 | RegistrationService and RegistrationRepository | Python method calls | The service may expect an enrollment to be saved while the repository fails to store it correctly. |
| IP4 | RegistrationRepository and SQLite | SQL queries and transactions | The repository may attempt to insert duplicate enrollments or update seats beyond capacity. |
| IP5 | RegistrationService and Notifier | Python method calls | The service may send an incorrect confirmation fee or rejection reason. |

## Known Defect (Section 4d — REQ-6)

The known defect is in `RegistrationRepository.remove_enrollment()`. It removes enrollments using only the course code instead of both the student ID and course code, which can delete other students' enrollments in the same course. A unit test using a mocked repository would not detect this problem because the mock would simulate successful removal without executing the incorrect SQL query. The integration test detects the defect using a real SQLite database and is marked `xfail(strict=True)`.

## Concurrency Testing (Section 5c — REQ-2)

The concurrency test must be a system test because it checks how the complete application handles simultaneous HTTP requests across the API, service, repository, and database. Ten students attempt to enroll in SE499, which has only three seats, and the test verifies that exactly three students enroll while seven are rejected.

## Running the Test Suite (Section 6)

Run all tests:

```bash
python -m pytest -v
```

Run integration tests:

```bash
python -m pytest -m integration -v
```

Run system tests:

```bash
python -m pytest -m system -v
```

## Test Results

The complete test suite was executed from the project root.

- Integration testing: 7 passed, 1 expected failure (XFAIL).
- System testing: 15 passed.
- Complete test suite: **22 passed, 1 xfailed in 15.85 seconds**.

The expected failure demonstrates the known withdrawal defect under REQ-6. The defect was intentionally left unfixed, as instructed. All other tests passed successfully.

The integration and system tests use pytest markers and test docstrings that identify the requirements being tested.

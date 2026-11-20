"""System tests (Section 5 of the assignment).

Mark every test in this file with the `system` marker. Use the provided
`system` fixture (tests/system/conftest.py); do not import anything from
src/ here -- a system test sees only HTTP and the outbox.
"""

# TODO: implement your tests here.


"""System tests for the Course Registration System."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import requests


pytestmark = pytest.mark.system

API_KEY = {"X-API-Key": "registrar-key"}


def test_successful_enrollment(system):
    """REQ-1, REQ-2, REQ-4, REQ-5, REQ-7: Verify enrollment, fee, seats, schedule and notification."""
    response = system.enroll("S01", "SE413")

    assert response.status_code == 201
    enrollment = response.json()
    assert enrollment["student_id"] == "S01"
    assert enrollment["course_code"] == "SE413"
    assert enrollment["credits"] == 3
    assert enrollment["total_credits"] == 3
    assert enrollment["fee"] == 300.0

    schedule_response = system.get("/students/S01/schedule")
    assert schedule_response.status_code == 200
    schedule = schedule_response.json()

    assert schedule["student_id"] == "S01"
    assert schedule["total_credits"] == 3
    assert schedule["fee"] == 300.0
    assert any(
        course["code"] == "SE413"
        for course in schedule["courses"]
    )

    course_response = system.get("/courses/SE413")
    assert course_response.status_code == 200
    assert course_response.json()["seats_taken"] == 1

    messages = system.outbox()
    assert len(messages) == 1
    assert messages[0] == {
        "type": "confirmation",
        "student_id": "S01",
        "course_code": "SE413",
        "fee": 300.0,
    }


def test_missing_prerequisite(system):
    """REQ-1, REQ-2, REQ-5, REQ-7: Verify prerequisite rejection and unchanged state."""
    response = system.enroll("S13", "SE413")

    assert response.status_code == 422
    assert "prerequisite" in response.json()["error"].lower()

    schedule_response = system.get("/students/S13/schedule")
    assert schedule_response.status_code == 200
    schedule = schedule_response.json()

    assert schedule["courses"] == []
    assert schedule["total_credits"] == 0
    assert schedule["fee"] == 0.0

    course_response = system.get("/courses/SE413")
    assert course_response.status_code == 200
    assert course_response.json()["seats_taken"] == 0

    messages = system.outbox()
    assert len(messages) == 1
    assert messages[0] == {
        "type": "rejection",
        "student_id": "S13",
        "course_code": "SE413",
        "reason": "prerequisite CIS350 not completed",
    }


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"student_id": "S01"},
        {"student_id": 123, "course_code": "SE413"},
        {"student_id": "S01", "course_code": ["SE413"]},
        ["S01", "SE413"],
        {"student_id": "S01", "course_code": "A" * 1000},
        {"student_id": "S01", "course_code": "SE413';DROP"},
    ],
)
def test_invalid_enrollment_requests(system, body):
    """REQ-8, REQ-2, REQ-5: Reject invalid JSON bodies without changing state."""
    response = requests.post(
        f"{system.url}/enrollments",
        headers=API_KEY,
        json=body,
        timeout=10,
    )

    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/json")
    assert "error" in response.json()

    course_response = system.get("/courses/SE413")
    assert course_response.status_code == 200
    assert course_response.json()["seats_taken"] == 0

    schedule_response = system.get("/students/S01/schedule")
    assert schedule_response.status_code == 200
    assert schedule_response.json()["courses"] == []

    assert system.outbox() == []


@pytest.mark.parametrize(
    "method,path,body",
    [
        (
            "POST",
            "/enrollments",
            {"student_id": "S01", "course_code": "SE413"},
        ),
        ("GET", "/students/S01/schedule", None),
        ("GET", "/courses/SE413", None),
        ("DELETE", "/enrollments/S01/SE413", None),
    ],
)
def test_missing_api_key(system, method, path, body):
    """REQ-8: Every protected endpoint requires an API key."""
    response = requests.request(
        method,
        system.url + path,
        json=body,
        timeout=10,
    )

    assert response.status_code == 401
    assert response.headers["Content-Type"].startswith("application/json")
    assert "error" in response.json()
    assert system.outbox() == []


def test_health_without_api_key(system):
    """REQ-8: Health endpoint works without an API key."""
    response = requests.get(
        f"{system.url}/health",
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_concurrent_enrollment(system):
    """REQ-2, REQ-5: Ten students compete for three seats with correct notifications."""
    students = [f"S{i:02d}" for i in range(1, 11)]
    barrier = Barrier(10)

    def enroll_student(student_id):
        barrier.wait(timeout=15)

        response = requests.post(
            f"{system.url}/enrollments",
            headers=API_KEY,
            json={
                "student_id": student_id,
                "course_code": "SE499",
            },
            timeout=20,
        )

        return student_id, response.status_code

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(enroll_student, student_id)
            for student_id in students
        ]
        results = [future.result() for future in futures]

    successful = [
        student_id
        for student_id, status in results
        if status == 201
    ]

    rejected = [
        student_id
        for student_id, status in results
        if status == 409
    ]

    assert len(successful) == 3
    assert len(rejected) == 7

    course_response = system.get("/courses/SE499")
    assert course_response.status_code == 200
    assert course_response.json()["seats_taken"] == 3

    messages = system.outbox()

    confirmations = [
        message
        for message in messages
        if message["type"] == "confirmation"
    ]

    rejections = [
        message
        for message in messages
        if message["type"] == "rejection"
    ]

    assert len(messages) == 10
    assert len(confirmations) == 3
    assert len(rejections) == 7

    assert {
        message["student_id"]
        for message in confirmations
    } == set(successful)

    assert {
        message["student_id"]
        for message in rejections
    } == set(rejected)

    assert all(
        message["course_code"] == "SE499"
        for message in messages
    )

    assert all(
        message["fee"] == 300.0
        for message in confirmations
    )

    assert all(
        message["reason"] == "course is full"
        for message in rejections
    )

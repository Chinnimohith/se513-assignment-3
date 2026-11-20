"""Integration tests (Section 4 of the assignment).

Mark every test in this file with the `integration` marker, e.g.

    pytestmark = pytest.mark.integration

Modules are importable directly (see pyproject.toml), e.g.

    import db
    from repository import RegistrationRepository
    from service import RegistrationService
    from errors import CourseFull, AlreadyEnrolled, NotEligible
"""

# TODO: implement your tests here.
"""Integration tests of the real repository, database, service and notifier."""

import sqlite3
import pytest
from errors import AlreadyEnrolled, CourseFull

pytestmark = pytest.mark.integration


def test_last_seat_boundary(connection, repository):
    """REQ-2: The final seat is available, but over-capacity is refused."""
    with connection:
        assert repository.take_seat("CS102") is True
        assert repository.take_seat("CS102") is False
    assert repository.get_course("CS102")["seats_taken"] == 1


def test_duplicate_enrollment_database(connection, repository):
    """REQ-3: SQLite forbids duplicate enrollments for the same student."""
    with connection:
        repository.add_enrollment("S01", "CS101")
    with pytest.raises(sqlite3.IntegrityError):
        with connection:
            repository.add_enrollment("S01", "CS101")
    rows = repository.enrolled_courses("S01")
    assert len(rows) == 1
    assert rows[0]["code"] == "CS101"


def test_current_credits_per_student(connection, repository):
    """REQ-1: Current credits include only the requested student's courses."""
    with connection:
        repository.add_enrollment("S01", "CS101")
        repository.add_enrollment("S01", "CS103")
        repository.add_enrollment("S02", "CS102")
    assert repository.current_credits("S01") == 5
    assert repository.current_credits("S02") == 4
    assert repository.current_credits("S03") == 0


def test_transaction_rolls_back(connection, repository):
    """REQ-2, REQ-3: Failed enrollment rolls back its reserved seat."""
    with connection:
        repository.add_enrollment("S01", "CS101")
    with pytest.raises(sqlite3.IntegrityError):
        with connection:
            assert repository.take_seat("CS101")
            repository.add_enrollment("S01", "CS101")
    assert repository.get_course("CS101")["seats_taken"] == 0
    assert len(repository.enrolled_courses("S01")) == 1


def test_service_enrollment_success(service, repository, notifier):
    """REQ-1, REQ-2, REQ-4, REQ-5: Enrollment updates data and confirms fee."""
    result = service.enroll("S01", "CS101")
    assert result["student_id"] == "S01"
    assert result["course_code"] == "CS101"
    assert result["total_credits"] == 3
    assert result["fee"] == 300.0
    assert [c["code"] for c in repository.enrolled_courses("S01")] == ["CS101"]
    assert repository.get_course("CS101")["seats_taken"] == 1
    assert notifier.messages == [{
        "type": "confirmation", "student_id": "S01",
        "course_code": "CS101", "fee": 300.0,
    }]


def test_service_course_full(service, repository, notifier):
    """REQ-2, REQ-5: Full course rejects enrollment and sends a reason."""
    service.enroll("S01", "CS102")
    notifier.messages.clear()
    with pytest.raises(CourseFull):
        service.enroll("S02", "CS102")
    assert repository.get_course("CS102")["seats_taken"] == 1
    assert repository.enrolled_courses("S02") == []
    assert notifier.messages == [{
        "type": "rejection", "student_id": "S02",
        "course_code": "CS102", "reason": "course is full",
    }]


def test_service_duplicate_no_notification(service, repository, notifier):
    """REQ-3, REQ-5: Duplicate enrollment changes neither seats nor messages."""
    service.enroll("S01", "CS101")
    notifier.messages.clear()
    with pytest.raises(AlreadyEnrolled):
        service.enroll("S01", "CS101")
    assert repository.get_course("CS101")["seats_taken"] == 1
    assert len(repository.enrolled_courses("S01")) == 1
    assert notifier.messages == []


@pytest.mark.xfail(
    strict=True,
    reason="remove_enrollment deletes every student's enrollment for a course, not just the withdrawing student's",
)
def test_withdraw_keeps_other_student_enrolled(service, repository):
    """REQ-6: Withdrawing one student must preserve others in the course."""
    service.enroll("S01", "CS101")
    service.enroll("S02", "CS101")
    service.withdraw("S01", "CS101")
    assert repository.enrolled_courses("S01") == []
    assert [c["code"] for c in repository.enrolled_courses("S02")] == ["CS101"]
    assert repository.get_course("CS101")["seats_taken"] == 1


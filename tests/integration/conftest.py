"""Fixtures for your integration tests (Section 4 of the assignment).

Your integration tests assemble the REAL repository and service on a
REAL SQLite database file -- inside the test process. Suggested fixtures
(write them here):

  - a connection to a new database file in pytest's `tmp_path`, with
    db.create_schema() applied and a few students and courses added
    through the repository (or with db.seed());
  - a RegistrationRepository on that connection;
  - a fake notifier: a small class of your own that records every
    send_confirmation / send_rejection call in a list, so a test can
    check what was sent;
  - a RegistrationService built from the three.
"""

# TODO: implement your fixtures here.
"""Fixtures for real SQLite and service integration tests."""

import pytest
import db
from repository import RegistrationRepository
from service import RegistrationService


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def send_confirmation(self, student_id, course_code, fee):
        self.messages.append({
            "type": "confirmation", "student_id": student_id,
            "course_code": course_code, "fee": fee,
        })

    def send_rejection(self, student_id, course_code, reason):
        self.messages.append({
            "type": "rejection", "student_id": student_id,
            "course_code": course_code, "reason": reason,
        })


@pytest.fixture
def connection(tmp_path):
    connection = db.connect(str(tmp_path / "registration.sqlite"))
    db.create_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def repository(connection):
    repository = RegistrationRepository(connection)
    with connection:
        for student in ("S01", "S02", "S03"):
            repository.add_student(student, f"Student {student}")
        repository.add_course("CS101", "Intro Programming", 3, 2)
        repository.add_course("CS102", "Data Systems", 4, 1)
        repository.add_course("CS103", "Web Testing", 2, 2)
    return repository


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def service(connection, repository, notifier):
    return RegistrationService(connection, repository, notifier)


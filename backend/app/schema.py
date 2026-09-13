"""M1 relational schema. Domain tables use composite edition-aware references."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

metadata = sa.MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def col(name, kind, **kwargs):
    return sa.Column(name, kind, nullable=False, **kwargs)


edition = sa.Table(
    "dataset_edition",
    metadata,
    col("id", sa.Uuid, primary_key=True),
    col("seed", sa.Integer),
    col("generator_version", sa.String(40)),
    col("config", JSONB),
    col("logical_content_hash", sa.String(64)),
    col("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("frozen_at", sa.DateTime(timezone=True)),
)


def ref(field, parent):
    return sa.ForeignKeyConstraint(["edition_id", field], [f"{parent}.edition_id", f"{parent}.id"])


def domain(name, *columns):
    return sa.Table(
        name,
        metadata,
        col("id", sa.Uuid, primary_key=True),
        col("edition_id", sa.Uuid),
        sa.ForeignKeyConstraint(["edition_id"], ["dataset_edition.id"]),
        sa.UniqueConstraint("edition_id", "id"),
        *columns,
    )


department = domain(
    "department", col("code", sa.String(40)), sa.UniqueConstraint("edition_id", "code")
)
program = domain(
    "program",
    col("department_id", sa.Uuid),
    col("code", sa.String(40)),
    ref("department_id", "department"),
    sa.UniqueConstraint("edition_id", "code"),
)
batch = domain(
    "batch",
    col("program_id", sa.Uuid),
    col("start_year", sa.Integer),
    ref("program_id", "program"),
    sa.UniqueConstraint("edition_id", "program_id", "start_year"),
)
section = domain(
    "section",
    col("batch_id", sa.Uuid),
    col("code", sa.String(40)),
    ref("batch_id", "batch"),
    sa.UniqueConstraint("edition_id", "batch_id", "code"),
)
student = domain(
    "student",
    col("section_id", sa.Uuid),
    col("synthetic_label", sa.String(80)),
    ref("section_id", "section"),
)
faculty = domain(
    "faculty",
    col("department_id", sa.Uuid),
    col("synthetic_label", sa.String(80)),
    ref("department_id", "department"),
)
course = domain(
    "course",
    col("department_id", sa.Uuid),
    col("code", sa.String(40)),
    col("required_room_kind", sa.String(20)),
    sa.Column("required_lab_type", sa.String(40)),
    ref("department_id", "department"),
    sa.UniqueConstraint("edition_id", "code"),
    sa.CheckConstraint("required_room_kind IN ('classroom','lab')", name="room_kind"),
    sa.CheckConstraint(
        "(required_room_kind='lab') = (required_lab_type IS NOT NULL)", name="lab_type"
    ),
)
term = domain(
    "term",
    col("start_date", sa.Date),
    col("end_date", sa.Date),
    sa.CheckConstraint("start_date < end_date", name="dates"),
)
offering = domain(
    "course_offering",
    col("course_id", sa.Uuid),
    col("section_id", sa.Uuid),
    col("faculty_id", sa.Uuid),
    col("term_id", sa.Uuid),
    ref("course_id", "course"),
    ref("section_id", "section"),
    ref("faculty_id", "faculty"),
    ref("term_id", "term"),
    sa.UniqueConstraint("edition_id", "course_id", "section_id", "term_id"),
)
room = domain(
    "room",
    col("code", sa.String(40)),
    col("capacity", sa.Integer),
    col("kind", sa.String(20)),
    sa.Column("lab_type", sa.String(40)),
    sa.UniqueConstraint("edition_id", "code"),
    sa.CheckConstraint("capacity > 0", name="capacity"),
    sa.CheckConstraint("kind IN ('classroom','lab')", name="kind"),
    sa.CheckConstraint("(kind='lab') = (lab_type IS NOT NULL)", name="lab_type"),
)
class_session = domain(
    "class_session",
    col("offering_id", sa.Uuid),
    col("room_id", sa.Uuid),
    col("starts_at", sa.DateTime(timezone=True)),
    col("ends_at", sa.DateTime(timezone=True)),
    col("status", sa.String(20)),
    col("status_recorded_at", sa.DateTime(timezone=True)),
    ref("offering_id", "course_offering"),
    ref("room_id", "room"),
    sa.CheckConstraint("starts_at < ends_at", name="interval"),
    sa.CheckConstraint("status IN ('scheduled','held','cancelled')", name="status"),
    sa.CheckConstraint("status != 'held' OR status_recorded_at >= ends_at", name="held_recording"),
    sa.Index("ix_class_session_edition_time", "edition_id", "starts_at"),
)
attendance = domain(
    "attendance",
    col("session_id", sa.Uuid),
    col("student_id", sa.Uuid),
    col("status", sa.String(10)),
    col("recorded_at", sa.DateTime(timezone=True)),
    ref("session_id", "class_session"),
    ref("student_id", "student"),
    sa.UniqueConstraint("edition_id", "session_id", "student_id"),
    sa.CheckConstraint("status IN ('present','absent')", name="status"),
    sa.Index("ix_attendance_student_session", "student_id", "session_id"),
)
sa.Index("ix_offering_section", offering.c.edition_id, offering.c.section_id)
sa.Index("ix_offering_faculty", offering.c.edition_id, offering.c.faculty_id)

user = sa.Table(
    "app_user",
    metadata,
    col("id", sa.Uuid, primary_key=True),
    col("username", sa.String(80), unique=True),
    col("password_hash", sa.Text),
    col("role", sa.String(10)),
    sa.CheckConstraint("role IN ('viewer','planner')", name="role"),
)
auth_session = sa.Table(
    "auth_session",
    metadata,
    col("token_hash", sa.String(64), primary_key=True),
    col("user_id", sa.Uuid),
    sa.ForeignKeyConstraint(["user_id"], ["app_user.id"]),
    col("csrf_hash", sa.String(64)),
    col("expires_at", sa.DateTime(timezone=True)),
)
audit = sa.Table(
    "audit_log",
    metadata,
    col("id", sa.Uuid, primary_key=True),
    sa.Column("actor_id", sa.Uuid, sa.ForeignKey("app_user.id")),
    col("action", sa.String(80)),
    sa.Column("resource_id", sa.Uuid),
    col("request_id", sa.String(40)),
    col("occurred_at", sa.DateTime(timezone=True)),
    col("outcome", sa.String(20)),
)

DOMAIN_TABLES = [
    department,
    program,
    batch,
    section,
    student,
    faculty,
    course,
    term,
    room,
    offering,
    class_session,
    attendance,
]

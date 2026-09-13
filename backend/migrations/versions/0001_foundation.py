"""M1 foundation: frozen DDL, independent of future application metadata."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE dataset_edition (\n\tid UUID NOT NULL, \n\tseed INTEGER NOT NULL, \n\tgenerator_version VARCHAR(40) NOT NULL, \n\tconfig JSONB NOT NULL, \n\tlogical_content_hash VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tfrozen_at TIMESTAMP WITH TIME ZONE, \n\tCONSTRAINT pk_dataset_edition PRIMARY KEY (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE app_user (\n\tid UUID NOT NULL, \n\tusername VARCHAR(80) NOT NULL, \n\tpassword_hash TEXT NOT NULL, \n\trole VARCHAR(10) NOT NULL, \n\tCONSTRAINT pk_app_user PRIMARY KEY (id), \n\tCONSTRAINT ck_app_user_role CHECK (role IN ('viewer','planner')), \n\tCONSTRAINT uq_app_user_username UNIQUE (username)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE department (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\tCONSTRAINT pk_department PRIMARY KEY (id), \n\tCONSTRAINT uq_department_edition_id_code UNIQUE (edition_id, code), \n\tCONSTRAINT fk_department_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_department_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE term (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tstart_date DATE NOT NULL, \n\tend_date DATE NOT NULL, \n\tCONSTRAINT pk_term PRIMARY KEY (id), \n\tCONSTRAINT ck_term_dates CHECK (start_date < end_date), \n\tCONSTRAINT fk_term_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_term_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE room (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\tcapacity INTEGER NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tlab_type VARCHAR(40), \n\tCONSTRAINT pk_room PRIMARY KEY (id), \n\tCONSTRAINT uq_room_edition_id_code UNIQUE (edition_id, code), \n\tCONSTRAINT ck_room_capacity CHECK (capacity > 0), \n\tCONSTRAINT ck_room_kind CHECK (kind IN ('classroom','lab')), \n\tCONSTRAINT ck_room_lab_type CHECK ((kind='lab') = (lab_type IS NOT NULL)), \n\tCONSTRAINT fk_room_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_room_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE auth_session (\n\ttoken_hash VARCHAR(64) NOT NULL, \n\tuser_id UUID NOT NULL, \n\tcsrf_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_auth_session PRIMARY KEY (token_hash), \n\tCONSTRAINT fk_auth_session_user_id_app_user FOREIGN KEY(user_id) REFERENCES app_user (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE audit_log (\n\tid UUID NOT NULL, \n\tactor_id UUID, \n\taction VARCHAR(80) NOT NULL, \n\tresource_id UUID, \n\trequest_id VARCHAR(40) NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\toutcome VARCHAR(20) NOT NULL, \n\tCONSTRAINT pk_audit_log PRIMARY KEY (id), \n\tCONSTRAINT fk_audit_log_actor_id_app_user FOREIGN KEY(actor_id) REFERENCES app_user (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE program (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\tCONSTRAINT pk_program PRIMARY KEY (id), \n\tCONSTRAINT fk_program_edition_id_department FOREIGN KEY(edition_id, department_id) REFERENCES department (edition_id, id), \n\tCONSTRAINT uq_program_edition_id_code UNIQUE (edition_id, code), \n\tCONSTRAINT fk_program_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_program_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE faculty (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\tsynthetic_label VARCHAR(80) NOT NULL, \n\tCONSTRAINT pk_faculty PRIMARY KEY (id), \n\tCONSTRAINT fk_faculty_edition_id_department FOREIGN KEY(edition_id, department_id) REFERENCES department (edition_id, id), \n\tCONSTRAINT fk_faculty_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_faculty_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE course (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tdepartment_id UUID NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\trequired_room_kind VARCHAR(20) NOT NULL, \n\trequired_lab_type VARCHAR(40), \n\tCONSTRAINT pk_course PRIMARY KEY (id), \n\tCONSTRAINT fk_course_edition_id_department FOREIGN KEY(edition_id, department_id) REFERENCES department (edition_id, id), \n\tCONSTRAINT uq_course_edition_id_code UNIQUE (edition_id, code), \n\tCONSTRAINT ck_course_room_kind CHECK (required_room_kind IN ('classroom','lab')), \n\tCONSTRAINT ck_course_lab_type CHECK ((required_room_kind='lab') = (required_lab_type IS NOT NULL)), \n\tCONSTRAINT fk_course_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_course_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE batch (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tprogram_id UUID NOT NULL, \n\tstart_year INTEGER NOT NULL, \n\tCONSTRAINT pk_batch PRIMARY KEY (id), \n\tCONSTRAINT fk_batch_edition_id_program FOREIGN KEY(edition_id, program_id) REFERENCES program (edition_id, id), \n\tCONSTRAINT uq_batch_edition_id_program_id_start_year UNIQUE (edition_id, program_id, start_year), \n\tCONSTRAINT fk_batch_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_batch_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE section (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tbatch_id UUID NOT NULL, \n\tcode VARCHAR(40) NOT NULL, \n\tCONSTRAINT pk_section PRIMARY KEY (id), \n\tCONSTRAINT fk_section_edition_id_batch FOREIGN KEY(edition_id, batch_id) REFERENCES batch (edition_id, id), \n\tCONSTRAINT uq_section_edition_id_batch_id_code UNIQUE (edition_id, batch_id, code), \n\tCONSTRAINT fk_section_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_section_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE student (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tsection_id UUID NOT NULL, \n\tsynthetic_label VARCHAR(80) NOT NULL, \n\tCONSTRAINT pk_student PRIMARY KEY (id), \n\tCONSTRAINT fk_student_edition_id_section FOREIGN KEY(edition_id, section_id) REFERENCES section (edition_id, id), \n\tCONSTRAINT fk_student_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_student_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE course_offering (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tcourse_id UUID NOT NULL, \n\tsection_id UUID NOT NULL, \n\tfaculty_id UUID NOT NULL, \n\tterm_id UUID NOT NULL, \n\tCONSTRAINT pk_course_offering PRIMARY KEY (id), \n\tCONSTRAINT fk_course_offering_edition_id_course FOREIGN KEY(edition_id, course_id) REFERENCES course (edition_id, id), \n\tCONSTRAINT fk_course_offering_edition_id_section FOREIGN KEY(edition_id, section_id) REFERENCES section (edition_id, id), \n\tCONSTRAINT fk_course_offering_edition_id_faculty FOREIGN KEY(edition_id, faculty_id) REFERENCES faculty (edition_id, id), \n\tCONSTRAINT fk_course_offering_edition_id_term FOREIGN KEY(edition_id, term_id) REFERENCES term (edition_id, id), \n\tCONSTRAINT uq_course_offering_edition_id_course_id_section_id_term_id UNIQUE (edition_id, course_id, section_id, term_id), \n\tCONSTRAINT fk_course_offering_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_course_offering_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_offering_section ON course_offering (edition_id, section_id)")
    op.execute("CREATE INDEX ix_offering_faculty ON course_offering (edition_id, faculty_id)")
    op.execute(
        "\nCREATE TABLE class_session (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\toffering_id UUID NOT NULL, \n\troom_id UUID NOT NULL, \n\tstarts_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tends_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tstatus_recorded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_class_session PRIMARY KEY (id), \n\tCONSTRAINT fk_class_session_edition_id_course_offering FOREIGN KEY(edition_id, offering_id) REFERENCES course_offering (edition_id, id), \n\tCONSTRAINT fk_class_session_edition_id_room FOREIGN KEY(edition_id, room_id) REFERENCES room (edition_id, id), \n\tCONSTRAINT ck_class_session_interval CHECK (starts_at < ends_at), \n\tCONSTRAINT ck_class_session_status CHECK (status IN ('scheduled','held','cancelled')), \n\tCONSTRAINT ck_class_session_held_recording CHECK (status != 'held' OR status_recorded_at >= ends_at), \n\tCONSTRAINT fk_class_session_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_class_session_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_class_session_edition_time ON class_session (edition_id, starts_at)"
    )
    op.execute(
        "\nCREATE TABLE attendance (\n\tid UUID NOT NULL, \n\tedition_id UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tstudent_id UUID NOT NULL, \n\tstatus VARCHAR(10) NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_attendance PRIMARY KEY (id), \n\tCONSTRAINT fk_attendance_edition_id_class_session FOREIGN KEY(edition_id, session_id) REFERENCES class_session (edition_id, id), \n\tCONSTRAINT fk_attendance_edition_id_student FOREIGN KEY(edition_id, student_id) REFERENCES student (edition_id, id), \n\tCONSTRAINT uq_attendance_edition_id_session_id_student_id UNIQUE (edition_id, session_id, student_id), \n\tCONSTRAINT ck_attendance_status CHECK (status IN ('present','absent')), \n\tCONSTRAINT fk_attendance_edition_id_dataset_edition FOREIGN KEY(edition_id) REFERENCES dataset_edition (id), \n\tCONSTRAINT uq_attendance_edition_id_id UNIQUE (edition_id, id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_attendance_student_session ON attendance (student_id, session_id)")
    op.execute(
        "\nCREATE FUNCTION protect_frozen_domain() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE target_edition uuid;\nBEGIN\n    IF TG_OP = 'DELETE' THEN target_edition := OLD.edition_id;\n    ELSE target_edition := NEW.edition_id; END IF;\n    IF EXISTS (SELECT 1 FROM dataset_edition WHERE id=target_edition AND frozen_at IS NOT NULL)\n       OR (TG_OP='UPDATE' AND EXISTS (SELECT 1 FROM dataset_edition WHERE id=OLD.edition_id AND frozen_at IS NOT NULL)) THEN\n        RAISE EXCEPTION 'Frozen edition is immutable';\n    END IF;\n    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;\nEND $$\n"
    )
    op.execute(
        "CREATE TRIGGER freeze_department BEFORE INSERT OR UPDATE OR DELETE ON department FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_program BEFORE INSERT OR UPDATE OR DELETE ON program FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_batch BEFORE INSERT OR UPDATE OR DELETE ON batch FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_section BEFORE INSERT OR UPDATE OR DELETE ON section FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_student BEFORE INSERT OR UPDATE OR DELETE ON student FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_faculty BEFORE INSERT OR UPDATE OR DELETE ON faculty FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_course BEFORE INSERT OR UPDATE OR DELETE ON course FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_term BEFORE INSERT OR UPDATE OR DELETE ON term FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_room BEFORE INSERT OR UPDATE OR DELETE ON room FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_course_offering BEFORE INSERT OR UPDATE OR DELETE ON course_offering FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_class_session BEFORE INSERT OR UPDATE OR DELETE ON class_session FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "CREATE TRIGGER freeze_attendance BEFORE INSERT OR UPDATE OR DELETE ON attendance FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    )
    op.execute(
        "\nCREATE FUNCTION protect_frozen_edition() RETURNS trigger LANGUAGE plpgsql AS $$\nBEGIN\n    IF OLD.frozen_at IS NOT NULL THEN RAISE EXCEPTION 'Frozen edition is immutable'; END IF;\n    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;\nEND $$\n"
    )
    op.execute(
        "CREATE TRIGGER freeze_edition BEFORE UPDATE OR DELETE ON dataset_edition FOR EACH ROW EXECUTE FUNCTION protect_frozen_edition()"
    )


def downgrade():
    op.drop_table("attendance")
    op.drop_table("class_session")
    op.drop_table("student")
    op.drop_table("course_offering")
    op.drop_table("section")
    op.drop_table("batch")
    op.drop_table("program")
    op.drop_table("faculty")
    op.drop_table("course")
    op.drop_table("term")
    op.drop_table("room")
    op.drop_table("department")
    op.drop_table("auth_session")
    op.drop_table("audit_log")
    op.drop_table("dataset_edition")
    op.drop_table("app_user")
    op.execute("DROP FUNCTION protect_frozen_domain()")
    op.execute("DROP FUNCTION protect_frozen_edition()")

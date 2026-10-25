"""Retain legacy sample tables; add versioned staff workflows and immutable evidence."""
from alembic import op
import sqlalchemy as sa
from civicpermit.workflow_schema import metadata, IMMUTABLE_TABLES

revision = "civicpermit_0001"
down_revision = None


def upgrade():
    connection = op.get_bind()
    metadata.create_all(connection)
    if connection.dialect.name == "postgresql":
        connection.execute(sa.text("""CREATE FUNCTION civicpermit.reject_connected_mutation()
            RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'Permitting history is append-only'; END $$"""))
        for table in IMMUTABLE_TABLES:
            connection.execute(sa.text(f"CREATE TRIGGER immutable_connected BEFORE UPDATE OR DELETE ON civicpermit.{table.name} FOR EACH ROW EXECUTE FUNCTION civicpermit.reject_connected_mutation()"))
    else:
        for table in IMMUTABLE_TABLES:
            for operation in ("UPDATE", "DELETE"):
                connection.execute(sa.text(f"CREATE TRIGGER {table.name}_{operation.lower()} BEFORE {operation} ON {table.name} BEGIN SELECT RAISE(ABORT, 'Permitting history is append-only'); END"))


def downgrade():
    raise RuntimeError("Destructive history downgrade is unsupported; restore a coherent backup.")

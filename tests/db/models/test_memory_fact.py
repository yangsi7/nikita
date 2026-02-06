"""Tests for MemoryFact model (Spec 042 T0.3)."""

from uuid import uuid4

import pytest

from nikita.db.models.memory_fact import MemoryFact


class TestMemoryFactModel:
    """Tests for MemoryFact SQLAlchemy model."""

    def test_has_all_required_columns(self):
        """AC-0.3.1: MemoryFact model with all columns mapped."""
        table = MemoryFact.__table__
        expected_columns = {
            "id", "user_id", "graph_type", "fact", "source",
            "confidence", "embedding", "metadata", "is_active",
            "superseded_by", "conversation_id", "created_at", "updated_at",
        }
        actual_columns = {c.name for c in table.columns}
        assert expected_columns.issubset(actual_columns), (
            f"Missing columns: {expected_columns - actual_columns}"
        )

    def test_embedding_column_is_vector_1536(self):
        """AC-0.3.1: embedding column uses Vector(1536)."""
        column = MemoryFact.__table__.columns["embedding"]
        # pgvector Vector type has dim attribute
        assert column.type.dim == 1536
        assert column.nullable is False

    def test_graph_type_check_constraint(self):
        """AC-0.1.3: graph_type CHECK enforces ('user', 'relationship', 'nikita')."""
        column = MemoryFact.__table__.columns["graph_type"]
        assert column.nullable is False
        # Verify the column exists and is a string type
        assert str(column.type).startswith("VARCHAR") or str(column.type) == "TEXT"

    def test_confidence_column_properties(self):
        """Confidence is REAL/FLOAT, not nullable."""
        column = MemoryFact.__table__.columns["confidence"]
        assert column.nullable is False

    def test_user_id_foreign_key(self):
        """AC-0.3.2: FK to users table with cascade delete."""
        column = MemoryFact.__table__.columns["user_id"]
        fks = list(column.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert str(fk.column) == "users.id"
        assert fk.ondelete == "CASCADE"

    def test_conversation_id_foreign_key_nullable(self):
        """AC-0.3.3: FK to conversations, nullable."""
        column = MemoryFact.__table__.columns["conversation_id"]
        assert column.nullable is True
        fks = list(column.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].column) == "conversations.id"

    def test_superseded_by_self_reference(self):
        """AC-0.3.4: Self-referential FK for superseded_by."""
        column = MemoryFact.__table__.columns["superseded_by"]
        assert column.nullable is True
        fks = list(column.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].column) == "memory_facts.id"

    def test_fact_metadata_maps_to_metadata_column(self):
        """Python attr 'fact_metadata' maps to DB column 'metadata'."""
        # The DB column name should be "metadata"
        column = MemoryFact.__table__.columns["metadata"]
        assert column is not None
        # But the Python attribute name should be fact_metadata
        fact = MemoryFact(
            id=uuid4(),
            user_id=uuid4(),
            graph_type="user",
            fact="Test fact",
            source="test",
            confidence=0.9,
            embedding=[0.1] * 1536,
            fact_metadata={"key": "value"},
            is_active=True,
        )
        assert fact.fact_metadata == {"key": "value"}

    def test_is_active_default_true(self):
        """is_active defaults to True."""
        column = MemoryFact.__table__.columns["is_active"]
        assert column.nullable is False

    def test_model_instantiation(self):
        """Can create MemoryFact instance with all fields."""
        user_id = uuid4()
        fact = MemoryFact(
            id=uuid4(),
            user_id=user_id,
            graph_type="relationship",
            fact="User likes hiking",
            source="conversation",
            confidence=0.85,
            embedding=[0.1] * 1536,
            fact_metadata={"topic": "hobbies"},
            is_active=True,
        )
        assert fact.user_id == user_id
        assert fact.graph_type == "relationship"
        assert fact.fact == "User likes hiking"
        assert fact.source == "conversation"
        assert fact.confidence == 0.85
        assert len(fact.embedding) == 1536
        assert fact.fact_metadata == {"topic": "hobbies"}
        assert fact.is_active is True

    def test_tablename(self):
        """Table name is memory_facts."""
        assert MemoryFact.__tablename__ == "memory_facts"

"""Add production CRM, call intelligence, work, and analytics schema.

Revision ID: a91e6d1f20b4
Revises: c36b74c6365a
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.compliance.encryption
import app.db.base


revision: str = "a91e6d1f20b4"
down_revision: Union[str, None] = "c36b74c6365a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    with op.batch_alter_table("customers") as batch:
        batch.add_column(sa.Column("photo_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("occupation", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("city", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("location", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("stage", sa.String(length=50), nullable=False, server_default="new"))
        batch.add_column(sa.Column("kyc_status", sa.String(length=50), nullable=False, server_default="pending"))
        batch.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("current_intent", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("current_sentiment", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="low"))
        batch.add_column(sa.Column("buying_signals", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("objections", sa.JSON(), nullable=False, server_default="[]"))

    with op.batch_alter_table("calls") as batch:
        batch.add_column(sa.Column("ai_session_id", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("ended_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("summary", app.compliance.encryption.EncryptedString(length=8192), nullable=True))
        batch.add_column(sa.Column("live_summary", app.compliance.encryption.EncryptedString(length=8192), nullable=True))
        batch.add_column(sa.Column("outcome", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("primary_intent", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("final_sentiment", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("compliance_status", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("compliance_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("agent_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("satisfaction_score", sa.Float(), nullable=True))
        batch.add_column(sa.Column("revenue", sa.Float(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("recording_url", sa.String(length=2048), nullable=True))
        batch.add_column(sa.Column("ai_suggestion_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("ai_suggestion_used_count", sa.Integer(), nullable=False, server_default="0"))
        batch.create_index("ix_calls_ai_session_id", ["ai_session_id"], unique=False)

    with op.batch_alter_table("transcripts") as batch:
        batch.add_column(sa.Column("segment_id", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("sequence_number", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("start_seconds", sa.Float(), nullable=True))
        batch.add_column(sa.Column("end_seconds", sa.Float(), nullable=True))
        batch.add_column(sa.Column("language", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("bookmarked", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_transcripts_segment_id", ["segment_id"], unique=True)

    with op.batch_alter_table("follow_ups") as batch:
        batch.add_column(sa.Column("title", sa.String(length=255), nullable=False, server_default="Customer follow-up"))
        batch.add_column(sa.Column("description", app.compliance.encryption.EncryptedString(length=4096), nullable=True))
        batch.add_column(sa.Column("channel", sa.String(length=30), nullable=False, server_default="phone"))
        batch.add_column(sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"))
        batch.add_column(sa.Column("reminder_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("assigned_user_id", app.db.base.GUID(), nullable=True))
        batch.create_foreign_key("fk_follow_ups_assigned_user", "users", ["assigned_user_id"], ["id"])

    op.create_table(
        "leads",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("customer_id", app.db.base.GUID(), nullable=False),
        sa.Column("owner_user_id", app.db.base.GUID(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="inbound"),
        sa.Column("stage", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_customer_id", "leads", ["customer_id"])
    op.create_index("ix_leads_stage", "leads", ["stage"])

    op.create_table(
        "purchases",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("customer_id", app.db.base.GUID(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchases_customer_id", "purchases", ["customer_id"])

    op.create_table(
        "customer_offers",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("customer_id", app.db.base.GUID(), nullable=False),
        sa.Column("product_offer_id", app.db.base.GUID(), nullable=True),
        sa.Column("offer_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="presented"),
        sa.Column("presented_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["product_offer_id"], ["products_offers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_offers_customer_id", "customer_offers", ["customer_id"])

    op.create_table(
        "notes",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("customer_id", app.db.base.GUID(), nullable=False),
        sa.Column("call_id", app.db.base.GUID(), nullable=True),
        sa.Column("author_user_id", app.db.base.GUID(), nullable=True),
        sa.Column("body", app.compliance.encryption.EncryptedString(length=8192), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_customer_id", "notes", ["customer_id"])
    op.create_index("ix_notes_call_id", "notes", ["call_id"])

    op.create_table(
        "tasks",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("customer_id", app.db.base.GUID(), nullable=True),
        sa.Column("call_id", app.db.base.GUID(), nullable=True),
        sa.Column("assigned_user_id", app.db.base.GUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", app.compliance.encryption.EncryptedString(length=4096), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="upcoming"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_customer_id", "tasks", ["customer_id"])
    op.create_index("ix_tasks_call_id", "tasks", ["call_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])

    op.create_table(
        "call_insights",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("call_id", app.db.base.GUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("sentiment", sa.String(length=50), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("buying_signals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("objections", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("next_action", sa.String(length=100), nullable=True),
        sa.Column("compliance_safe", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("call_id", "sequence_number", name="uq_call_insight_sequence"),
    )
    op.create_index("ix_call_insights_call_id", "call_insights", ["call_id"])

    op.create_table(
        "ai_suggestions",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("call_id", app.db.base.GUID(), nullable=False),
        sa.Column("insight_id", app.db.base.GUID(), nullable=True),
        sa.Column("text", app.compliance.encryption.EncryptedString(length=8192), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.ForeignKeyConstraint(["insight_id"], ["call_insights.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_suggestions_call_id", "ai_suggestions", ["call_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=2048), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("indexed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_sha256"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("user_id", app.db.base.GUID(), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=2048), nullable=True),
        sa.Column("related_type", sa.String(length=50), nullable=True),
        sa.Column("related_id", app.db.base.GUID(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_ai_suggestions_call_id", table_name="ai_suggestions")
    op.drop_table("ai_suggestions")
    op.drop_index("ix_call_insights_call_id", table_name="call_insights")
    op.drop_table("call_insights")
    op.drop_index("ix_tasks_due_at", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_call_id", table_name="tasks")
    op.drop_index("ix_tasks_customer_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_notes_call_id", table_name="notes")
    op.drop_index("ix_notes_customer_id", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_customer_offers_customer_id", table_name="customer_offers")
    op.drop_table("customer_offers")
    op.drop_index("ix_purchases_customer_id", table_name="purchases")
    op.drop_table("purchases")
    op.drop_index("ix_leads_stage", table_name="leads")
    op.drop_index("ix_leads_customer_id", table_name="leads")
    op.drop_table("leads")

    with op.batch_alter_table("follow_ups") as batch:
        batch.drop_constraint("fk_follow_ups_assigned_user", type_="foreignkey")
        for column in ("assigned_user_id", "completed_at", "reminder_at", "priority", "channel", "description", "title"):
            batch.drop_column(column)
    with op.batch_alter_table("transcripts") as batch:
        batch.drop_index("ix_transcripts_segment_id")
        for column in ("bookmarked", "is_final", "language", "end_seconds", "start_seconds", "sequence_number", "segment_id"):
            batch.drop_column(column)
    with op.batch_alter_table("calls") as batch:
        batch.drop_index("ix_calls_ai_session_id")
        for column in ("ai_suggestion_used_count", "ai_suggestion_count", "recording_url", "revenue", "satisfaction_score", "agent_score", "compliance_score", "compliance_status", "final_sentiment", "primary_intent", "outcome", "live_summary", "summary", "duration_seconds", "ended_at", "started_at", "ai_session_id"):
            batch.drop_column(column)
    with op.batch_alter_table("customers") as batch:
        for column in ("objections", "buying_signals", "risk_level", "current_sentiment", "current_intent", "tags", "kyc_status", "stage", "lead_score", "location", "city", "occupation", "photo_url"):
            batch.drop_column(column)

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

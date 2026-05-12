"""add indexes to audit_logs for security

Revision ID: c1144cdcd576
Revises: 9aac18eb7bba
Create Date: 2026-05-12 08:40:10.755910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1144cdcd576'
down_revision: Union[str, Sequence[str], None] = '9aac18eb7bba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Índice para busca rápida de falhas por usuário e IP específico
    op.create_index(
        'ix_audit_logs_security_lookup', 
        'audit_logs', 
        ['action', 'username', 'ip_address', 'created_at']
    )
    # Índice para busca rápida de falhas globais por IP
    op.create_index(
        'ix_audit_logs_ip_lookup', 
        'audit_logs', 
        ['action', 'ip_address', 'created_at']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_audit_logs_ip_lookup', table_name='audit_logs')
    op.drop_index('ix_audit_logs_security_lookup', table_name='audit_logs')

"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-27 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'sensor_nodes',
        sa.Column('node_id', sa.String(length=64), primary_key=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('elevation_m', sa.Float(), nullable=True),
        sa.Column('node_type', sa.String(length=64), nullable=False, server_default='multiparameter'),
        sa.Column('installation_location', sa.String(length=256), nullable=True),
        sa.Column('firmware_version', sa.String(length=32), nullable=True, server_default='v1.0.0'),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('battery_pct', sa.Float(), nullable=True),
        sa.Column('connectivity_status', sa.String(length=32), nullable=False, server_default='OFFLINE'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_sensor_nodes_node_id', 'sensor_nodes', ['node_id'])

    op.create_table(
        'telemetry_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('event_id', sa.String(length=64), nullable=False),
        sa.Column('node_id', sa.String(length=64), sa.ForeignKey('sensor_nodes.node_id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('displacement_mm', sa.Float(), nullable=True),
        sa.Column('tilt_x_deg', sa.Float(), nullable=True),
        sa.Column('tilt_y_deg', sa.Float(), nullable=True),
        sa.Column('vector_tilt_deg', sa.Float(), nullable=True),
        sa.Column('velocity_mm_hr', sa.Float(), nullable=True),
        sa.Column('acceleration_mm_hr2', sa.Float(), nullable=True),
        sa.Column('vibration_rms_ms2', sa.Float(), nullable=True),
        sa.Column('peak_acceleration_ms2', sa.Float(), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('crack_width_mm', sa.Float(), nullable=True),
        sa.Column('battery_voltage_v', sa.Float(), nullable=True),
        sa.Column('battery_pct', sa.Float(), nullable=True),
        sa.Column('sensor_quality', sa.JSON(), nullable=True),
        sa.Column('data_source', sa.String(length=32), nullable=False, server_default='rest'),
        sa.Column('calibration_status', sa.String(length=32), nullable=True, server_default='nominal'),
        sa.Column('raw_metadata', sa.JSON(), nullable=True)
    )
    op.create_index('ix_telemetry_records_event_id', 'telemetry_records', ['event_id'], unique=True)
    op.create_index('ix_telemetry_records_node_id', 'telemetry_records', ['node_id'])
    op.create_index('ix_telemetry_records_timestamp', 'telemetry_records', ['timestamp'])
    op.create_index('idx_node_timestamp', 'telemetry_records', ['node_id', 'timestamp'])
    op.create_index('idx_node_seq', 'telemetry_records', ['node_id', 'sequence_number'])

    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_id', sa.String(length=64), nullable=False),
        sa.Column('node_id', sa.String(length=64), sa.ForeignKey('sensor_nodes.node_id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('triggering_rule', sa.String(length=128), nullable=False),
        sa.Column('acknowledged_by', sa.String(length=128), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledgement_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(length=128), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True)
    )
    op.create_index('ix_alerts_alert_id', 'alerts', ['alert_id'], unique=True)
    op.create_index('ix_alerts_node_id', 'alerts', ['node_id'])
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'])
    op.create_index('ix_alerts_severity', 'alerts', ['severity'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])

    op.create_table(
        'node_baselines',
        sa.Column('node_id', sa.String(length=64), sa.ForeignKey('sensor_nodes.node_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('calculation_period_start', sa.DateTime(), nullable=True),
        sa.Column('calculation_period_end', sa.DateTime(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('displacement_mean', sa.Float(), nullable=True),
        sa.Column('displacement_std', sa.Float(), nullable=True),
        sa.Column('tilt_x_mean', sa.Float(), nullable=True),
        sa.Column('tilt_x_std', sa.Float(), nullable=True),
        sa.Column('tilt_y_mean', sa.Float(), nullable=True),
        sa.Column('tilt_y_std', sa.Float(), nullable=True),
        sa.Column('temperature_mean', sa.Float(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('node_id', sa.String(length=64), nullable=True),
        sa.Column('alert_id', sa.String(length=64), nullable=True),
        sa.Column('actor', sa.String(length=128), nullable=False, server_default='system'),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('outcome', sa.String(length=32), nullable=False, server_default='SUCCESS'),
        sa.Column('details', sa.JSON(), nullable=True)
    )
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])

    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=64), primary_key=True),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('system_settings')
    op.drop_table('audit_events')
    op.drop_table('node_baselines')
    op.drop_table('alerts')
    op.drop_table('telemetry_records')
    op.drop_table('sensor_nodes')

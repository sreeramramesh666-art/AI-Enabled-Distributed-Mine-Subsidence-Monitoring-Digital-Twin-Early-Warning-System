"""add mine panels and test runs

Revision ID: 002_mine_panels_and_test_runs
Revises: 001_initial_schema
Create Date: 2026-10-28 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_mine_panels_and_test_runs'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create test_runs table
    op.create_table(
        'test_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('test_run_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('scenario', sa.String(length=64), nullable=False),
        sa.Column('test_conditions', sa.String(length=256), nullable=False),
        sa.Column('target_node_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='RUNNING'),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('intended_movement_mm', sa.Float(), nullable=True),
        sa.Column('reference_movement_mm', sa.Float(), nullable=True),
        sa.Column('sensor_reported_movement_mm', sa.Float(), nullable=True),
        sa.Column('measurement_error_mm', sa.Float(), nullable=True),
        sa.Column('detection_latency_sec', sa.Float(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_test_runs_test_run_id', 'test_runs', ['test_run_id'], unique=True)
    op.create_index('ix_test_runs_status', 'test_runs', ['status'])

    # 2. Add columns to sensor_nodes
    with op.batch_alter_table('sensor_nodes') as batch_op:
        batch_op.add_column(sa.Column('mine_panel', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('depth_m', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('extraction_method', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('geological_context', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('sampling_interval_sec', sa.Float(), nullable=False, server_default='5.0'))
        batch_op.add_column(sa.Column('last_calibration_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('calibration_status', sa.String(length=32), nullable=False, server_default='nominal'))
        batch_op.create_index('ix_sensor_nodes_mine_panel', ['mine_panel'])

    # 3. Add columns to telemetry_records
    with op.batch_alter_table('telemetry_records') as batch_op:
        batch_op.add_column(sa.Column('test_run_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('baseline_relative_displacement_mm', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('baseline_relative_tilt_deg', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('sensor_quality_state', sa.String(length=32), nullable=False, server_default='valid'))
        batch_op.add_column(sa.Column('is_interpolated', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.create_index('ix_telemetry_records_test_run_id', ['test_run_id'])

    # 4. Add columns to alerts
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.add_column(sa.Column('test_run_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('mine_panel', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('sensor_type', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('recommended_action', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('trend_evidence', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('investigated_by', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('investigated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('investigation_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('reopened_by', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('reopened_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reopen_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('lifecycle_history', sa.JSON(), nullable=True))
        batch_op.create_index('ix_alerts_mine_panel', ['mine_panel'])


def downgrade() -> None:
    with op.batch_alter_table('alerts') as batch_op:
        batch_op.drop_index('ix_alerts_mine_panel')
        batch_op.drop_column('lifecycle_history')
        batch_op.drop_column('reopen_notes')
        batch_op.drop_column('reopened_at')
        batch_op.drop_column('reopened_by')
        batch_op.drop_column('investigation_notes')
        batch_op.drop_column('investigated_at')
        batch_op.drop_column('investigated_by')
        batch_op.drop_column('trend_evidence')
        batch_op.drop_column('recommended_action')
        batch_op.drop_column('sensor_type')
        batch_op.drop_column('mine_panel')
        batch_op.drop_column('test_run_id')

    with op.batch_alter_table('telemetry_records') as batch_op:
        batch_op.drop_index('ix_telemetry_records_test_run_id')
        batch_op.drop_column('is_interpolated')
        batch_op.drop_column('sensor_quality_state')
        batch_op.drop_column('baseline_relative_tilt_deg')
        batch_op.drop_column('baseline_relative_displacement_mm')
        batch_op.drop_column('test_run_id')

    with op.batch_alter_table('sensor_nodes') as batch_op:
        batch_op.drop_index('ix_sensor_nodes_mine_panel')
        batch_op.drop_column('calibration_status')
        batch_op.drop_column('last_calibration_date')
        batch_op.drop_column('sampling_interval_sec')
        batch_op.drop_column('geological_context')
        batch_op.drop_column('extraction_method')
        batch_op.drop_column('depth_m')
        batch_op.drop_column('mine_panel')

    op.drop_table('test_runs')


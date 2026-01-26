"""Smart Alerts - AI-Powered Anomaly Detection

Revision ID: 20260126_2100
Revises: 20260126_2000
Create Date: 2026-01-26 21:00:00.000000

Epic 13: Smart Alerts
- Anomaly detection with ML models
- Predictive alerting
- Alert correlation and root cause analysis
- Noise reduction and suppression
- User feedback collection
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_2100'
down_revision = '20260126_2000'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create Smart Alerts infrastructure.
    
    Tables:
    1. smart_alert_models - Trained ML models and baselines
    2. anomaly_detections - Detected anomalies
    3. alert_predictions - Predictive alerts
    4. alert_correlations - Grouped related alerts
    5. alert_suppression_rules - Noise reduction rules
    6. alert_feedback - User feedback on alerts
    
    Enhanced:
    - alerts table with smart alert metadata
    """
    
    # =====================================================================
    # 1. smart_alert_models - ML Models and Baselines
    # =====================================================================
    op.create_table(
        'smart_alert_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('model_type', sa.String(50), nullable=False,
                  comment='isolation_forest, statistical, lstm, arima'),
        sa.Column('model_data', postgresql.JSONB, nullable=False,
                  comment='Serialized model parameters and weights'),
        sa.Column('baseline_stats', postgresql.JSONB, nullable=True,
                  comment='Mean, std, percentiles, seasonal patterns'),
        sa.Column('training_data_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_data_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accuracy_score', sa.Float, nullable=True,
                  comment='Model accuracy on validation data (0-1)'),
        sa.Column('false_positive_rate', sa.Float, nullable=True,
                  comment='False positive rate on validation data (0-1)'),
        sa.Column('last_trained_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()')),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active',
                  comment='active, deprecated, training, failed'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()')),
        
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        
        comment='Trained ML models for anomaly detection per device/metric'
    )
    
    # Indexes for smart_alert_models
    op.create_index('idx_smart_alert_models_device', 'smart_alert_models', ['device_id'])
    op.create_index('idx_smart_alert_models_metric', 'smart_alert_models', ['metric_name'])
    op.create_index('idx_smart_alert_models_status', 'smart_alert_models', ['status'])
    op.create_index('idx_smart_alert_models_device_metric', 'smart_alert_models', 
                    ['device_id', 'metric_name', 'status'])
    
    # =====================================================================
    # 2. anomaly_detections - Detected Anomalies
    # =====================================================================
    op.create_table(
        'anomaly_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()')),
        sa.Column('metric_value', sa.Float, nullable=False,
                  comment='Actual metric value that triggered anomaly'),
        sa.Column('expected_value', sa.Float, nullable=True,
                  comment='Model-predicted expected value'),
        sa.Column('expected_range_min', sa.Float, nullable=True,
                  comment='Lower bound of normal range'),
        sa.Column('expected_range_max', sa.Float, nullable=True,
                  comment='Upper bound of normal range'),
        sa.Column('anomaly_score', sa.Float, nullable=False,
                  comment='How anomalous (0-1, higher = more anomalous)'),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_type', sa.String(50), nullable=True,
                  comment='Which model detected this'),
        sa.Column('confidence', sa.Float, nullable=True,
                  comment='Model confidence (0-1)'),
        sa.Column('severity', sa.String(20), nullable=True,
                  comment='info, warning, error, critical'),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Created alert if anomaly was severe enough'),
        sa.Column('false_positive', sa.Boolean, nullable=True,
                  comment='User feedback - was this a false positive?'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}',
                  comment='Additional context, contributing factors'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['smart_alert_models.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='SET NULL'),
        
        comment='Record of all detected anomalies'
    )
    
    # Indexes for anomaly_detections
    op.create_index('idx_anomaly_detections_device', 'anomaly_detections', ['device_id'])
    op.create_index('idx_anomaly_detections_metric', 'anomaly_detections', ['metric_name'])
    op.create_index('idx_anomaly_detections_detected_at', 'anomaly_detections', 
                    [sa.text('detected_at DESC')])
    op.create_index('idx_anomaly_detections_score', 'anomaly_detections',
                    [sa.text('anomaly_score DESC')])
    op.create_index('idx_anomaly_detections_alert', 'anomaly_detections', ['alert_id'])
    op.create_index('idx_anomaly_detections_device_metric_time', 'anomaly_detections',
                    ['device_id', 'metric_name', sa.text('detected_at DESC')])
    
    # =====================================================================
    # 3. alert_predictions - Predictive Alerts
    # =====================================================================
    op.create_table(
        'alert_predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('prediction_type', sa.String(50), nullable=False,
                  comment='threshold_crossing, resource_exhaustion, trend_alert'),
        sa.Column('predicted_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'),
                  comment='When prediction was made'),
        sa.Column('will_occur_at', sa.DateTime(timezone=True), nullable=False,
                  comment='Predicted time when issue will occur'),
        sa.Column('confidence', sa.Float, nullable=False,
                  comment='Prediction confidence (0-1)'),
        sa.Column('current_value', sa.Float, nullable=True,
                  comment='Current metric value'),
        sa.Column('predicted_value', sa.Float, nullable=True,
                  comment='Predicted value at will_occur_at'),
        sa.Column('threshold_value', sa.Float, nullable=True,
                  comment='Threshold that will be crossed'),
        sa.Column('time_to_critical_minutes', sa.Integer, nullable=True,
                  comment='Minutes until critical state'),
        sa.Column('recommendation', sa.Text, nullable=True,
                  comment='What action to take'),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Created alert for this prediction'),
        sa.Column('actually_occurred', sa.Boolean, nullable=True,
                  comment='Validation - did it actually happen?'),
        sa.Column('accuracy_score', sa.Float, nullable=True,
                  comment='How accurate was the prediction'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}',
                  comment='Growth rate, trend data, etc.'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='SET NULL'),
        
        comment='Predictive alerts for future issues'
    )
    
    # Indexes for alert_predictions
    op.create_index('idx_alert_predictions_device', 'alert_predictions', ['device_id'])
    op.create_index('idx_alert_predictions_will_occur', 'alert_predictions',
                    [sa.text('will_occur_at')])
    op.create_index('idx_alert_predictions_confidence', 'alert_predictions',
                    [sa.text('confidence DESC')])
    op.create_index('idx_alert_predictions_created', 'alert_predictions',
                    [sa.text('created_at DESC')])
    op.create_index('idx_alert_predictions_type', 'alert_predictions', ['prediction_type'])
    
    # =====================================================================
    # 4. alert_correlations - Alert Grouping
    # =====================================================================
    op.create_table(
        'alert_correlations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('correlation_group_id', postgresql.UUID(as_uuid=True), nullable=False,
                  comment='Shared ID for all alerts in this correlation group'),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_root_cause', sa.Boolean, nullable=False, server_default='false',
                  comment='Is this alert the root cause?'),
        sa.Column('correlation_score', sa.Float, nullable=True,
                  comment='How related to root cause (0-1)'),
        sa.Column('correlation_type', sa.String(50), nullable=True,
                  comment='time_based, device_based, metric_based, causal'),
        sa.Column('detected_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('metadata', postgresql.JSONB, server_default='{}',
                  comment='Correlation evidence, dependency paths'),
        
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('correlation_group_id', 'alert_id',
                           name='uq_correlation_group_alert'),
        
        comment='Groups related alerts together with root cause identification'
    )
    
    # Indexes for alert_correlations
    op.create_index('idx_alert_correlations_group', 'alert_correlations',
                    ['correlation_group_id'])
    op.create_index('idx_alert_correlations_alert', 'alert_correlations', ['alert_id'])
    op.create_index('idx_alert_correlations_root_cause', 'alert_correlations',
                    ['is_root_cause'])
    op.create_index('idx_alert_correlations_detected', 'alert_correlations',
                    [sa.text('detected_at DESC')])
    
    # =====================================================================
    # 5. alert_suppression_rules - Noise Reduction
    # =====================================================================
    op.create_table(
        'alert_suppression_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('rule_type', sa.String(50), nullable=False,
                  comment='maintenance_window, known_issue, flapping, duplicate, threshold'),
        sa.Column('conditions', postgresql.JSONB, nullable=False,
                  comment='Match criteria: device_id, metric, severity, time_range, etc.'),
        sa.Column('action', sa.String(50), nullable=False, server_default='suppress',
                  comment='suppress, downgrade, group, snooze'),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0',
                  comment='Rule evaluation order (higher = first)'),
        sa.Column('active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alerts_suppressed', sa.Integer, nullable=False, server_default='0',
                  comment='Counter for how many alerts matched'),
        sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Auto-disable after this time'),
        
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                               ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        comment='Rules to suppress noisy or expected alerts'
    )
    
    # Indexes for alert_suppression_rules
    op.create_index('idx_alert_suppression_rules_active', 'alert_suppression_rules',
                    ['active'])
    op.create_index('idx_alert_suppression_rules_org', 'alert_suppression_rules',
                    ['organization_id'])
    op.create_index('idx_alert_suppression_rules_expires', 'alert_suppression_rules',
                    ['expires_at'])
    op.create_index('idx_alert_suppression_rules_priority', 'alert_suppression_rules',
                    [sa.text('priority DESC')])
    
    # =====================================================================
    # 6. alert_feedback - User Feedback Collection
    # =====================================================================
    op.create_table(
        'alert_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False,
                  comment='useful, false_positive, duplicate, noise, actionable'),
        sa.Column('rating', sa.Integer, nullable=True,
                  comment='1-5 stars for alert quality'),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('action_taken', sa.String(100), nullable=True,
                  comment='acknowledged, resolved, ignored, escalated'),
        sa.Column('time_to_acknowledge_seconds', sa.Integer, nullable=True,
                  comment='Time from alert creation to acknowledgment'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        
        sa.ForeignKeyConstraint(['alert_id'], ['alerts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        comment='User feedback on alert usefulness for model improvement'
    )
    
    # Indexes for alert_feedback
    op.create_index('idx_alert_feedback_alert', 'alert_feedback', ['alert_id'])
    op.create_index('idx_alert_feedback_user', 'alert_feedback', ['user_id'])
    op.create_index('idx_alert_feedback_type', 'alert_feedback', ['feedback_type'])
    op.create_index('idx_alert_feedback_created', 'alert_feedback',
                    [sa.text('created_at DESC')])
    op.create_index('idx_alert_feedback_rating', 'alert_feedback', ['rating'])
    
    # =====================================================================
    # 7. Enhance Existing alerts Table
    # =====================================================================
    # Add smart alert metadata columns to existing alerts table
    op.add_column('alerts', 
                  sa.Column('is_smart_alert', sa.Boolean, 
                           server_default='false', nullable=False,
                           comment='Generated by Smart Alerts system'))
    
    op.add_column('alerts',
                  sa.Column('anomaly_id', postgresql.UUID(as_uuid=True), nullable=True,
                           comment='Link to anomaly detection that triggered this'))
    
    op.add_column('alerts',
                  sa.Column('prediction_id', postgresql.UUID(as_uuid=True), nullable=True,
                           comment='Link to prediction that triggered this'))
    
    op.add_column('alerts',
                  sa.Column('priority_score', sa.Float, nullable=True,
                           comment='Calculated priority (0-100, higher = more urgent)'))
    
    op.add_column('alerts',
                  sa.Column('correlation_group_id', postgresql.UUID(as_uuid=True), nullable=True,
                           comment='Group ID if correlated with other alerts'))
    
    op.add_column('alerts',
                  sa.Column('noise_score', sa.Float, nullable=True,
                           comment='Likelihood this is noise (0-1, higher = more likely noise)'))
    
    op.add_column('alerts',
                  sa.Column('ml_confidence', sa.Float, nullable=True,
                           comment='ML model confidence (0-1)'))
    
    # Add foreign key constraints for new alert columns
    op.create_foreign_key(
        'fk_alerts_anomaly',
        'alerts', 'anomaly_detections',
        ['anomaly_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_alerts_prediction',
        'alerts', 'alert_predictions',
        ['prediction_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Indexes for enhanced alerts table
    op.create_index('idx_alerts_smart', 'alerts', ['is_smart_alert'])
    op.create_index('idx_alerts_priority', 'alerts',
                    [sa.text('priority_score DESC NULLS LAST')])
    op.create_index('idx_alerts_correlation_group', 'alerts', ['correlation_group_id'])
    op.create_index('idx_alerts_anomaly', 'alerts', ['anomaly_id'])
    op.create_index('idx_alerts_prediction', 'alerts', ['prediction_id'])
    
    print("✅ Smart Alerts database schema created successfully!")
    print("   - 6 new tables: models, anomalies, predictions, correlations, rules, feedback")
    print("   - Enhanced alerts table with 7 new columns")
    print("   - 30+ indexes for query performance")


def downgrade():
    """
    Remove Smart Alerts infrastructure.
    """
    
    # Drop foreign keys from alerts table first
    op.drop_constraint('fk_alerts_prediction', 'alerts', type_='foreignkey')
    op.drop_constraint('fk_alerts_anomaly', 'alerts', type_='foreignkey')
    
    # Drop indexes from alerts
    op.drop_index('idx_alerts_prediction', 'alerts')
    op.drop_index('idx_alerts_anomaly', 'alerts')
    op.drop_index('idx_alerts_correlation_group', 'alerts')
    op.drop_index('idx_alerts_priority', 'alerts')
    op.drop_index('idx_alerts_smart', 'alerts')
    
    # Remove columns from alerts
    op.drop_column('alerts', 'ml_confidence')
    op.drop_column('alerts', 'noise_score')
    op.drop_column('alerts', 'correlation_group_id')
    op.drop_column('alerts', 'priority_score')
    op.drop_column('alerts', 'prediction_id')
    op.drop_column('alerts', 'anomaly_id')
    op.drop_column('alerts', 'is_smart_alert')
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('alert_feedback')
    op.drop_table('alert_suppression_rules')
    op.drop_table('alert_correlations')
    op.drop_table('alert_predictions')
    op.drop_table('anomaly_detections')
    op.drop_table('smart_alert_models')
    
    print("✅ Smart Alerts database schema removed")

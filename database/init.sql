-- =============================================================================
-- Distributed Logging & Monitoring System — Database Initialization
-- =============================================================================
-- This script is executed by PostgreSQL on first container startup.
-- It creates the database, applies the schema, and seeds sample data.
-- =============================================================================

-- Apply the schema
\i /docker-entrypoint-initdb.d/schema.sql

-- =============================================================================
-- Seed sample log data for immediate dashboard visualization
-- =============================================================================
INSERT INTO logs (timestamp, service, level, endpoint, latency_ms, status_code, trace_id, request_id, message) VALUES
    (NOW() - INTERVAL '5 minutes',  'auth-service',         'INFO',    '/login',           45,   200, 'trace-001', 'req-001', 'User login successful'),
    (NOW() - INTERVAL '4 minutes',  'auth-service',         'WARNING', '/login',          180,   200, 'trace-002', 'req-002', 'Slow authentication response detected'),
    (NOW() - INTERVAL '4 minutes',  'payment-service',      'ERROR',   '/checkout',       420,   500, 'trace-003', 'req-003', 'Database connection timeout'),
    (NOW() - INTERVAL '3 minutes',  'order-service',        'INFO',    '/orders',          32,   201, 'trace-004', 'req-004', 'Order created successfully'),
    (NOW() - INTERVAL '3 minutes',  'notification-service', 'ERROR',   '/send-email',     890,   503, 'trace-005', 'req-005', 'Email service unavailable'),
    (NOW() - INTERVAL '2 minutes',  'inventory-service',    'INFO',    '/stock/check',     28,   200, 'trace-006', 'req-006', 'Stock check completed'),
    (NOW() - INTERVAL '2 minutes',  'payment-service',      'WARNING', '/refund',         340,   200, 'trace-007', 'req-007', 'Refund processing delayed'),
    (NOW() - INTERVAL '1 minute',   'auth-service',         'DEBUG',   '/token/refresh',   12,   200, 'trace-008', 'req-008', 'Token refresh initiated'),
    (NOW() - INTERVAL '1 minute',   'order-service',        'ERROR',   '/orders/cancel',  650,   500, 'trace-009', 'req-009', 'Order cancellation failed - item already shipped'),
    (NOW() - INTERVAL '30 seconds', 'inventory-service',    'INFO',    '/stock/update',    55,   200, 'trace-010', 'req-010', 'Inventory updated for SKU-12345'),
    (NOW() - INTERVAL '20 seconds', 'auth-service',         'INFO',    '/register',        95,   201, 'trace-011', 'req-011', 'New user registered'),
    (NOW() - INTERVAL '15 seconds', 'payment-service',      'INFO',    '/checkout',        78,   200, 'trace-012', 'req-012', 'Payment processed successfully'),
    (NOW() - INTERVAL '10 seconds', 'notification-service', 'INFO',    '/send-sms',        42,   200, 'trace-013', 'req-013', 'SMS notification sent'),
    (NOW() - INTERVAL '5 seconds',  'order-service',        'WARNING', '/orders',         290,   200, 'trace-014', 'req-014', 'High order volume detected'),
    (NOW(),                         'inventory-service',    'ERROR',   '/stock/reserve',  720,   500, 'trace-015', 'req-015', 'Failed to reserve stock - concurrent modification');

-- Refresh materialized view with initial data
REFRESH MATERIALIZED VIEW service_log_stats;

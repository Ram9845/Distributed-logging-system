"""
Constants used throughout the application.

Centralizes magic strings, service definitions, and configuration
constants to prevent duplication and ensure consistency.
"""

from typing import Final

# =============================================================================
# Microservice Definitions
# =============================================================================

SERVICES: Final[list[str]] = [
    "auth-service",
    "payment-service",
    "order-service",
    "notification-service",
    "inventory-service",
]

# =============================================================================
# Log Levels with weighted probabilities for realistic simulation
# =============================================================================

LOG_LEVELS: Final[list[str]] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

LOG_LEVEL_WEIGHTS: Final[dict[str, float]] = {
    "DEBUG": 0.10,
    "INFO": 0.50,
    "WARNING": 0.20,
    "ERROR": 0.15,
    "CRITICAL": 0.05,
}

# =============================================================================
# Service Endpoint Definitions
# =============================================================================

SERVICE_ENDPOINTS: Final[dict[str, list[str]]] = {
    "auth-service": [
        "/login",
        "/register",
        "/logout",
        "/token/refresh",
        "/password/reset",
        "/verify-email",
        "/oauth/callback",
    ],
    "payment-service": [
        "/checkout",
        "/refund",
        "/payment/status",
        "/webhook/stripe",
        "/invoices",
        "/payment-methods",
    ],
    "order-service": [
        "/orders",
        "/orders/cancel",
        "/orders/status",
        "/orders/history",
        "/cart",
        "/cart/checkout",
    ],
    "notification-service": [
        "/send-email",
        "/send-sms",
        "/send-push",
        "/templates",
        "/preferences",
        "/webhooks",
    ],
    "inventory-service": [
        "/stock/check",
        "/stock/update",
        "/stock/reserve",
        "/products",
        "/warehouses",
        "/stock/bulk-update",
    ],
}

# =============================================================================
# HTTP Status Codes by Level
# =============================================================================

STATUS_CODES_BY_LEVEL: Final[dict[str, list[int]]] = {
    "DEBUG": [200],
    "INFO": [200, 201, 204],
    "WARNING": [200, 301, 400, 408, 429],
    "ERROR": [400, 401, 403, 404, 500, 502, 503],
    "CRITICAL": [500, 502, 503, 504],
}

# =============================================================================
# Sample Error Messages by Service
# =============================================================================

ERROR_MESSAGES: Final[dict[str, dict[str, list[str]]]] = {
    "auth-service": {
        "ERROR": [
            "Invalid credentials provided",
            "Account locked after multiple failed attempts",
            "OAuth token expired",
            "Session validation failed",
            "Two-factor authentication timeout",
        ],
        "WARNING": [
            "Slow authentication response detected",
            "Rate limit approaching for IP range",
            "Deprecated auth endpoint called",
            "Token near expiration",
        ],
        "INFO": [
            "User login successful",
            "New user registered",
            "Token refresh initiated",
            "Password reset email sent",
            "OAuth callback processed",
        ],
    },
    "payment-service": {
        "ERROR": [
            "Database connection timeout",
            "Payment gateway unreachable",
            "Insufficient funds",
            "Card declined by issuer",
            "Stripe webhook signature mismatch",
        ],
        "WARNING": [
            "Refund processing delayed",
            "Payment retry attempt #2",
            "High transaction volume detected",
            "Currency conversion rate outdated",
        ],
        "INFO": [
            "Payment processed successfully",
            "Refund issued",
            "Invoice generated",
            "Payment method added",
            "Checkout completed",
        ],
    },
    "order-service": {
        "ERROR": [
            "Order cancellation failed - item already shipped",
            "Inventory check failed during order creation",
            "Order total mismatch",
            "Duplicate order detected",
            "Fulfillment service unavailable",
        ],
        "WARNING": [
            "High order volume detected",
            "Order processing delayed",
            "Partial order fulfillment",
            "Cart abandoned after timeout",
        ],
        "INFO": [
            "Order created successfully",
            "Order status updated to shipped",
            "Cart updated",
            "Order history retrieved",
            "Order confirmed",
        ],
    },
    "notification-service": {
        "ERROR": [
            "Email service unavailable",
            "SMS gateway timeout",
            "Push notification delivery failed",
            "Template rendering error",
            "Invalid recipient address",
        ],
        "WARNING": [
            "Email delivery delayed",
            "SMS rate limit reached",
            "Notification queue backlog growing",
            "Template version deprecated",
        ],
        "INFO": [
            "SMS notification sent",
            "Email delivered successfully",
            "Push notification sent",
            "Template updated",
            "Notification preferences saved",
        ],
    },
    "inventory-service": {
        "ERROR": [
            "Failed to reserve stock - concurrent modification",
            "Warehouse sync failed",
            "Stock count mismatch detected",
            "Bulk update transaction rolled back",
            "Product not found in catalog",
        ],
        "WARNING": [
            "Low stock alert for SKU-12345",
            "Warehouse capacity at 90%",
            "Stock sync delayed",
            "Inventory recount scheduled",
        ],
        "INFO": [
            "Stock check completed",
            "Inventory updated for SKU-12345",
            "Product added to catalog",
            "Warehouse capacity report generated",
            "Stock reservation confirmed",
        ],
    },
}

# =============================================================================
# Kafka Topics
# =============================================================================

KAFKA_TOPIC_LOGS: Final[str] = "service-logs"
KAFKA_TOPIC_ALERTS: Final[str] = "alerts"
KAFKA_TOPIC_DLQ: Final[str] = "dead-letter-logs"

# =============================================================================
# Alert Thresholds
# =============================================================================

ALERT_ERROR_THRESHOLD: Final[int] = 20          # Errors per minute
ALERT_LATENCY_THRESHOLD_MS: Final[float] = 500  # Milliseconds
ALERT_CPU_THRESHOLD_PCT: Final[float] = 80.0    # Percentage

# =============================================================================
# API Defaults
# =============================================================================

DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 500
DEFAULT_SIMULATION_COUNT: Final[int] = 100

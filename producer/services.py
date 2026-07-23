"""
Microservice definitions for the log producer.

Defines realistic service configurations including endpoints,
response characteristics, and error scenarios for each
simulated microservice.
"""

from dataclasses import dataclass, field


@dataclass
class ServiceConfig:
    """Configuration for a simulated microservice."""

    name: str
    endpoints: list[str]
    base_latency_ms: float = 30.0
    error_rate: float = 0.10
    warning_rate: float = 0.15
    info_messages: list[str] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    error_messages: list[str] = field(default_factory=list)
    debug_messages: list[str] = field(default_factory=list)


# =============================================================================
# Service Definitions
# =============================================================================

SERVICES: dict[str, ServiceConfig] = {
    "auth-service": ServiceConfig(
        name="auth-service",
        endpoints=[
            "/login", "/register", "/logout", "/token/refresh",
            "/password/reset", "/verify-email", "/oauth/callback",
        ],
        base_latency_ms=25.0,
        error_rate=0.08,
        info_messages=[
            "User login successful",
            "New user registered",
            "Token refresh initiated",
            "Password reset email sent",
            "OAuth callback processed",
            "User session created",
            "Email verification completed",
        ],
        warning_messages=[
            "Slow authentication response detected",
            "Rate limit approaching for IP range",
            "Deprecated auth endpoint called",
            "Token near expiration",
            "Multiple login attempts from same IP",
        ],
        error_messages=[
            "Invalid credentials provided",
            "Account locked after multiple failed attempts",
            "OAuth token expired",
            "Session validation failed",
            "Two-factor authentication timeout",
            "JWT signature verification failed",
        ],
        debug_messages=[
            "Auth middleware executed",
            "Token decoded successfully",
            "Session cache hit",
            "Password hash verified",
            "CORS preflight handled",
        ],
    ),
    "payment-service": ServiceConfig(
        name="payment-service",
        endpoints=[
            "/checkout", "/refund", "/payment/status",
            "/webhook/stripe", "/invoices", "/payment-methods",
        ],
        base_latency_ms=80.0,
        error_rate=0.12,
        info_messages=[
            "Payment processed successfully",
            "Refund issued",
            "Invoice generated",
            "Payment method added",
            "Checkout completed",
            "Stripe webhook received",
        ],
        warning_messages=[
            "Refund processing delayed",
            "Payment retry attempt #2",
            "High transaction volume detected",
            "Currency conversion rate outdated",
            "Payment method expiring soon",
        ],
        error_messages=[
            "Database connection timeout",
            "Payment gateway unreachable",
            "Insufficient funds",
            "Card declined by issuer",
            "Stripe webhook signature mismatch",
            "Transaction rollback due to timeout",
        ],
        debug_messages=[
            "Payment intent created",
            "Idempotency key checked",
            "Currency conversion applied",
            "Fraud check passed",
            "Payment confirmation sent",
        ],
    ),
    "order-service": ServiceConfig(
        name="order-service",
        endpoints=[
            "/orders", "/orders/cancel", "/orders/status",
            "/orders/history", "/cart", "/cart/checkout",
        ],
        base_latency_ms=45.0,
        error_rate=0.10,
        info_messages=[
            "Order created successfully",
            "Order status updated to shipped",
            "Cart updated",
            "Order history retrieved",
            "Order confirmed",
            "Order tracking updated",
        ],
        warning_messages=[
            "High order volume detected",
            "Order processing delayed",
            "Partial order fulfillment",
            "Cart abandoned after timeout",
            "Inventory reservation expiring",
        ],
        error_messages=[
            "Order cancellation failed - item already shipped",
            "Inventory check failed during order creation",
            "Order total mismatch",
            "Duplicate order detected",
            "Fulfillment service unavailable",
            "Cart checkout validation failed",
        ],
        debug_messages=[
            "Order validation passed",
            "Cart items serialized",
            "Shipping rates calculated",
            "Tax computation completed",
            "Order event published",
        ],
    ),
    "notification-service": ServiceConfig(
        name="notification-service",
        endpoints=[
            "/send-email", "/send-sms", "/send-push",
            "/templates", "/preferences", "/webhooks",
        ],
        base_latency_ms=60.0,
        error_rate=0.15,
        info_messages=[
            "SMS notification sent",
            "Email delivered successfully",
            "Push notification sent",
            "Template updated",
            "Notification preferences saved",
            "Webhook delivered",
        ],
        warning_messages=[
            "Email delivery delayed",
            "SMS rate limit reached",
            "Notification queue backlog growing",
            "Template version deprecated",
            "Push token expiring",
        ],
        error_messages=[
            "Email service unavailable",
            "SMS gateway timeout",
            "Push notification delivery failed",
            "Template rendering error",
            "Invalid recipient address",
            "Webhook delivery failed after retries",
        ],
        debug_messages=[
            "Template compiled",
            "Recipient list resolved",
            "Email content sanitized",
            "Push payload constructed",
            "Delivery receipt received",
        ],
    ),
    "inventory-service": ServiceConfig(
        name="inventory-service",
        endpoints=[
            "/stock/check", "/stock/update", "/stock/reserve",
            "/products", "/warehouses", "/stock/bulk-update",
        ],
        base_latency_ms=35.0,
        error_rate=0.09,
        info_messages=[
            "Stock check completed",
            "Inventory updated for SKU-12345",
            "Product added to catalog",
            "Warehouse capacity report generated",
            "Stock reservation confirmed",
            "Bulk update completed",
        ],
        warning_messages=[
            "Low stock alert for SKU-12345",
            "Warehouse capacity at 90%",
            "Stock sync delayed",
            "Inventory recount scheduled",
            "Supplier delivery delayed",
        ],
        error_messages=[
            "Failed to reserve stock - concurrent modification",
            "Warehouse sync failed",
            "Stock count mismatch detected",
            "Bulk update transaction rolled back",
            "Product not found in catalog",
            "Inventory database lock timeout",
        ],
        debug_messages=[
            "Stock level cached",
            "Warehouse connection pool refreshed",
            "SKU lookup completed",
            "Reservation lock acquired",
            "Inventory snapshot created",
        ],
    ),
}

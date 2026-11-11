# Python-Flask_FinancialLedger-TransactionOperations

**MK7 Luxury Fashion & Financial Ledger Platform** — An end-to-end Python Flask e-commerce system featuring an immutable store credit wallet ledger, National Bank of Cambodia (NBC) Bakong KHQR integration, dual-currency engine (KHR/USD), 4-hour cancellation auto-refunds, and automated Telegram operations.

## Core Features & Architecture

- **Framework**: Python 3.12 / Flask 3.x / SQLAlchemy
- **National Bank of Cambodia (NBC) Bakong KHQR**: Dynamic 30-minute EMVCo QR code generation with base64 PNG rendering, 32-character MD5 transaction fingerprinting, and automated payment verification polling.
- **Authoritative KHR Dual-Currency Engine**: Cambodian Riel (`KHR ៛`) as the authoritative database currency with real-time US Dollar (`USD $`) estimation across all storefront cards, checkout bills, and admin dashboards.
- **Customer Wallet & Split Payments**: Store credit balance management with 3-way smart checkout (100% Wallet, 100% Bakong KHQR, or Split Payment applying balance first).
- **Immutable Financial Ledger**: Every credit and debit creates an immutable record in `wallet_transactions` with `balance_after`, transaction type, order reference, and audit trail.
- **4-Hour Cancellation Grace Period**: Self-service cancellation within 4 hours featuring automated 100% store credit refunds and instant warehouse inventory restock.
- **Real-Time Telegram Operations Dispatcher**: Automated alerts to `@SV26_Shop` for new orders, cancellations, HTTP 500 runtime errors, and HTTP 429 rate limit security lockouts.
- **Admin Management Portal**: Real-time Net Realized Revenue, warehouse stock valuation, fulfillment tracking, structured order inspection modals, and product/brand/category CRUD.
- **Security & Concurrency**: Flask-Limiter brute-force protection, ProxyFix client IP extraction across reverse proxies, CSRF protection, and shared-memory Gunicorn deployment.

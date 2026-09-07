# RetailMate Backend API Contract

Base URL: `http://localhost:8002`

The backend is the deterministic authority for transactional data and policy decisions. SQLite is the authoritative live inventory source; inventory is queried from SQLite on every request and is not cached in RAG or an LLM.

All errors use this shape directly, without a FastAPI `detail` wrapper:

```json
{"success": false, "error": {"code": "ERROR_CODE", "message": "Human-readable explanation"}}
```

## Products

| Method | Path | Purpose | Important errors |
|---|---|---|---|
| GET | `/api/products` | List active products; supports `search`, `category`, `brand`, and `active` query filters. Search covers name, SKU, brand, category, and description. | `422` invalid query |
| POST | `/api/products` | Create a product. Body: `sku`, `name`, `category`, `brand`, `price`; optional `description`, `image_url`, `active`. | `409 DUPLICATE_SKU`, `422` validation |
| GET | `/api/products/{id}` | Get one product. | `404 PRODUCT_NOT_FOUND` |
| PUT | `/api/products/{id}` | Update any supplied product fields. | `404`, `409 DUPLICATE_SKU`, `422` |
| DELETE | `/api/products/{id}` | Deactivate a product while preserving history. | `404`, `500` |

## Inventory

| Method | Path | Purpose | Important errors |
|---|---|---|---|
| GET | `/api/inventory` | Read current SQLite inventory; supports `product_id` and `low_stock`. | `422` invalid query |
| GET | `/api/inventory/{product_id}` | Read one inventory record. | `404 INVENTORY_NOT_FOUND` |
| PUT | `/api/inventory/{product_id}` | Update supplied `quantity`, `aisle`, or `shelf`; quantity must be non-negative. | `404`, `400 NO_UPDATE_FIELDS`, `422` |

## Orders

| Method | Path | Purpose | Important errors |
|---|---|---|---|
| GET | `/api/orders/{order_number}` | Return order number, customer, delivery date, status, and item product IDs, quantities, and unit prices. | `404 ORDER_NOT_FOUND` |

## Returns and Exchanges

Eligibility bodies contain `order_number`, `product_id`, and optional `reason`, `product_identifier`, `accessories_complete`, `product_unused`, `product_undamaged`, `packaging_undamaged`, `device_unlocked`, `device_formatted`, `icloud_lock_disabled`, and `installation_done_by_authorized_person`. Create bodies also require `reason`.

| Method | Path | Purpose | Important errors |
|---|---|---|---|
| POST | `/api/returns/check-eligibility` | Run the deterministic return policy engine. | `422` validation |
| POST | `/api/returns` | Run eligibility and create a ticket only for `ELIGIBLE`; transactionally commits the ticket. | `400 RETURN_NOT_ELIGIBLE`, `409`, `422` |
| GET | `/api/returns` | List return tickets. | `500` |
| GET | `/api/returns/{ticket_number}` | Get one return ticket. | `404 RETURN_TICKET_NOT_FOUND` |
| POST | `/api/exchanges/check-eligibility` | Run the same engine with `requested_action=EXCHANGE`. | `422` validation |
| POST | `/api/exchanges` | Create an exchange ticket only for `ELIGIBLE`. | `400 EXCHANGE_NOT_ELIGIBLE`, `409`, `422` |
| GET | `/api/exchanges` | List exchange tickets. | `500` |
| GET | `/api/exchanges/{ticket_number}` | Get one exchange ticket. | `404 EXCHANGE_TICKET_NOT_FOUND` |

Eligibility responses contain `status`, `eligible`, `message`, and `reasons`. The only states are:

- `ELIGIBLE`: all required policy conditions pass.
- `INELIGIBLE`: a known policy condition fails, the order/item is missing, the window expired, or the action is not allowed.
- `AMBIGUOUS`: required information or a unique policy rule is missing.

The backend deterministic policy engine is the final authority. Product-specific rules take priority over category rules, and category rules take priority over general rules. No LLM may override the result.

## Health

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{ "status": "ok" }` |
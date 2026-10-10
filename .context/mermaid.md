erDiagram
 direction TB
 USER_ACCOUNT ||--o{ SUPPLIER_MEMBERSHIP : authenticates
 SUPPLIER ||--o{ SUPPLIER_MEMBERSHIP : grants_access
 PRODUCT ||--o{ PRODUCT_VARIANT : has
 SUPPLIER ||--o{ SUPPLIER_VARIANT : supplies
 PRODUCT_VARIANT ||--o{ SUPPLIER_VARIANT : assigned_to
 SUPPLIER_VARIANT ||--|| INVENTORY_BALANCE : tracks
 SUPPLIER_VARIANT ||--o{ STOCK_RESERVATION : holds
 INVENTORY_BALANCE ||--o{ STOCK_EVENT : records
 USER_ACCOUNT {
 uuid id PK
 text auth_subject UK
 }
 SUPPLIER {
 uuid id PK
 text name
 text status
 }
 SUPPLIER_MEMBERSHIP {
 uuid user_id FK
 uuid supplier_id FK
 boolean active
 }
 PRODUCT {
 uuid id PK
 text title
 text status
 text fulfillment_type
 }
 PRODUCT_VARIANT {
 uuid id PK
 uuid product_id FK
 text sku UK
 text size
 text color
 bigint retail_price_minor
 }
 SUPPLIER_VARIANT {
 uuid id PK
 uuid supplier_id FK
 uuid variant_id FK
 boolean active
 }
 INVENTORY_BALANCE {
 uuid supplier_variant_id PK,FK
 int on_hand
 bigint version
 timestamptz last_counted_at
 }
 STOCK_RESERVATION {
 uuid id PK
 uuid supplier_variant_id FK
 uuid order_line_id
 int quantity
 text stage
 timestamptz supplier_accepted_at
 timestamptz instructions_sent_at
 timestamptz payment_due_at
 timestamptz closed_at
 }
 STOCK_EVENT {
 uuid id PK
 uuid supplier_variant_id FK
 uuid actor_user_id FK
 int previous_on_hand
 int new_on_hand
 text reason
 timestamptz occurred_at
 }
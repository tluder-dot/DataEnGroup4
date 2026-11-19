# Data governance

How Group 4 classifies the data in its platform. This page holds the
classification policy: every column of every layer, its class, its owner and the
reason. Decision on why access is granted by class:
[ADR 0010](adr/0010-data-classification.md). Column meanings:
[data dictionary](data-dictionary.md).

The column tables further down are generated from BigQuery metadata by
[`infra/governance/classify_columns.py`](../infra/governance/classify_columns.py).
The classes, the rules and the owners on this page are written by hand.

## The classes

Seven classes, ordered from the least to the most sensitive:

`public` < `internal` < `pii.location` < `pii.identifier` < `pii.contact` < `unclassified` < `secret`

The order runs from what harms nobody if it leaks to what harms most: a
location narrows a person to a place, an identifier points to one person,
contact data reaches that person directly, and unclassified text is handled at
least like contact data because nobody can say what it holds.

| Class | Means | Examples |
|---|---|---|
| `public` | Can be read by anyone without risk | Nothing in the platform today: we publish none of it |
| `internal` | Not about a person, for the group and its consumers only | Prices, quantities, dates, product keys |
| `pii.location` | Says where a person lives, less precisely than the street | City, region, postcode, country on a row that carries an identifier |
| `pii.identifier` | A stable ID that leads to one person | `buyer_id`, `c_id`, `seller_id`, `address_id` |
| `pii.contact` | Identifies or reaches a person directly | Name, email, phone, street address, billing address |
| `unclassified` | Free text and uploads: we cannot tell what they hold, so they are treated at least as `pii.contact` | `review_text`, `r_desc`, `title`, `raw` |
| `secret` | Must never enter the platform | `customer.pwd`, `payment_details.card_no`, `cvv` |

### Rules that decide a class

1. **A pseudonymous identifier is personal data.** `buyer_id` is a pseudonym, but
   under the GDPR it stays personal data (Art. 4(5)), because anyone can join it
   to other tables (orders, addresses, reviews) and find the person again.
2. **The class of a country depends on the identifier on its row.** `country` is
   `pii.location` when it sits on the same row as an identifier (`buyer_id`,
   `c_id`, `address_id`; for example `int_buyer_country`), and `internal` when it
   is aggregated or looked up with no identifier on the row (gold, `country_codes`).
3. **Free text is `unclassified`, never assumed clean.** A reader who knows which
   columns we cannot vouch for can do something about it.
4. **A class describes the column, not the join.** An `order_id` is `internal`
   even though silver can join it to a `buyer_id`; the limits section says what
   that means for gold.

## Owners

An owner is a person who can answer questions about a column.

| Owner | Answers for | Why |
|---|---|---|
| Till | Bronze tables from the export and the extractor, silver and gold | Landed the bronze tables, wrote the extractor and the dbt models |
| Jane | `clickstream_external` and the dead letter queue | Wrote the clickstream consumer and its schema |
| Enzo | `g04_warehouse` | Built the native tables and the materialised views |
| Evaluna | The classes themselves and this page | Step 10 |

## Never ingested

These columns are not in the platform, and this is why no column below is
`secret`. They were deselected at extraction
([ADR 0001](adr/0001-target-architecture.md)). None of the three names appears in
a column of `g04_bronze_1` (the metadata read in the summary below).

| Column | Class | Why it never enters |
|---|---|---|
| `customer.pwd` | `secret` | Plaintext password |
| `payment_details.card_no` | `secret` | Card number |
| `payment_details.cvv` | `secret` | Card security code |

<!-- BEGIN GENERATED: infra/governance/classify_columns.py -->

## Summary

Columns per class, read from the metadata of the four datasets on 2026-11-19, no row read.

| Layer | Tables and views | Columns | `public` | `internal` | `pii.location` | `pii.identifier` | `pii.contact` | `unclassified` | `secret` |
|---|---|---|---|---|---|---|---|---|---|
| Bronze | 35 | 176 | 0 | 129 | 8 | 21 | 11 | 7 | 0 |
| Silver | 14 | 60 | 0 | 47 | 2 | 9 | 0 | 2 | 0 |
| Gold | 5 | 31 | 0 | 31 | 0 | 0 | 0 | 0 | 0 |
| Warehouse | 11 | 56 | 0 | 46 | 1 | 6 | 0 | 3 | 0 |

Not in this count: the dead letter queue files `bronze/_dlq/clickstream/`, which are in the bucket and not in BigQuery. Their `raw` column is `unclassified`, owner Jane.

## The classification, column by column

`csv_index` is the export's row number: it is on every table read from the export, and is `internal` each time.

### Bronze: `g04_bronze_1`

#### `g04_bronze_1.buyer_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |

#### `g04_bronze_1.carrier_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `carrier_id` | STRING | `internal` | Key; no personal content on its own |
| `carrier_name` | STRING | `internal` | No personal content |

#### `g04_bronze_1.cart_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `cart_id` | STRING | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `total_qty` | STRING | `internal` | No personal content |
| `total_price` | STRING | `internal` | Amount or rating; no personal content |

#### `g04_bronze_1.cart_items_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `cart_id` | STRING | `internal` | Key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |

#### `g04_bronze_1.category_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `category_id` | INT64 | `internal` | Key; no personal content on its own |
| `name` | STRING | `internal` | No personal content |
| `c_desc` | STRING | `internal` | No personal content |

#### `g04_bronze_1.clickstream_external` (external table, owner: Jane)

| Column | Type | Class | Why |
|---|---|---|---|
| `schema_version` | INT64 | `internal` | Key; no personal content on its own |
| `event_id` | STRING | `internal` | Key; no personal content on its own |
| `event_type` | STRING | `internal` | No personal content |
| `event_time` | STRING | `internal` | Date or time; no personal content |
| `emitted_at` | STRING | `internal` | Date or time; no personal content |
| `session_id` | STRING | `internal` | Random UUID per visit; follows no one from one visit to the next |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `price` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `qty` | FLOAT64 | `internal` | No personal content |
| `order_id` | FLOAT64 | `internal` | Order key; no personal content on its own |
| `payment_method` | STRING | `internal` | No personal content |
| `amount` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `currency` | STRING | `internal` | No personal content |
| `items` | ARRAY<STRUCT<p_id STRING, qty INT64, price FLOAT64>> | `internal` | No personal content |
| `dt` | DATE | `internal` | Date or time; no personal content |

#### `g04_bronze_1.customer_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `fname` | STRING | `pii.contact` | First name; directly identifies a person |
| `lname` | STRING | `pii.contact` | Last name; directly identifies a person |
| `phone` | STRING | `pii.contact` | Phone number; reaches a person directly |
| `email` | STRING | `pii.contact` | Email address; reaches a person directly |

#### `g04_bronze_1.customer_payment_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `is_default` | STRING | `internal` | No personal content |

#### `g04_bronze_1.customer_shipping_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `is_default` | STRING | `internal` | No personal content |

#### `g04_bronze_1.customer_shipping_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `is_default` | STRING | `internal` | No personal content |

#### `g04_bronze_1.daily_deals_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `deal_date` | STRING | `internal` | Date or time; no personal content |
| `discount` | STRING | `internal` | Amount or rating; no personal content |

#### `g04_bronze_1.discount_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `discount_id` | INT64 | `internal` | Key; no personal content on its own |
| `discount_name` | STRING | `internal` | No personal content |
| `d_desc` | STRING | `internal` | No personal content |
| `discount_amt` | STRING | `internal` | Amount or rating; no personal content |

#### `g04_bronze_1.order_items_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | FLOAT64 | `internal` | Amount or rating; no personal content |

#### `g04_bronze_1.order_items_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | FLOAT64 | `internal` | Amount or rating; no personal content |

#### `g04_bronze_1.orders_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `discount_id` | INT64 | `internal` | Key; no personal content on its own |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `order_year` | INT64 | `internal` | Date or time; no personal content |

#### `g04_bronze_1.orders_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `discount_id` | INT64 | `internal` | Key; no personal content on its own |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `order_year` | INT64 | `internal` | Date or time; no personal content |

#### `g04_bronze_1.payment_details_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `expiry_date` | STRING | `pii.contact` | No card class in the scale; card data linked to a customer, so it takes the strictest personal-data class |
| `billing_address` | STRING | `pii.contact` | Billing address; reaches a person directly |

#### `g04_bronze_1.payment_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `transaction_id` | STRING | `internal` | Key; no personal content on its own |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `amount` | STRING | `internal` | Amount or rating; no personal content |
| `method` | STRING | `internal` | No personal content |
| `status` | STRING | `internal` | No personal content |
| `created_at` | STRING | `internal` | Date or time; no personal content |

#### `g04_bronze_1.product_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `p_name` | STRING | `internal` | Short product title; no personal content expected |
| `p_desc` | STRING | `unclassified` | Free text written by sellers; may contain anything |
| `price` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `qty` | INT64 | `internal` | No personal content |
| `category_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.product_images_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `p_image` | STRING | `internal` | No personal content |

#### `g04_bronze_1.product_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `p_name` | STRING | `internal` | Short product title; no personal content expected |
| `p_desc` | STRING | `unclassified` | Free text written by sellers; may contain anything |
| `price` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `qty` | INT64 | `internal` | No personal content |
| `category_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.product_reviews_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.product_reviews_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.returns_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `return_id` | STRING | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |

#### `g04_bronze_1.review_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `r_desc` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `title` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `rating` | INT64 | `internal` | No personal content |
| `seller_product_flag` | STRING | `internal` | No personal content |

#### `g04_bronze_1.review_images_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |
| `review_img` | STRING | `unclassified` | Link to an image a reviewer uploaded; a photo can show anything |

#### `g04_bronze_1.review_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `review_id` | INT64 | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `r_desc` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `title` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `rating` | INT64 | `internal` | No personal content |
| `seller_product_flag` | STRING | `internal` | No personal content |

#### `g04_bronze_1.seller_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `seller_id` | STRING | `pii.identifier` | Pseudonymous ID of a seller, who may be a person |
| `seller_type` | STRING | `internal` | No personal content |
| `seller_name` | STRING | `pii.contact` | Name of a seller, who may be a person |

#### `g04_bronze_1.seller_products_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `seller_id` | STRING | `pii.identifier` | Pseudonymous ID of a seller, who may be a person |
| `p_id` | STRING | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.seller_reviews_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `seller_id` | STRING | `pii.identifier` | Pseudonymous ID of a seller, who may be a person |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_bronze_1.shipment_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `shipping_id` | STRING | `internal` | Key; no personal content on its own |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `carrier_id` | STRING | `internal` | Key; no personal content on its own |
| `shipment_type` | STRING | `internal` | No personal content |
| `status` | STRING | `internal` | No personal content |
| `est_delivery_date` | STRING | `internal` | Date or time; no personal content |
| `actual_delivery_date` | STRING | `internal` | Date or time; no personal content |

#### `g04_bronze_1.shipping_details_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `street_address` | STRING | `pii.contact` | Street address; reaches a person directly |
| `city` | STRING | `pii.location` | Town where a person lives |
| `state` | STRING | `pii.location` | Region where a person lives |
| `zip` | STRING | `pii.location` | Postcode where a person lives |
| `country` | STRING | `pii.location` | Country on a row that carries an identifier: where one person lives (rule: the class depends on the identifier on the row) |
| `phone` | STRING | `pii.contact` | Phone number; reaches a person directly |

#### `g04_bronze_1.shipping_details_live` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `street_address` | STRING | `pii.contact` | Street address; reaches a person directly |
| `city` | STRING | `pii.location` | Town where a person lives |
| `state` | STRING | `pii.location` | Region where a person lives |
| `zip` | STRING | `pii.location` | Postcode where a person lives |
| `country` | STRING | `pii.location` | Country on a row that carries an identifier: where one person lives (rule: the class depends on the identifier on the row) |
| `phone` | STRING | `pii.contact` | Phone number; reaches a person directly |

#### `g04_bronze_1.subscription_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `subscription_id` | STRING | `internal` | Key; no personal content on its own |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `start_date` | STRING | `internal` | Date or time; no personal content |
| `end_date` | STRING | `internal` | Date or time; no personal content |

#### `g04_bronze_1.wishlist_item_external` (external table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `product_id` | STRING | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |

### Silver: `g04_silver`

#### `g04_silver.country_codes` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `country` | STRING | `internal` | Country with no identifier on the row (aggregated or lookup); no personal content |
| `country_code` | STRING | `internal` | No personal content |

#### `g04_silver.int_buyer_country` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `country` | STRING | `pii.location` | Country on a row that carries an identifier: where one person lives (rule: the class depends on the identifier on the row) |

#### `g04_silver.int_order_items` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | NUMERIC | `internal` | Amount or rating; no personal content |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |

#### `g04_silver.int_orders` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |

#### `g04_silver.int_product_ratings` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `n_reviews` | INT64 | `internal` | No personal content |
| `avg_rating` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `has_rating_above_four` | BOOL | `internal` | No personal content |

#### `g04_silver.stg_category` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `category_id` | INT64 | `internal` | Key; no personal content on its own |
| `category_name` | STRING | `internal` | No personal content |

#### `g04_silver.stg_clickstream` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `event_id` | STRING | `internal` | Key; no personal content on its own |
| `event_type` | STRING | `internal` | No personal content |
| `event_time` | TIMESTAMP | `internal` | Date or time; no personal content |
| `emitted_at` | TIMESTAMP | `internal` | Date or time; no personal content |
| `session_id` | STRING | `internal` | Random UUID per visit; follows no one from one visit to the next |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `price` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `qty` | INT64 | `internal` | No personal content |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `payment_method` | STRING | `internal` | No personal content |
| `amount` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `currency` | STRING | `internal` | No personal content |
| `items` | ARRAY<STRUCT<p_id STRING, qty INT64, price FLOAT64>> | `internal` | No personal content |

#### `g04_silver.stg_customer_shipping` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `is_default` | BOOL | `internal` | No personal content |

#### `g04_silver.stg_order_items` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | NUMERIC | `internal` | Amount or rating; no personal content |

#### `g04_silver.stg_orders` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |

#### `g04_silver.stg_product` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `product_name` | STRING | `internal` | Short product title; no personal content expected |
| `price` | NUMERIC | `internal` | Amount or rating; no personal content |
| `stock_qty` | INT64 | `internal` | No personal content |
| `category_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_silver.stg_product_reviews` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_silver.stg_review` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `review_id` | INT64 | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `review_text` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `review_title` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `rating` | INT64 | `internal` | No personal content |

#### `g04_silver.stg_shipping_details` (view, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `country` | STRING | `pii.location` | Country on a row that carries an identifier: where one person lives (rule: the class depends on the identifier on the row) |

### Gold: `g04_gold`

#### `g04_gold.dim_country` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `country` | STRING | `internal` | Country with no identifier on the row (aggregated or lookup); no personal content |
| `country_code` | STRING | `internal` | No personal content |
| `n_buyers` | INT64 | `internal` | No personal content |

#### `g04_gold.dim_date` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `year` | INT64 | `internal` | Date or time; no personal content |
| `quarter` | INT64 | `internal` | Date or time; no personal content |
| `month` | INT64 | `internal` | Date or time; no personal content |
| `iso_week` | INT64 | `internal` | Date or time; no personal content |
| `day_of_week` | STRING | `internal` | Date or time; no personal content |
| `is_weekend` | BOOL | `internal` | Date or time; no personal content |

#### `g04_gold.dim_product` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `product_name` | STRING | `internal` | Short product title; no personal content expected |
| `category_name` | STRING | `internal` | No personal content |
| `price` | NUMERIC | `internal` | Amount or rating; no personal content |
| `n_reviews` | INT64 | `internal` | No personal content |
| `avg_rating` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `has_rating_above_four` | BOOL | `internal` | No personal content |

#### `g04_gold.fct_daily_demand` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `demand_key` | STRING | `internal` | Key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `country` | STRING | `internal` | Country with no identifier on the row (aggregated or lookup); no personal content |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `units_sold` | INT64 | `internal` | No personal content |
| `gross_revenue` | NUMERIC | `internal` | Amount or rating; no personal content |
| `order_count` | INT64 | `internal` | No personal content |

#### `g04_gold.fct_order_items` (table, owner: Till)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `country` | STRING | `internal` | Country with no identifier on the row (aggregated or lookup); no personal content |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | NUMERIC | `internal` | Amount or rating; no personal content |
| `line_revenue` | NUMERIC | `internal` | Amount or rating; no personal content |

### Warehouse: `g04_warehouse`

#### `g04_warehouse.customer_shipping` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `c_id` | STRING | `pii.identifier` | Pseudonymous ID of a customer; joins to the buyer or seller it equals |
| `is_default` | STRING | `internal` | No personal content |

#### `g04_warehouse.daily_demand_country_mv` (materialised view, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `country` | STRING | `internal` | Country with no identifier on the row (aggregated or lookup); no personal content |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `units` | INT64 | `internal` | No personal content |
| `revenue` | FLOAT64 | `internal` | Amount or rating; no personal content |

#### `g04_warehouse.daily_demand_mv` (materialised view, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `units` | INT64 | `internal` | No personal content |
| `revenue` | FLOAT64 | `internal` | Amount or rating; no personal content |

#### `g04_warehouse.monthly_demand_mv` (materialised view, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `month` | DATE | `internal` | Date or time; no personal content |
| `units` | INT64 | `internal` | No personal content |
| `revenue` | FLOAT64 | `internal` | Amount or rating; no personal content |

#### `g04_warehouse.order_items_month_pc` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `qty` | INT64 | `internal` | No personal content |
| `price_at_purchase` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `order_date` | DATE | `internal` | Date or time; no personal content |

#### `g04_warehouse.orders_month` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `discount_id` | INT64 | `internal` | Key; no personal content on its own |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `order_year` | INT64 | `internal` | Date or time; no personal content |

#### `g04_warehouse.orders_plain` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `order_id` | INT64 | `internal` | Order key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `discount_id` | INT64 | `internal` | Key; no personal content on its own |
| `payment_id` | INT64 | `internal` | Key; no personal content on its own |
| `order_date` | DATE | `internal` | Date or time; no personal content |
| `order_year` | INT64 | `internal` | Date or time; no personal content |

#### `g04_warehouse.product` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `p_name` | STRING | `internal` | Short product title; no personal content expected |
| `p_desc` | STRING | `unclassified` | Free text written by sellers; may contain anything |
| `price` | FLOAT64 | `internal` | Amount or rating; no personal content |
| `qty` | INT64 | `internal` | No personal content |
| `category_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_warehouse.product_reviews` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `p_id` | STRING | `internal` | Key; no personal content on its own |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |

#### `g04_warehouse.review` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `review_id` | INT64 | `internal` | Key; no personal content on its own |
| `buyer_id` | STRING | `pii.identifier` | Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews |
| `r_desc` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `title` | STRING | `unclassified` | Free text typed by a reviewer; may contain anything |
| `rating` | INT64 | `internal` | No personal content |
| `seller_product_flag` | STRING | `internal` | No personal content |

#### `g04_warehouse.shipping_details` (table, owner: Enzo)

| Column | Type | Class | Why |
|---|---|---|---|
| `csv_index` | INT64 | `internal` | Row number the export added; no meaning |
| `address_id` | INT64 | `pii.identifier` | Key of one customer's address; joins to the customer, so it points to one person |
| `country` | STRING | `pii.location` | Country on a row that carries an identifier: where one person lives (rule: the class depends on the identifier on the row) |

<!-- END GENERATED -->

## Limits of this classification

- **Gold is not anonymous.** It holds no identifier, so its columns are
  `internal`. But `fct_order_items.order_id` is also in silver (`int_orders`),
  next to a `buyer_id`: someone who can read both can find the buyer of a gold
  row. Gold protects the buyer from analysts who cannot read silver, not from
  people who can read both.
- **Unclassified columns stay unclassified.** We did not read the text to judge
  it, and profiling stops at counts and lengths. `review_text` and `review_title`
  reach silver unchanged.
- **`p_desc` is `unclassified`, though it looks like product data.** Sellers
  type it freely, so it can hold a name or a phone number. `p_name`, a short
  title, is `internal`.
- **`extra_fields` is not in BigQuery.** The clickstream consumer writes it into
  the Parquet files from 6 November (data dictionary), but `clickstream_external`
  does not expose it, so it is not in the counts above. It would be
  `unclassified` if the table exposed it.
- **`expiry_date` is classed by lack of a better class.** The scale has no card
  class. It is landed by `ingestion/land_export.py` (Evaluna, step 2) and
  no model reads it: no dbt model reads `payment_details` (searched in
  `transform/models` and `warehouse/`). It is a candidate to stop landing
  (data minimisation), a later change to that script. The same holds for the
  other `pii.contact` columns of tables no model reads: `customer` (name,
  email, phone), `payment_details` (billing address) and `seller` (name).
- **A new column defaults to `internal`.** The script lists the columns that
  matched none of its rules when it runs. Someone has to read that list after
  every schema change, or a new personal column would be classed `internal`.
- **Classes on views follow the source.** Every silver model is a view over bronze:
  a class written here says what the column holds, not that anything enforces it.
  Enforcement is a separate piece of work.
- **Owners are people, not a team.** A column owned by one person also depends
  on that person being reachable.

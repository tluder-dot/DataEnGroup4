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

## Access matrix

Who may read or write which class of data, and what the platform grants today.
The matrix is the target, by least privilege. The real grants were read on
19 November 2026 (`gcloud storage buckets get-iam-policy` and `describe` on the
two buckets, `bq show` on the four datasets) and the gaps between the two are
listed below. Nothing in the cloud was changed to write this page.

### Roles

| Role | Held by | What it does |
|---|---|---|
| Analyst | Nobody today | Reads the figures of gold |
| Transform engineer | Till | Runs the extractor, owns bronze, writes the dbt models |
| Pipeline engineer | Jane | Writes the clickstream consumer and the DAG, runs the orchestrator |
| Platform engineer | Enzo | Owns Terraform and `g04_warehouse` |
| Governance owner | Evaluna | Owns the classes, the access matrix and the erasure check |
| Orchestrator | Whoever starts Airflow, with their own Google login | Runs the extractor, recreates the `_live` tables, runs dbt |

There is no service account: groups cannot create one in this project. The
orchestrator therefore has the rights of the person who starts it, not the
rights in the matrix (gap 8).

### The matrix

`read`: may read. `write`: may produce data of this class. `count`: may run
counts and lengths, never print values. `no`: no access.

| Role | `public` | `internal` | `pii.location` | `pii.identifier` | `pii.contact` | `unclassified` | `secret` |
|---|---|---|---|---|---|---|---|
| Analyst | read | read | no | no | no | no | no |
| Transform engineer (Till) | read, write | read, write | read, write | read, write | read, write | read, write | no |
| Pipeline engineer (Jane) | read, write | read, write | read, write | read, write | no | read, write | no |
| Platform engineer (Enzo) | read, write | read, write | read | read | no | read | no |
| Governance owner (Evaluna) | read | read | count | count | count | count | no |
| Orchestrator | read, write | read, write | read, write | read, write | no | read, write | no |

Why the cells say what they say:

- **`public`** is empty today: nothing in the platform is published.
- **`pii.contact` is `no` for Jane, Enzo and the orchestrator** because no dbt
  model reads `customer`, `payment_details` or `seller`. The extractor does write
  contact columns into the bronze files; that is a write, not a read from
  BigQuery.
- **The orchestrator reads and writes `pii.identifier`, `pii.location` and
  `unclassified`** because dbt joins on `buyer_id`, keeps the country of each
  buyer and copies the review text into silver.
- **Enzo reads `pii.identifier`, `pii.location` and `unclassified`** because
  `g04_warehouse` holds `buyer_id` (`orders_*`, `review`, `customer_shipping`),
  the country of an address and the review text.
- **The governance owner counts and never reads values**: profiling and checking
  an erasure need counts and lengths only.
- **`secret` is `no` for everyone**: those columns never enter the platform.

### Separation of duties for an erasure

The data owner runs the erasure and the governance owner checks it. Till, who
owns bronze, silver and gold, deletes the person's rows. Evaluna then checks, by
counts, that no row is left in any layer. Nobody checks their own deletion. The
steps are in the erasure runbook.

### When you need a `no`

Every `no` has a way out, so that nobody routes around the rule:

1. Open a GitHub issue that names the columns, the reason and how long you need
   them.
2. The owner of those columns (see Owners) approves or refuses in the issue.
3. If approved, the governance owner records it here with its end date, and the
   owner grants the right on those columns only, for that time.
4. When the date passes, the right is removed and the entry is closed.

This is informal on purpose: we have no ticket system and no way to expire a
grant automatically. A grant nobody removes is the failure to watch.

### What the platform grants today

Read on 19 November 2026.

| Resource | Principal | Role |
|---|---|---|
| Bucket `g04` (bronze files) | `projectOwner`, `projectEditor` | Bucket and object owner |
| Bucket `g04` | `projectViewer` | Bucket and object reader |
| Bucket `g04-tfstate` (Terraform state) | Same three bindings as `g04` | Same |
| `g04_bronze_1` | Till, Enzo | Owner |
| `g04_bronze_1` | Evaluna, Jane | Reader |
| `g04_silver`, `g04_gold` | Till, Enzo | Owner |
| `g04_silver`, `g04_gold` | Evaluna, Jane | Writer |
| `g04_warehouse` | Enzo | Owner |
| `g04_warehouse` | Jane | Reader |
| Every dataset | `projectOwners` | Owner |

Neither bucket has a binding we added. Settings read the same day: both have
uniform bucket-level access and a soft delete of 7 days; `g04` has no object
versioning, `g04-tfstate` has it on and blocks public access. The project's own
IAM policy cannot be read (`gcloud projects get-iam-policy` is refused), so a
role granted at project level is invisible here.

### Gaps between the matrix and the platform

| # | Gap | The matrix says | Reality | Can we close it? |
|---|---|---|---|---|
| 1 | Anyone with Viewer on the project reads all the bronze files | Only the roles that need bronze | `projectViewer` reads contacts, addresses and free text | Yes, on the bucket. Risk: our own reads of the external tables may depend on it (see note) |
| 2 | Anyone with Viewer reads the Terraform state | Enzo and Till only | The state holds the dataset access lists, so the members' email addresses | Yes, on the bucket. Risk: Terraform may stop if our own access relies on it |
| 3 | Jane can read the rows of `g04_warehouse` | Metadata only: the pipeline does not read it | No file under `orchestration/` or `transform/` reads it. Her jobs there, 6 to 19 November, only read metadata (see "What the audit showed") | Yes: narrow her role to metadata viewer, with Enzo's agreement and through Terraform (gap 12) |
| 4 | Evaluna is Writer on silver and gold | `count` only | She can read `buyer_id` and write in silver and gold | Yes: Writer to Reader. Risk: tagging columns will need rights on the source tables |
| 5 | Till is Owner of `g04_bronze_1`, silver and gold | Editor is enough | Owner can change the access list and delete the dataset | Yes, with Till's agreement. Enzo's Owner is needed for Terraform |
| 6 | Enzo is Owner of bronze, silver and gold | `pii.contact`: no | An Owner reads every column | Not until columns carry policy tags |
| 7 | Jane and Evaluna read all of `g04_bronze_1` | Jane: no `pii.contact`. Evaluna: `count` | A dataset Reader reads every column | Not until columns carry policy tags |
| 8 | There is no service account | An orchestrator with limited rights | The orchestrator runs with the login of the person who starts it, so with all of that person's rights | No: groups cannot create one |
| 9 | `projectOwners` is Owner everywhere | | Default, kept: the course's owners | Accepted |
| 10 | A project-level role is wider than the dataset grants, and invisible | Access follows the dataset grants | `testIamPermissions` on 19 November 2026 shows Evaluna's login holds `bigquery.tables.getData` on `g04_warehouse.orders_month`, where the dataset lists her nothing, so a project-level role gives it. We cannot list that role or say who else holds it | No: `resourcemanager.projects.getIamPolicy` is denied |
| 11 | No analyst exists | Reader on gold only | The Analyst row cannot be tested against anyone | No |
| 12 | Terraform does not manage any access | Access changes go through `plan` | `infra/terraform/` declares no `access` block and no IAM resource: it owns the containers, not who may read them | Yes: one `google_bigquery_dataset_iam_member` per grant, not a full `access` list (one dataset first) |

**Note on gaps 1 and 2.** An external table reads the files with the rights of
the person who queries it, so a dataset Reader also needs to read the bucket.
Removing `projectViewer` could stop our own reads. This is a hypothesis to test,
not something we measured.

### What the audit showed

The brief asks to find out what reads a dataset before changing access.

- **Cloud Logging can be read.** A first `gcloud logging read` on 19 November 2026
  failed with `UNAUTHENTICATED: Request had invalid authentication credentials`:
  the login had expired, it was not a refusal. After logging in again it worked.
  The `activity` log holds 47 entries naming `g04_warehouse` over 30 days, all
  Enzo's: creating and updating the dataset, 19 job inserts on 5 November, and
  table deletions on 5 and 19 November. The `data_access` log exists but holds
  no BigQuery entry in the same 30 days, so it cannot show who read rows. Cloud
  Logging therefore adds nothing about Jane; `JOBS_BY_PROJECT` is our evidence.
- **`INFORMATION_SCHEMA.JOBS_BY_PROJECT` could be read** for our login on
  19 November 2026 (175,112,192 bytes needed, cache off). The group's working
  rules say it is refused; that is no longer what we see.
- **Who queried `g04_warehouse` in the last 30 days** (jobs that name it):
  Enzo 238 jobs, the course's `bigquery-adminbot` 14 jobs on 5 November, Jane 8
  jobs, Evaluna 6 jobs.
- **Jane's 8 jobs, from 6 to 19 November, only read metadata**:
  `INFORMATION_SCHEMA.TABLES`, `.COLUMNS`, `.PARTITIONS` and `__TABLES__`. None
  read a data table. Evaluna's 6 are metadata reads too (`INFORMATION_SCHEMA`,
  to write this page).

What this cannot show: a job log lists queries, not a table preview in the
console or a read through the API that creates no query job. It covers 30 days,
and it does not say who would need access in the future.

### Next reductions

| Reduction | For | Risk | State |
|---|---|---|---|
| **B.** Jane on `g04_warehouse`: `roles/bigquery.dataViewer` to `roles/bigquery.metadataViewer` | Her 8 jobs there, 6 to 19 November 2026, only read metadata (`INFORMATION_SCHEMA`, `__TABLES__`) and the pipeline never reads the dataset. She keeps the lists of tables and columns and can no longer read rows, `buyer_id` included | No pipeline job breaks. Not verified: `__TABLES__` must still work with the metadata role, to be tested by Jane after the change. If Jane holds the same project-level role as Evaluna (gap 10), narrowing her dataset grant changes nothing: test it by reading a row as Jane after the change | Proposed to Enzo (code owner) and Jane (grant holder) on 2026-11-19; not applied. Access is not in Terraform (gap 12): two steps, add the metadata role, then remove the data role, in a separate pull request after their agreement |
| **A.** Remove `projectViewer` from `g04-tfstate` | The state holds the members' email addresses | Terraform stops if the person running it relied on that binding; give Enzo and Till named access first | Not done. The bucket was made by hand, outside Terraform |
| **C.** Evaluna: Writer to Reader on silver and gold | Governance needs counts, not writes | Setting a policy tag needs rights on the source table | Not done: wait for the enforcement work |

## Enforcement: what was tested

The brief asks for at least two columns classified and enforced, and enforcement
verified by being refused. This section says what was tested and what was shown.
Why access follows the class of a column is in
[ADR-0010](adr/0010-data-classification.md).

**Result in one line: a tag was set on one test column, and the read was not refused.
No real table carries a tag, and the refusal is not shown.**

### The test

On 20 November 2026, on a table of 3 synthetic rows, never on a real table. Times
are UTC, read from BigQuery's clock.

| Step | Result | Time |
|---|---|---|
| Create the taxonomy `g04-classification` (`europe-west1`, fine-grained access control on) | HTTP 200 | 09:34:13 |
| Create 5 tags: `pii`, with `location`, `identifier` and `contact` under it, and `unclassified` | HTTP 200 for the five. Short names are accepted | 09:38:33 to 09:38:34 |
| Create the dataset `g04_test_tags` and the table `orders_sample` (3 synthetic rows) | Created, default groups removed | 09:39:02, 09:39:19 |
| Set the tag `pii/identifier` on `buyer_id` | "successfully updated". `bq show --schema` shows the tag on `buyer_id` and on no other column | 09:39:27 |
| `SELECT buyer_id`, the tagged column | **3 rows, no error** | 09:39:39 |
| `SELECT order_id, order_date`, untagged columns | 3 rows | 09:39:46 |
| `SELECT buyer_id` again, 10 minutes after the tag | **3 rows, no error** | 09:50:06 |

Read at 09:40:07: the taxonomy has `FINE_GRAINED_ACCESS_CONTROL` on, and the IAM
policy of the tag is empty: nobody was granted the Fine-Grained Reader role on it.

### Not refused

The likeliest reason is that this login holds `datacatalog.categories.fineGrainedGet`
at project level (`testIamPermissions`, 19 November 2026), through a role that we
cannot list (gap 10). That is a hypothesis. It would be shown by a login that does
not hold the permission, and none ran the test. Jane was added as a reader of the
test dataset on 20 November at 09:46:37 and asked to run `SELECT buyer_id`:
**no second login ran the test by 20 November 2026. Documented as a gap; the
refusal is not shown.**

What this leaves of the brief's three requirements:

| Requirement | State |
|---|---|
| Every column has a class and an owner | Done (this page) |
| At least two columns classified through a taxonomy and policy tags | The mechanism works: a taxonomy, a hierarchy of tags, and a tag set on a column. **Not done on any real table** |
| Enforcement verified by being refused | **Not shown** |

### Also found

- **A taxonomy has no labels.** The group's label convention
  ([costs](costs.md)) does not apply to it, and it was created by hand, so it is
  outside Terraform.
- **A tag cannot go everywhere.** BigQuery supports column-level access control for
  "BigLake tables, BigQuery tables, and BigQuery Omni tables" (documentation, read
  19 November 2026). Bronze is plain external tables and silver is views, so only
  the native tables of `g04_warehouse` can carry a tag.
- **`orders_month` is the one table that could be tagged first.** No materialised
  view reads it, and only 4 query jobs touched it in 30 days, all Enzo's, the last on
  5 November (`INFORMATION_SCHEMA`, 20 November). Tagging a table of `g04_warehouse`
  changes Enzo's table and takes effect for everyone at once, so it needs his
  agreement.
- **A rebuild erases the tag.** `warehouse/02_tuned_tables.sql`, line 37, runs
  `CREATE OR REPLACE TABLE` on `orders_month`: after it the tag is gone.
- **Not these tables.** `daily_demand_country_mv` reads `orders_plain`,
  `customer_shipping`, `shipping_details` and `order_items_month_pc`.

### Cleaned up

The test left nothing in the project. On 20 November 2026:

| Step | Time |
|---|---|
| Jane's read access removed from `g04_test_tags`; `bq show` lists only `projectOwners` and the owner's login | 10:51:00 to 10:51:14 |
| Dataset `g04_test_tags` and its table deleted | 10:51:24 to 10:51:31 |
| Taxonomy `g04-classification` deleted (HTTP 200). Its tags went with it: the one checked answers 404 | 10:51:34 to 10:51:36 |
| Checked: `bq ls` lists `g04_bronze_1`, `g04_gold`, `g04_silver` and `g04_warehouse` only; the taxonomy and one of its tags answer 404; the 4 taxonomies of other groups are untouched | 10:51:50 |

The proposal for what comes next, a taxonomy declared in Terraform with
`google_data_catalog_taxonomy` and `google_data_catalog_policy_tag`, is in the ADR.

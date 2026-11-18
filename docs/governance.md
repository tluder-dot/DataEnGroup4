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


{#
  Replaces a personal identifier by a salted SHA-256 hash, 64 hex characters.
  The same input gives the same output, so joins on it still work.

  The salt is read from pii_salt in the dataset salt_dataset (g04_secrets unless
  a run says otherwise) at run time, never written into the
  SQL: a view stores its SQL, and the job history shows it to every user of the
  project. See docs/governance.md. A missing or empty salt stops the query with
  an error, instead of giving every row the same hash.
#}
{% macro pseudonymise(column) %}
    TO_HEX(SHA256(CONCAT(
        IFNULL(
            (SELECT NULLIF(salt, '') FROM {{ source('secrets', 'pii_salt') }}),
            ERROR('the salt table pii_salt is missing or empty')
        ),
        CAST({{ column }} AS STRING)
    )))
{% endmacro %}

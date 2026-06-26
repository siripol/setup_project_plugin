# Data Classification — ${name}

| Category | Examples | Classification | Storage tier | Notes |
|---|---|---|---|---|
| PII Identity | Thai NI, passport, full name | Restricted | encrypted-at-rest | Subject to PDPA §22 |
| PII Contact | email, phone, address | Confidential | encrypted-at-rest | |
| PII Behavioral | clickstream, session logs | Internal | encrypted-in-transit | Aggregable after 90 days |
| Financial | card last-4, billing | Restricted | tokenized | PCI-DSS overlap |
| Public | catalog data, public posts | Public | any | No PDPA restriction |

Replace example rows with the categories this service actually handles. Every restricted/confidential category MUST have a `data/<category>/` directory with retention sidecars.

"""Read-only adapters for the legacy Firestore menu.

The previous version of the site kept every menu item in a single Firestore
collection, images included as base64 data URLs. Nothing here is used at request
time: these modules exist so the one-off `import_firestore` management command can
be small, and so each translation rule can be unit tested without a database.

The subpackage is deliberately free of Django model imports except where a write is
unavoidable (`categories`), which keeps the parsing and data-quality layers usable
from a plain `python -c` session while auditing the source data.
"""

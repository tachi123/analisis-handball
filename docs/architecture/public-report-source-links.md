# Public report source links

The public report may state that a FEMEBAL sheet was confirmed, but this is not
permission to publish the imported document or its source location.

## Current projection

`official_sheet_confirmed` is a boolean public fact. It contains neither a file
path nor a URL and is safe to include in the static catalog and report.

## Future FEMEBAL link

Add an outbound link only when an analyst explicitly records a public, approved
HTTPS URL for that specific sheet. The export must project that approved URL
alone; it must never derive a URL from local imports, database values, storage
paths, match IDs, or operational configuration.

Until then the public UI must show confirmation without a hyperlink.

# Public report source links

The public report may state that a FEMEBAL sheet was confirmed, but this is not
permission to publish the imported document or its source location.

## Current projection

`official_sheet_confirmed` is a boolean public fact. It contains neither a file
path nor a URL and is safe to include in the static catalog and report.

## Published FEMEBAL link

An analyst must explicitly approve a confirmed snapshot for public publication.
The exporter verifies its SHA-256, then copies the approved PDF to a derived
static artifact named from the public match key. The report exposes only that
relative artifact link; it never exposes the snapshot ID, imported filename,
source path, or operational configuration.

Without explicit approval the public UI may show confirmation, but no hyperlink.

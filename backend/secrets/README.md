# Local Service-Account Credentials

Place the local Google service-account JSON at:

`backend/secrets/google-service-account.json`

This directory is bind-mounted into the backend container at `/app/secrets`.
The JSON key is ignored by Git; do not commit it.

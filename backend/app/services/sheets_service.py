import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock


class SheetsConfigurationError(RuntimeError):
    pass


class SheetsProviderError(RuntimeError):
    pass


class FileReportAdapter:
    """Stores the current development report as one atomically replaced JSON file."""

    def __init__(self, path=None):
        self.path = Path(path or os.getenv("LOCAL_PUBLIC_REPORT_FILE", ""))

    def upsert(self, projection):
        payload = json.dumps(projection, separators=(",", ":"), sort_keys=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        try:
            temporary_path.replace(self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def read(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SheetsProviderError("Local public report is unavailable") from error


def report_publisher_name():
    publisher = os.getenv("REPORT_PUBLISHER", "google").lower()
    if publisher not in {"google", "file"}:
        raise SheetsConfigurationError("REPORT_PUBLISHER must be google or file")
    return publisher


def validate_report_publisher_configuration():
    if report_publisher_name() != "file":
        return
    if os.getenv("APP_ENV") != "development":
        raise SheetsConfigurationError("REPORT_PUBLISHER=file requires APP_ENV=development")
    path = Path(os.getenv("LOCAL_PUBLIC_REPORT_FILE", ""))
    if not path.is_absolute() or not path.parent.is_dir():
        raise SheetsConfigurationError("LOCAL_PUBLIC_REPORT_FILE must be an absolute path in an existing directory")


class GoogleSheetsAdapter:
    """Writes one current public report projection to deterministic Sheet ranges."""

    _write_lock = Lock()

    def __init__(self, spreadsheet_id=None, credentials_path=None, credentials_json=None, service=None, sleep=time.sleep):
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.credentials_json = credentials_json or os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
        self.sheet_name = os.getenv("GOOGLE_SHEETS_TAB", "PublicReports")
        self.service = service
        self.sleep = sleep
        if not self.spreadsheet_id:
            raise SheetsConfigurationError("GOOGLE_SHEETS_ID is required to publish reports")

    def _service(self):
        if self.service is not None:
            return self.service
        if not self.credentials_path and not self.credentials_json:
            raise SheetsConfigurationError("Google Sheets credentials are required to publish reports")
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            credentials = (
                Credentials.from_service_account_info(json.loads(self.credentials_json))
                if self.credentials_json
                else Credentials.from_service_account_file(self.credentials_path)
            )
            return build("sheets", "v4", credentials=credentials, cache_discovery=False)
        except (ImportError, OSError, ValueError, json.JSONDecodeError) as error:
            raise SheetsConfigurationError("Google Sheets credentials could not be loaded") from error

    @staticmethod
    def _is_transient(error):
        status = getattr(error, "status_code", None) or getattr(getattr(error, "resp", None), "status", None)
        return isinstance(error, (ConnectionError, TimeoutError, OSError)) or status == 429 or status is not None and status >= 500

    def upsert(self, projection, attempts=3, base_delay=0.1):
        payload = json.dumps(projection, separators=(",", ":"), sort_keys=True)
        metadata = json.dumps({"schema_version": projection["schema_version"], "report_version": projection["report_version"]}, separators=(",", ":"), sort_keys=True)
        body = {
            "valueInputOption": "RAW",
            "data": [
                {"range": f"{self.sheet_name}!A1", "values": [[payload]]},
                {"range": f"{self.sheet_name}!A2", "values": [[metadata]]},
            ],
        }
        with self._write_lock:
            for attempt in range(attempts):
                try:
                    return self._service().spreadsheets().values().batchUpdate(
                        spreadsheetId=self.spreadsheet_id, body=body
                    ).execute()
                except SheetsConfigurationError:
                    raise
                except Exception as error:
                    if not self._is_transient(error) or attempt == attempts - 1:
                        raise SheetsProviderError("Google Sheets publication failed") from error
                    self.sleep(base_delay * (2 ** attempt))


def get_report_adapter(google_adapter_factory=GoogleSheetsAdapter):
    validate_report_publisher_configuration()
    if report_publisher_name() == "file":
        return FileReportAdapter()
    return google_adapter_factory()

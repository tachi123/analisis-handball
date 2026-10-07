import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user
from ...models import ReportPackage, User
from ...schemas import (
    RecoveryArtifactAttestation,
    RecoveryArtifactStatus,
    ReportPackageCreate,
    ReportPackageUpdate,
    ReportPublicationStatus,
    ReviewedReportPackage,
)
from ...services.report_service import REQUIRED_RECOVERY_ARTIFACTS, ReportService
from ...services.sheets_service import (
    GoogleSheetsAdapter,
    SheetsConfigurationError,
    SheetsProviderError,
    get_report_adapter,
    report_publisher_name,
    validate_report_publisher_configuration,
)

router = APIRouter(tags=["reports"])


@router.post("/matches/{match_id}/report-packages", response_model=ReviewedReportPackage, status_code=201)
def create_report_package(match_id: int, data: ReportPackageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return ReportService.create(db, match_id, data, user)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/report-packages/{package_id}", response_model=ReviewedReportPackage)
def get_report_package(package_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    package = ReportService.get(db, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Report package not found")
    return package


@router.put("/report-packages/{package_id}", response_model=ReviewedReportPackage)
def update_report_package(package_id: int, data: ReportPackageUpdate, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    package = ReportService.get(db, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Report package not found")
    try:
        return ReportService.update(db, package, data)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/report-packages/{package_id}/approve", response_model=ReviewedReportPackage)
def approve_report_package(package_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    package = ReportService.get(db, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Report package not found")
    try:
        return ReportService.approve(db, package)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def publication_status(package: ReportPackage):
    readiness = ReportService.publication_readiness(package)
    publication = max(package.publications, key=lambda item: item.id, default=None)
    status = publication.status if publication else ("ready" if readiness["ready"] else "not_ready")
    return ReportPublicationStatus(
        package_id=package.id,
        report_version=package.report_version,
        status=status,
        missing_recovery_artifacts=readiness["missing_recovery_artifacts"],
        recovery_artifacts=[RecoveryArtifactStatus.model_validate(item) for item in package.recovery_artifacts],
        published_at=publication.published_at if publication else None,
        failure_message="Publication failed. Retry the publication." if status == "failed" else None,
        public_url=os.getenv("PUBLIC_REPORT_URL") if status == "published" else None,
    )


def get_package_or_404(db, package_id):
    package = db.get(ReportPackage, package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Report package not found")
    return package


def report_adapter_factory():
    return get_report_adapter(GoogleSheetsAdapter)


@router.get("/report-packages/{package_id}/publication-status", response_model=ReportPublicationStatus)
def get_publication_status(package_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return publication_status(get_package_or_404(db, package_id))


@router.put(
    "/report-packages/{package_id}/recovery-artifacts/{artifact_type}",
    response_model=RecoveryArtifactStatus,
)
def attest_recovery_artifact(
    package_id: int,
    artifact_type: str,
    data: RecoveryArtifactAttestation,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if artifact_type not in REQUIRED_RECOVERY_ARTIFACTS:
        raise HTTPException(status_code=422, detail="Unsupported recovery artifact type")
    package = get_package_or_404(db, package_id)
    return ReportService.attest_recovery_artifact(db, package, artifact_type, data.location, user)


@router.post("/report-packages/{package_id}/publish", response_model=ReportPublicationStatus)
def publish_report(package_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    package = get_package_or_404(db, package_id)
    try:
        ReportService.publish(db, package, report_adapter_factory)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SheetsConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SheetsProviderError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return publication_status(package).model_dump()


@router.get("/public/reports/current")
def get_current_public_report():
    try:
        validate_report_publisher_configuration()
        if report_publisher_name() != "file":
            raise SheetsConfigurationError("Local reader is disabled")
        return get_report_adapter().read()
    except (SheetsConfigurationError, SheetsProviderError) as error:
        raise HTTPException(status_code=404, detail="Public report is unavailable") from error

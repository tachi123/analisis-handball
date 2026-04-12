from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...database import get_db
from ...deps import get_current_user, require_role
from ...models import User
from ...schemas import LoginRequest, TokenResponse, UserCreate, UserRead, ChangePasswordRequest
from ...security import create_access_token
from ...services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = AuthService.authenticate(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    token = create_access_token({"sub": str(user.id), "role": user.role, "club_id": user.club_id})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/change-password", response_model=UserRead)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ...security import verify_password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta",
        )
    updated = AuthService.change_password(db, current_user, data.new_password)
    return updated


# ─── User management (admin+ only) ────────────────────────────────────────────

@router.get("/users", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_role("superadmin", "admin")),
    db: Session = Depends(get_db),
):
    return AuthService.get_all_users(db)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    current_user: User = Depends(require_role("superadmin", "admin")),
    db: Session = Depends(get_db),
):
    # admin can only create analysts, superadmin can create any role
    if current_user.role == "admin" and data.role != "analyst":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un admin solo puede crear usuarios analistas",
        )
    existing = AuthService.get_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email",
        )
    user = AuthService.create_user(db, data.email, data.password, data.full_name, data.role)
    user.must_change_password = True
    db.commit()
    db.refresh(user)
    return user

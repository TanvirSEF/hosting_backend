# app/api/v1/auth.py
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
import jwt
from app.database.session import get_db
from app.core.config import settings
from app.models.user import User
from app.models.security import RefreshTokenSession, TokenBlacklist
from app.schemas.user import UserCreate, UserLogin, Token, UserOut
from app.schemas.security import LogoutRequest, RefreshTokenRequest
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.api.deps import decode_bearer_token, get_current_user
from app.services.audit import write_audit_log

router = APIRouter()

def client_context(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }

def create_token_pair(user_id: int, db: Session) -> tuple[str, str]:
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    payload = jwt.decode(refresh_token, settings.JWT_SECRET, algorithms=["HS256"])
    db.add(
        RefreshTokenSession(
            user_id=user_id,
            jti=payload["jti"],
            expires_at=datetime.utcfromtimestamp(payload["exp"]),
        )
    )
    return access_token, refresh_token

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    # 1. Duplicate email matching database exception handling block
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="This email is already registered."
        )

    if user_in.phone_number:
        user = db.query(User).filter(User.phone_number == user_in.phone_number).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="This phone number is already registered."
            )
    
    # 2. Object construction parsing encrypted password target mapping
    db_user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        phone_number=user_in.phone_number,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    db.flush()
    access_token, refresh_token = create_token_pair(db_user.id, db)
    write_audit_log(db, "auth.signup", db_user.id, "user", str(db_user.id), "User signed up.", **client_context(request))
    db.commit()
    db.refresh(db_user)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": db_user}

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    # 1. Target criteria scanning on database users relation layer
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )
    
    access_token, refresh_token = create_token_pair(user.id, db)
    write_audit_log(db, "auth.login", user.id, "user", str(user.id), "User logged in.", **client_context(request))
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": user}

@router.post("/refresh", response_model=Token)
def refresh_access_token(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)):
    try:
        decoded = jwt.decode(payload.refresh_token, settings.JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    session = db.query(RefreshTokenSession).filter(RefreshTokenSession.jti == decoded.get("jti")).first()
    if not session or session.revoked_at:
        raise HTTPException(status_code=401, detail="Refresh token is revoked or unknown.")

    blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == decoded.get("jti")).first()
    if blacklisted:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked.")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    access_token = create_access_token(subject=user.id)
    write_audit_log(db, "auth.refresh", user.id, "user", str(user.id), "Access token refreshed.", **client_context(request))
    db.commit()
    return {"access_token": access_token, "refresh_token": payload.refresh_token, "token_type": "bearer", "user": user}

@router.post("/logout")
def logout(
    payload: LogoutRequest,
    request: Request,
    authorization: str = Header(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    access_payload = decode_bearer_token(authorization, db, "access")
    if access_payload.get("jti"):
        db.add(
            TokenBlacklist(
                jti=access_payload["jti"],
                token_type="access",
                user_id=current_user.id,
                expires_at=datetime.utcfromtimestamp(access_payload["exp"]),
            )
        )

    if payload.refresh_token:
        try:
            refresh_payload = jwt.decode(payload.refresh_token, settings.JWT_SECRET, algorithms=["HS256"])
            refresh_session = db.query(RefreshTokenSession).filter(RefreshTokenSession.jti == refresh_payload.get("jti")).first()
            if refresh_session and refresh_session.user_id == current_user.id:
                refresh_session.revoked_at = datetime.utcnow()
                db.add(
                    TokenBlacklist(
                        jti=refresh_payload["jti"],
                        token_type="refresh",
                        user_id=current_user.id,
                        expires_at=datetime.utcfromtimestamp(refresh_payload["exp"]),
                    )
                )
        except Exception:
            pass

    write_audit_log(db, "auth.logout", current_user.id, "user", str(current_user.id), "User logged out.", **client_context(request))
    db.commit()
    return {"status": "logged_out"}

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

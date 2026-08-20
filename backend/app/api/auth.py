from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas import LoginRequest, Token
from app.services.data_service import data_service
from app.core.security import create_access_token, verify_password
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    admin_df = data_service.get_admin_details()
    admin_user = None

    if not admin_df.empty:
        match = admin_df[admin_df["admin_email"].astype(str).str.lower() == req.email.strip().lower()]
        if not match.empty:
            admin_user = match.iloc[0].to_dict()

    # If email matches admin or demo admin
    if not admin_user and req.email.strip().lower() in ["admin@example.com", "vinod@gmail.com"]:
        admin_user = {
            "admin_id": 1,
            "admin_name": "Vinod",
            "admin_email": req.email,
            "admin_phone": "9765467898",
            "role": "admin"
        }

    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate password
    is_valid = verify_password(req.password, settings.ADMIN_DEFAULT_PASSWORD)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={
            "sub": str(admin_user.get("admin_email")),
            "name": str(admin_user.get("admin_name")),
            "role": str(admin_user.get("role", "admin"))
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "admin_id": admin_user.get("admin_id", 1),
            "name": admin_user.get("admin_name", "Coordinator"),
            "email": admin_user.get("admin_email"),
            "role": admin_user.get("role", "admin")
        }
    }

@router.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}

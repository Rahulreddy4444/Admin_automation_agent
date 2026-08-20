from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token
from app.services.data_service import data_service
from typing import Dict, Any

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_admin(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    admin_df = data_service.get_admin_details()
    if not admin_df.empty:
        match = admin_df[admin_df["admin_email"].astype(str).str.lower() == email.lower()]
        if not match.empty:
            return match.iloc[0].to_dict()

    # Fallback default admin profile
    return {
        "admin_id": 1,
        "admin_name": payload.get("name", "Admin"),
        "admin_email": email,
        "admin_phone": "9999999999",
        "role": payload.get("role", "admin")
    }

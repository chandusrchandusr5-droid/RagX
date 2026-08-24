from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateProfileRequest(BaseModel):
    full_name: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/register")
async def register(request: RegisterRequest):
    try:
        session_data = AuthService.register_user(
            email=request.email,
            full_name=request.full_name,
            password=request.password
        )
        return {
            "message": "User registered successfully.",
            "token": session_data["token"],
            "user": session_data["user"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login(request: LoginRequest):
    try:
        session_data = AuthService.login_user(
            email=request.email,
            password=request.password
        )
        return {
            "message": "Login successful.",
            "token": session_data["token"],
            "user": session_data["user"]
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None), current_user: dict = Depends(get_current_user)):
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    AuthService.logout_session(token, user=current_user)
    return {"message": "Logged out successfully."}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user
    }

@router.put("/profile")
async def update_profile(request: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    try:
        updated = AuthService.update_profile(user_id=current_user["id"], new_name=request.full_name)
        return {
            "message": "Profile updated successfully.",
            "user": updated
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

@router.post("/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    try:
        AuthService.change_password(
            user_id=current_user["id"],
            current_password=request.current_password,
            new_password=request.new_password
        )
        return {
            "message": "Password changed successfully. Please log in with your new password."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password change failed: {str(e)}")

@router.delete("/account")
async def delete_account(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    try:
        from app.services.document_registry import DocumentRegistryService
        from app.core.vector_db import vector_db

        # Purge user's documents and vector chunks safely
        user_docs = DocumentRegistryService.get_all_documents(owner_id=user_id)
        for doc in user_docs:
            DocumentRegistryService.permanently_delete_document(doc["document_id"], owner_id=user_id)
            vector_db.delete_document_chunks_by_id(doc["document_id"], owner_id=user_id)

        AuthService.delete_account(user_id)
        return {
            "message": "Account and associated data deleted successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Account deletion failed: {str(e)}")

from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.dependencies import get_admin_user
from app.services.auth_service import AuthService
from app.services.document_registry import DocumentRegistryService
from app.core.vector_db import vector_db

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/dashboard")
async def get_admin_dashboard(admin_user: dict = Depends(get_admin_user)):
    users = AuthService.get_all_users_admin()
    docs = DocumentRegistryService.get_all_documents(owner_id=None) # All system docs across users for admin summary
    activities = AuthService.get_activity_logs(limit=200)

    total_users = len(users)
    active_users = sum(1 for u in users if u.get("status") == "ACTIVE")
    admin_count = sum(1 for u in users if u.get("role") == "ADMIN")
    total_docs = len(docs)
    active_docs = sum(1 for d in docs if d.get("status") == "ACTIVE")

    return {
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "admin_count": admin_count,
            "total_documents": total_docs,
            "active_documents": active_docs,
            "total_activities": len(activities)
        },
        "recent_activities": activities[:10]
    }

@router.get("/users")
async def list_users_admin(admin_user: dict = Depends(get_admin_user)):
    users = AuthService.get_all_users_admin()
    # Enrich users with document counts
    all_docs = DocumentRegistryService.get_all_documents(owner_id=None)
    for u in users:
        u_docs = [d for d in all_docs if d.get("owner_id") == u["id"]]
        u["document_count"] = len(u_docs)

    return {
        "total_users": len(users),
        "users": users
    }

@router.get("/users/{user_id}/documents")
async def get_user_documents_admin(user_id: str, admin_user: dict = Depends(get_admin_user)):
    user_docs = DocumentRegistryService.get_all_documents(owner_id=user_id)
    return {
        "user_id": user_id,
        "total_documents": len(user_docs),
        "documents": user_docs
    }

@router.delete("/users/{user_id}")
async def delete_user_admin(user_id: str, admin_user: dict = Depends(get_admin_user)):
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account through User Management. Use Settings -> Delete Account instead.")

    # 1. Purge target user's documents
    user_docs = DocumentRegistryService.get_all_documents(owner_id=user_id)
    for doc in user_docs:
        DocumentRegistryService.permanently_delete_document(doc["document_id"], owner_id=user_id)
        vector_db.delete_document_chunks_by_id(doc["document_id"], owner_id=user_id)

    # 2. Delete user account
    AuthService.delete_account(user_id)
    AuthService.log_activity(admin_user["id"], admin_user["full_name"], admin_user["email"], "Admin Deleted User", f"Admin deleted user account '{user_id}'.")

    return {
        "message": f"User '{user_id}' and all associated documents deleted successfully."
    }

@router.get("/activity")
async def get_activity_logs_admin(limit: int = Query(100, ge=1, le=500), admin_user: dict = Depends(get_admin_user)):
    logs = AuthService.get_activity_logs(limit=limit)
    return {
        "total_logs": len(logs),
        "activities": logs
    }

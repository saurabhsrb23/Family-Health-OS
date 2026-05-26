import logging
import re
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from database import SessionLocal
from models.audit_log import AuditLog

logger = logging.getLogger(__name__)

SKIP_PATHS = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]


def extract_resource_from_path(path: str, method: str) -> tuple:
    """
    Parse request path + method into (action, resource_type).

    Examples:
      POST /api/v1/members            → CREATE_MEMBER,      Member
      GET  /api/v1/members/{id}       → READ_MEMBER,        Member
      POST /api/v1/members/{id}/meals → CREATE_MEAL_LOG,    MealLog
      GET  /api/v1/members/{id}/adherence → READ_ADHERENCE, Adherence
    """
    method_map = {
        "GET": "READ",
        "POST": "CREATE",
        "PUT": "UPDATE",
        "DELETE": "DELETE",
        "PATCH": "PATCH",
    }
    verb = method_map.get(method, method)

    if "/meals" in path:
        return f"{verb}_MEAL_LOG", "MealLog"
    elif "/workouts" in path:
        return f"{verb}_WORKOUT", "WorkoutSession"
    elif "/measurements" in path:
        return f"{verb}_MEASUREMENT", "HealthMeasurement"
    elif "/adherence" in path:
        return f"{verb}_ADHERENCE", "Adherence"
    elif "/summaries" in path:
        return f"{verb}_SUMMARY", "ProgramSummary"
    elif "/programs" in path:
        return f"{verb}_PROGRAM", "CareProgram"
    elif "/members" in path:
        return f"{verb}_MEMBER", "FamilyMember"
    elif "/auth" in path:
        return f"{verb}_AUTH", "Auth"
    return f"{verb}_UNKNOWN", "Unknown"


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Append-only audit log for every API request.
    Runs after response is sent — never blocks the request path.
    PHI access is traceable via user_id + resource_type + path.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip noisy system paths
        if any(request.url.path.startswith(p) for p in SKIP_PATHS):
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000)

        try:
            action, resource_type = extract_resource_from_path(request.url.path, request.method)

            # X-Forwarded-For for prod (behind load balancer); fallback to direct client
            ip = request.headers.get("X-Forwarded-For", "")
            if not ip and request.client:
                ip = request.client.host

            # Auth middleware sets user_id on request.state after token validation
            user_id = getattr(request.state, "user_id", None)

            db = SessionLocal()
            try:
                audit = AuditLog(
                    id=uuid4(),
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    ip_address=(ip[:45] if ip else None),
                    user_agent=(request.headers.get("user-agent", "")[:500]),
                    request_path=str(request.url.path)[:500],
                    status_code=response.status_code,
                    extra_data={"duration_ms": duration_ms, "method": request.method},
                )
                db.add(audit)
                db.commit()
            finally:
                db.close()

        except Exception as e:
            # Never let audit logging crash the response
            logger.warning(f"Audit log write failed: {e}")

        return response

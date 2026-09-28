"""Small operational admin API for reports, quota and search telemetry."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.api.search import _quota_status
from backend.database.database import get_connection
from backend.security import require_admin, require_csrf

router = APIRouter(prefix="/admin", tags=["admin"])


class ReportStatusPayload(BaseModel):
    status: str


@router.get("/summary")
def summary(request: Request):
    require_admin(request)
    connection = get_connection()
    try:
        users = int(connection.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])
        videos = int(connection.execute("SELECT COUNT(*) AS c FROM videos").fetchone()["c"])
        open_reports = int(connection.execute("SELECT COUNT(*) AS c FROM video_reports WHERE status = 'open'").fetchone()["c"])
        new_contacts = int(connection.execute("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'new'").fetchone()["c"])
        searches_24h = int(connection.execute("SELECT COUNT(*) AS c FROM search_history WHERE datetime(created_at) >= datetime('now', '-1 day')").fetchone()["c"])
        top_rows = connection.execute(
            """SELECT query, COUNT(*) AS count
               FROM search_history
               WHERE datetime(created_at) >= datetime('now', '-7 day') AND trim(query) <> ''
               GROUP BY lower(query)
               ORDER BY count DESC, query COLLATE NOCASE ASC
               LIMIT 10"""
        ).fetchall()
        top_queries = [{"query": row["query"], "count": int(row["count"])} for row in top_rows]
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "users": users,
            "videos": videos,
            "open_reports": open_reports,
            "new_contacts": new_contacts,
            "searches_24h": searches_24h,
            "top_queries": top_queries,
            "quota": _quota_status(),
        }
    finally:
        connection.close()


@router.get("/reports")
def reports(request: Request, status: str = "open", limit: int = 100):
    admin = require_admin(request)
    clean_status = str(status or "open").strip().lower()
    if clean_status not in {"open", "resolved", "all"}:
        raise HTTPException(status_code=422, detail="status должен быть open, resolved или all")
    safe_limit = max(1, min(int(limit or 100), 200))
    connection = get_connection()
    try:
        if clean_status == "all":
            rows = connection.execute(
                """SELECT r.*, u.email AS reporter_email, u.name AS reporter_name
                   FROM video_reports r JOIN users u ON u.id = r.user_id
                   ORDER BY datetime(r.created_at) DESC LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        else:
            rows = connection.execute(
                """SELECT r.*, u.email AS reporter_email, u.name AS reporter_name
                   FROM video_reports r JOIN users u ON u.id = r.user_id
                   WHERE r.status = ?
                   ORDER BY datetime(r.created_at) DESC LIMIT ?""",
                (clean_status, safe_limit),
            ).fetchall()
        return {
            "items": [
                {
                    "id": int(row["id"]),
                    "video_id": row["video_id"],
                    "reason": row["reason"],
                    "details": row["details"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "resolved_at": row["resolved_at"],
                    "reporter": {"name": row["reporter_name"], "email": row["reporter_email"]},
                }
                for row in rows
            ],
            "admin": {"email": admin["email"]},
        }
    finally:
        connection.close()


@router.patch("/reports/{report_id}")
def update_report(report_id: int, payload: ReportStatusPayload, request: Request):
    admin = require_admin(request)
    require_csrf(request)
    status = str(payload.status or "").strip().lower()
    if status not in {"open", "resolved"}:
        raise HTTPException(status_code=422, detail="status должен быть open или resolved")
    connection = get_connection()
    try:
        if status == "resolved":
            cursor = connection.execute(
                "UPDATE video_reports SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP, resolved_by = ? WHERE id = ?",
                (int(admin["id"]), int(report_id)),
            )
        else:
            cursor = connection.execute(
                "UPDATE video_reports SET status = 'open', resolved_at = NULL, resolved_by = NULL WHERE id = ?",
                (int(report_id),),
            )
        connection.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Жалоба не найдена")
        return {"ok": True, "id": int(report_id), "status": status}
    finally:
        connection.close()

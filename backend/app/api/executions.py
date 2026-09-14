from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.database import get_db
from backend.app.models import Execution, ExecutionLog, User
from backend.app.schemas import ExecutionResponse, ExecutionLogResponse
from backend.app.api.deps import get_current_user

router = APIRouter(tags=["executions"])


@router.get("/api/jobs/{job_id}/executions", response_model=List[ExecutionResponse])
async def list_job_executions(
    job_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Execution)
        .where(Execution.job_id == job_id)
        .order_by(Execution.id.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/api/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    execution = await db.get(Execution, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution


@router.get("/api/executions/{execution_id}/logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    execution_id: int,
    level: Optional[str] = None,
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
    if level:
        stmt = stmt.where(ExecutionLog.level == level.upper())
    stmt = stmt.order_by(ExecutionLog.id.asc()).limit(limit)

    res = await db.execute(stmt)
    return res.scalars().all()

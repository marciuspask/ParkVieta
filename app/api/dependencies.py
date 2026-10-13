from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.database import get_engine
from db.orm_models import TenantORM


def get_db():
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_tenant_id(
    x_tenant_id: str = Header(...),
    session: Session = Depends(get_db),
) -> str:
    exists = session.execute(
        select(TenantORM).where(TenantORM.tenant_id == x_tenant_id)
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Tenant '{x_tenant_id}' not found")
    return x_tenant_id

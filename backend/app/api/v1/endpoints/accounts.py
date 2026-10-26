from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.account import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])
Db = Annotated[AsyncSession, Depends(get_db)]


class AccountCreate(BaseModel):
    name: str
    type: str  # checking | credit_card
    institution: str = ""
    mask: str = ""


class AccountOut(BaseModel):
    id: str
    name: str
    type: str
    institution: str
    mask: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[AccountOut])
async def list_accounts(db: Db) -> list[Account]:
    result = await db.execute(select(Account).order_by(Account.name))
    return list(result.scalars())


@router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountCreate, db: Db) -> Account:
    account = Account(
        id=str(uuid.uuid4()),
        name=body.name,
        type=body.type,
        institution=body.institution,
        mask=body.mask,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: str, db: Db) -> Account:
    account = await db.get(Account, account_id)
    if not account:
        raise NotFoundError("Account", account_id)
    return account


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: str, db: Db) -> None:
    account = await db.get(Account, account_id)
    if not account:
        raise NotFoundError("Account", account_id)
    await db.delete(account)
    await db.commit()

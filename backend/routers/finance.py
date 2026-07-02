"""
finance.py — plain JSON endpoints for the Finance module.
Reuses modules/finance/utils.py verbatim; only serialization is added.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.finance import utils as fu
from backend.serializers import jsonable

router = APIRouter(prefix="/api/finance", tags=["finance"])

VALID_DECISIONS = {"blocked", "cleared", "escalated", "monitoring"}


class CompareRequest(BaseModel):
    account_ids: list[str]


class DecisionRequest(BaseModel):
    account_id: str
    decision: str
    analyst: str = "analyst"
    notes: str = ""


@router.get("/alerts")
def alerts():
    txns, accounts = fu.load_data()
    queue = fu.build_alert_queue(txns, accounts)
    return {"threshold": fu.VELOCITY_THRESHOLD, "alerts": jsonable(queue)}


@router.get("/accounts/{account_id}")
def account_detail(account_id: str):
    txns, accounts = fu.load_data()
    acc_id = account_id.upper()
    acc_row = accounts[accounts["account_id"] == acc_id]
    if acc_row.empty:
        raise HTTPException(status_code=404, detail=f"Account {acc_id} not found")
    acc_txns = txns[txns["account_id"] == acc_id].sort_values("timestamp")
    velocity = fu.compute_velocity(acc_txns)
    return {
        "account": jsonable(acc_row.iloc[0].to_dict()),
        "velocity": jsonable(velocity),
        "transactions": jsonable(acc_txns),
    }


@router.post("/accounts/compare")
def compare(req: CompareRequest):
    txns, accounts = fu.load_data()
    return {"comparison": jsonable(fu.compare_accounts(req.account_ids, txns, accounts))}


@router.get("/decisions")
def decisions():
    fu.init_db()
    return {"decisions": jsonable(fu.get_decisions())}


@router.post("/decisions")
def save_decision(req: DecisionRequest):
    if req.decision not in VALID_DECISIONS:
        raise HTTPException(status_code=400, detail=f"decision must be one of {sorted(VALID_DECISIONS)}")
    fu.init_db()
    fu.save_decision(req.account_id.upper(), req.decision, req.analyst, req.notes)
    return {"ok": True, "decisions": jsonable(fu.get_decisions())}


@router.get("/invoices/report")
def invoices_report():
    df = fu.load_invoices()
    return jsonable(fu.build_invoice_risk_report(df))

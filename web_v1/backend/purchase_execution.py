"""Opt-in purchase execution on a shared Agent; ownership stays with the caller."""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from .config import settings
from .setup_state import setup_status


def resolve_purchase_execution(caller: dict[str, Any]) -> dict[str, Any]:
    users = {item.casefold() for item in re.split(r"[,;\s]+", settings.purchase_shared_user_ids) if item}
    shared = str(caller.get("user_id") or "").strip().casefold() in users
    if not shared:
        if not caller.get("ready"):
            missing = ", ".join(caller.get("missing_items") or [])
            raise HTTPException(status_code=409, detail=f"필수 프로그램 점검이 완료되지 않았습니다: {missing}")
        return caller
    target_ip = str(settings.purchase_shared_agent_ip or "").strip()
    target_id = str(settings.purchase_shared_agent_id or "").strip()
    if not target_ip or not target_id:
        raise HTTPException(status_code=409, detail="구매 공용 PC의 Agent 설정이 없습니다. 관리자에게 확인해 주세요.")
    target = setup_status(agent_id=target_id, client_ip=target_ip)
    if not target.get("ready") or target.get("agent_id") != target_id or target.get("client_ip") != target_ip:
        missing = ", ".join(target.get("missing_items") or [])
        raise HTTPException(status_code=409, detail=f"구매 공용 PC({target_ip})가 준비되지 않았습니다: {missing}")
    return target


def purchase_routing_payload(caller: dict[str, Any], executor: dict[str, Any]) -> dict[str, Any]:
    if (caller.get("agent_id"), caller.get("client_ip")) == (executor.get("agent_id"), executor.get("client_ip")):
        return {}
    return {
        "purchase_shared": True,
        "output_agent_id": str(caller.get("agent_id") or ""),
        "output_client_ip": str(caller.get("client_ip") or ""),
    }

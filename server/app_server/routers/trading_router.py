"""売買・損益集計用 API（設計書 8.2）"""

from fastapi import APIRouter, Depends

import app_server.share.global_value as g
from app_server.service.core_logic.base import CoreLogic

router = APIRouter(prefix="/trading", tags=["trading"])


def get_core_logic() -> CoreLogic:
    return g.injector.resolve(CoreLogic)


@router.post("/pnl-summary")
async def output_pnl_summary(
    period_type: str = "daily",
    core_logic: CoreLogic = Depends(get_core_logic),
):
    """損益集計を実行し、集計結果CSVを出力する。"""
    core_logic.output_pnl_summary(period_type=period_type)
    return {"status": "ok", "period_type": period_type}

"""売買・損益集計用 API"""

import app_server.share.global_value as g
from app_server.application.trading_service.base import TradingServiceBase
from app_server.domain.sender.base import OrderSender
from app_server.share.my_exception import Mt4RequestTimeoutError
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/trading", tags=["trading"])


def get_trading_service() -> TradingServiceBase:
    return g.injector.resolve(TradingServiceBase)


def get_order_sender() -> OrderSender:
    return g.injector.resolve(OrderSender)


@router.post("/pnl-summary")
async def output_pnl_summary(
    period_type: str = "daily",
    trading_service: TradingServiceBase = Depends(get_trading_service),
):
    """損益集計を実行し、集計結果CSVを出力する。"""
    trading_service.output_pnl_summary(period_type=period_type)
    return {"status": "ok", "period_type": period_type}


@router.get("/price-info/{symbol}")
async def api_get_price_info(
    symbol: str,
    order_sender: OrderSender = Depends(get_order_sender),
):
    """指定シンボルの価格情報（point, digits, pips）を MT4 に問い合わせて返す。"""
    try:
        info = await order_sender.get_price_info(symbol)
        return info.model_dump()
    except Mt4RequestTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e)) from e


@router.get("/order-info")
async def api_get_order_info(
    ticket: int | None = None,
    order_sender: OrderSender = Depends(get_order_sender),
):
    """注文情報を MT4 に問い合わせて返す。ticket 省略時は全注文一覧。"""
    try:
        result = await order_sender.get_order_info(ticket=ticket)
        return result.model_dump()
    except Mt4RequestTimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e)) from e

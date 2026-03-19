"""
Surenxuan Connector Transforms
将 mason-hub 标准 schema 与 surenxuan 内部数据格式互转。

v0.1: 只定义接口签名，不写实现。
"""

from typing import Any


def to_standard_inventory(surenxuan_data: dict) -> dict:
    """surenxuan 库存数据 → 标准 inventory schema"""
    raise NotImplementedError("v0.2 实现")


def from_standard_inventory(standard_data: dict) -> dict:
    """标准 inventory schema → surenxuan 库存数据"""
    raise NotImplementedError("v0.2 实现")


def to_standard_product(surenxuan_data: dict) -> dict:
    """surenxuan 商品数据 → 标准 product schema"""
    raise NotImplementedError("v0.2 实现")


def to_standard_order(surenxuan_data: dict) -> dict:
    """surenxuan 订单数据 → 标准 order schema"""
    raise NotImplementedError("v0.2 实现")


def to_standard_price(surenxuan_data: dict) -> dict:
    """surenxuan 价格数据 → 标准 price schema"""
    raise NotImplementedError("v0.2 实现")


def execute_command(command: dict) -> dict:
    """
    接收 mason-hub 标准指令，转换并执行。

    command 格式:
    {
        "action": "inventory.query",
        "params": {"sku": "BAG-001", "channel": "offline"},
        "request_id": "xxx"
    }

    返回标准格式的结果。
    """
    raise NotImplementedError("v0.2 实现")

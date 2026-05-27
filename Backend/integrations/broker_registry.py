"""
Broker Registry — Factory pattern to get broker instances by ID.
Add new brokers here by registering them in BROKER_MAP.
"""
from integrations.base_broker import BaseBroker
from integrations.indstocks import INDstocksBroker
from integrations.zerodha import ZerodhaBroker
from integrations.upstox import UpstoxBroker

# Registry: broker_id → broker class instance
BROKER_MAP: dict[str, BaseBroker] = {
    "indstocks": INDstocksBroker(),
    "zerodha":   ZerodhaBroker(),
    "upstox":    UpstoxBroker(),
}


def get_broker(broker_id: str) -> BaseBroker:
    """Get a broker instance by its ID. Raises ValueError if not found."""
    broker = BROKER_MAP.get(broker_id)
    if not broker:
        raise ValueError(f"Unknown broker: '{broker_id}'. Available: {list(BROKER_MAP.keys())}")
    return broker


def list_brokers() -> list[dict]:
    """Return metadata for all registered brokers."""
    return [b.broker_info() for b in BROKER_MAP.values()]

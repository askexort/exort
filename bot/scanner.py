"""
Blockchain scanner — detects buy/sell events for tracked tokens.

Uses DEXScreener API (free, no key) for trade data and public
RPCs for on-chain Transfer event monitoring.
"""

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("openmind-scanner")

# ─── Chain Config ─────────────────────────────────────────────────────────────

CHAIN_CONFIG = {
    "ethereum": {
        "name": "Ethereum",
        "chain_id": 1,
        "rpc": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "dexscreener_id": "ethereum",
    },
    "base": {
        "name": "Base",
        "chain_id": 8453,
        "rpc": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "dexscreener_id": "base",
    },
    "polygon": {
        "name": "Polygon",
        "chain_id": 137,
        "rpc": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
        "dexscreener_id": "polygon",
    },
    "bsc": {
        "name": "BNB Chain",
        "chain_id": 56,
        "rpc": "https://bsc-dataseed.binance.org",
        "explorer": "https://bscscan.com",
        "dexscreener_id": "bsc",
    },
    "arbitrum": {
        "name": "Arbitrum",
        "chain_id": 42161,
        "rpc": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "dexscreener_id": "arbitrum",
    },
    "solana": {
        "name": "Solana",
        "chain_id": 0,
        "rpc": "https://api.mainnet-beta.solana.com",
        "explorer": "https://solscan.io",
        "dexscreener_id": "solana",
    },
}

# Known DEX router addresses (EVM)
UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
UNISWAP_V3_ROUTER = "0xe592427a0aece92de3edee1f18e0157c05861564"
UNISWAP_V3_SWAP_ROUTER = "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45"
UNISWAP_UNIVERSAL_ROUTER = "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad"

SUSHISWAP_ROUTER = "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f"
PANCAKE_ROUTER = "0x10ed43c718714eb63d5aa57b78b54704e256024e"
BASESWAP_ROUTER = "0x327df1e6de05895d2ab08513aadd9313fe505d86"

KNOWN_ROUTERS = {
    "ethereum": [
        UNISWAP_V2_ROUTER,
        UNISWAP_V3_ROUTER,
        UNISWAP_V3_SWAP_ROUTER,
        UNISWAP_UNIVERSAL_ROUTER,
        SUSHISWAP_ROUTER,
    ],
    "base": [UNISWAP_V3_SWAP_ROUTER, UNISWAP_UNIVERSAL_ROUTER, BASESWAP_ROUTER],
    "polygon": [UNISWAP_V3_SWAP_ROUTER, UNISWAP_UNIVERSAL_ROUTER],
    "bsc": [PANCAKE_ROUTER],
    "arbitrum": [UNISWAP_V3_SWAP_ROUTER, UNISWAP_UNIVERSAL_ROUTER],
}

# Transfer event topic
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@dataclass
class TradeEvent:
    """Represents a detected buy or sell."""

    tx_hash: str
    token_address: str
    token_symbol: str
    token_name: str
    chain: str
    side: str  # "BUY" or "SELL"
    amount_usd: float
    amount_token: float
    price_usd: float
    trader: str
    timestamp: float
    pair_address: str = ""
    dex: str = ""
    explorer_url: str = ""


def _http_get(url: str, headers: dict | None = None, timeout: int = 10) -> dict | None:
    """Make an HTTP GET request and return parsed JSON."""
    hdrs = {"User-Agent": "OpenMind-Bot/0.1.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.debug(f"HTTP GET failed for {url[:80]}: {e}")
        return None


def _http_post(url: str, data: dict, timeout: int = 10) -> dict | None:
    """Make an HTTP POST request with JSON body."""
    payload = json.dumps(data).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OpenMind-Bot/0.1.0",
    }
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.debug(f"HTTP POST failed for {url[:80]}: {e}")
        return None


# ─── DEXScreener API ─────────────────────────────────────────────────────────


def get_token_info(token_address: str, chain: str) -> dict | None:
    """Get token info from DEXScreener."""
    chain_cfg = CHAIN_CONFIG.get(chain.lower())
    if not chain_cfg:
        return None

    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    data = _http_get(url, timeout=15)
    if not data or "pairs" not in data:
        return None

    # Filter pairs for the correct chain
    pairs = [
        p
        for p in data["pairs"]
        if p.get("chainId", "").lower() == chain_cfg["dexscreener_id"].lower()
    ]

    if not pairs:
        return None

    # Use the most liquid pair
    pairs.sort(key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
    pair = pairs[0]

    return {
        "token_address": token_address,
        "token_name": pair.get("baseToken", {}).get("name", "Unknown"),
        "token_symbol": pair.get("baseToken", {}).get("symbol", "???"),
        "chain": chain,
        "price_usd": float(pair.get("priceUsd", 0) or 0),
        "price_change_5m": float(pair.get("priceChange", {}).get("m5", 0) or 0),
        "price_change_1h": float(pair.get("priceChange", {}).get("h1", 0) or 0),
        "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
        "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
        "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
        "pair_address": pair.get("pairAddress", ""),
        "dex": pair.get("dexId", ""),
        "pair_created": pair.get("pairCreatedAt", 0),
        "url": pair.get("url", ""),
    }


def get_recent_trades(token_address: str, chain: str, limit: int = 20) -> list[TradeEvent]:
    """Get recent trades for a token via DEXScreener pairs endpoint."""
    chain_cfg = CHAIN_CONFIG.get(chain.lower())
    if not chain_cfg:
        return []

    # Get token pairs
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    data = _http_get(url, timeout=15)
    if not data or "pairs" not in data:
        return []

    pairs = [
        p
        for p in data["pairs"]
        if p.get("chainId", "").lower() == chain_cfg["dexscreener_id"].lower()
    ]

    if not pairs:
        return []

    trades = []

    # DEXScreener doesn't return individual trades in the token endpoint.
    # We use the boost/latest endpoint or scan on-chain.
    # For now, return pair-level data as a "trade" snapshot.
    return trades


# ─── On-Chain Scanner (EVM) ──────────────────────────────────────────────────


def get_latest_block(chain: str) -> int:
    """Get the latest block number via JSON-RPC."""
    chain_cfg = CHAIN_CONFIG.get(chain.lower())
    if not chain_cfg or chain_cfg.get("chain_id", 0) == 0:
        return 0

    result = _http_post(
        chain_cfg["rpc"],
        {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1,
        },
    )
    if result and "result" in result:
        return int(result["result"], 16)
    return 0


def get_token_transfers(
    token_address: str,
    chain: str,
    from_block: int = 0,
    to_block: int = 0,
    page_size: int = 100,
) -> list[dict]:
    """Get Transfer events for a token via eth_getLogs."""
    chain_cfg = CHAIN_CONFIG.get(chain.lower())
    if not chain_cfg or chain_cfg.get("chain_id", 0) == 0:
        return []

    if to_block == 0:
        to_block = get_latest_block(chain)
    if from_block == 0:
        from_block = max(0, to_block - 100)  # Last ~100 blocks

    # Transfer event: Transfer(address indexed from, indexed to, indexed value)
    result = _http_post(
        chain_cfg["rpc"],
        {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [
                {
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                    "address": token_address,
                    "topics": [TRANSFER_TOPIC],
                }
            ],
            "id": 1,
        },
        timeout=30,
    )

    if not result or "result" not in result:
        return []

    return result["result"]


def decode_transfer(log: dict, chain: str) -> dict | None:
    """Decode a Transfer event log into readable data."""
    topics = log.get("topics", [])
    if len(topics) < 3:
        return None

    from_addr = "0x" + topics[1][-40:]
    to_addr = "0x" + topics[2][-40:]
    data = log.get("data", "0x")

    try:
        value = int(data, 16) if data != "0x" else 0
    except ValueError:
        value = 0

    chain_cfg = CHAIN_CONFIG.get(chain.lower(), {})

    return {
        "from": from_addr.lower(),
        "to": to_addr.lower(),
        "value": value,
        "tx_hash": log.get("transactionHash", ""),
        "block": int(log.get("blockNumber", "0x0"), 16),
        "log_index": int(log.get("logIndex", "0x0"), 16),
        "explorer": chain_cfg.get("explorer", ""),
    }


def classify_trade(
    transfer: dict,
    chain: str,
    token_decimals: int = 18,
) -> str | None:
    """Classify a transfer as BUY, SELL, or None (transfer).

    A BUY is when tokens flow FROM a DEX router TO a wallet.
    A SELL is when tokens flow FROM a wallet TO a DEX router.
    """
    routers = [r.lower() for r in KNOWN_ROUTERS.get(chain, [])]
    from_addr = transfer["from"]
    to_addr = transfer["to"]

    if from_addr in routers:
        return "BUY"
    elif to_addr in routers:
        return "SELL"

    # If neither address is a known router, it's a regular transfer
    return None


# ─── Solana Scanner ───────────────────────────────────────────────────────────


def get_solana_token_info(mint_address: str) -> dict | None:
    """Get Solana token info from DEXScreener."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
    data = _http_get(url, timeout=15)
    if not data or "pairs" not in data:
        return None

    pairs = [p for p in data["pairs"] if p.get("chainId", "").lower() == "solana"]

    if not pairs:
        return None

    pairs.sort(key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
    pair = pairs[0]

    return {
        "token_address": mint_address,
        "token_name": pair.get("baseToken", {}).get("name", "Unknown"),
        "token_symbol": pair.get("baseToken", {}).get("symbol", "???"),
        "chain": "solana",
        "price_usd": float(pair.get("priceUsd", 0) or 0),
        "price_change_5m": float(pair.get("priceChange", {}).get("m5", 0) or 0),
        "price_change_1h": float(pair.get("priceChange", {}).get("h1", 0) or 0),
        "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0),
        "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
        "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
        "pair_address": pair.get("pairAddress", ""),
        "dex": pair.get("dexId", ""),
        "url": pair.get("url", ""),
    }


# ─── Price Alerts ────────────────────────────────────────────────────────────


def check_price_alerts(
    token_info: dict,
    buy_threshold: float = 0,
    sell_threshold: float = 0,
) -> str | None:
    """Check if price change triggers an alert.

    Returns alert message or None.
    """
    price = token_info.get("price_usd", 0)
    change_5m = token_info.get("price_change_5m", 0)
    change_1h = token_info.get("price_change_1h", 0)
    alerts = []

    if buy_threshold > 0 and price <= buy_threshold:
        alerts.append(f"🟢 Price hit BUY target: ${price:.8f} ≤ ${buy_threshold:.8f}")

    if sell_threshold > 0 and price >= sell_threshold:
        alerts.append(f"🔴 Price hit SELL target: ${price:.8f} ≥ ${sell_threshold:.8f}")

    if abs(change_5m) >= 20:
        direction = "📈" if change_5m > 0 else "📉"
        alerts.append(f"{direction} 5m change: {change_5m:+.1f}%")

    if abs(change_1h) >= 50:
        direction = "📈" if change_1h > 0 else "📉"
        alerts.append(f"{direction} 1h change: {change_1h:+.1f}%")

    if alerts:
        return "\n".join(alerts)
    return None


def format_trade_alert(
    token_info: dict,
    chain: str,
    trade_type: str = "SNAPSHOT",
) -> str:
    """Format a token status alert message."""
    chain_cfg = CHAIN_CONFIG.get(chain.lower(), {})
    chain_name = chain_cfg.get("name", chain.title())
    symbol = token_info.get("token_symbol", "???")
    name = token_info.get("token_name", "Unknown")
    price = token_info.get("price_usd", 0)

    lines = [
        f"🔔 **{symbol}** ({name}) — {chain_name}",
        "",
        f"💰 Price: `${price:.8f}`" if price < 0.01 else f"💰 Price: `${price:.4f}`",
    ]

    change_5m = token_info.get("price_change_5m", 0)
    change_1h = token_info.get("price_change_1h", 0)
    change_24h = token_info.get("price_change_24h", 0)

    def fmt_change(val: float) -> str:
        emoji = "🟢" if val >= 0 else "🔴"
        return f"{emoji} {val:+.1f}%"

    lines.append(
        f"  5m: {fmt_change(change_5m)} | 1h: {fmt_change(change_1h)}"
        f"  | 24h: {fmt_change(change_24h)}"
    )

    vol = token_info.get("volume_24h", 0)
    liq = token_info.get("liquidity_usd", 0)
    lines.append(f"📊 Vol 24h: ${vol:,.0f}  |  💧 Liq: ${liq:,.0f}")

    url = token_info.get("url", "")
    explorer = chain_cfg.get("explorer", "")
    addr = token_info.get("token_address", "")

    if url:
        lines.append(f"📈 [DEXScreener]({url})")
    if explorer and addr:
        lines.append(f"🔍 [Explorer]({explorer}/token/{addr})")

    return "\n".join(lines)

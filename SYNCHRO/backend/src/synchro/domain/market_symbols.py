import enum


class MarketCategory(str, enum.Enum):
    VOLATILITY = "volatility"
    FOREX = "forex"
    STOCK = "stock"


ALLOWED_SYMBOLS: dict[str, MarketCategory] = {
    "R_10": MarketCategory.VOLATILITY,
    "R_25": MarketCategory.VOLATILITY,
    "R_50": MarketCategory.VOLATILITY,
    "R_75": MarketCategory.VOLATILITY,
    "R_100": MarketCategory.VOLATILITY,
    "1HZ10V": MarketCategory.VOLATILITY,
    "1HZ25V": MarketCategory.VOLATILITY,
    "1HZ50V": MarketCategory.VOLATILITY,
    "1HZ75V": MarketCategory.VOLATILITY,
    "1HZ100V": MarketCategory.VOLATILITY,
    "frxEURUSD": MarketCategory.FOREX,
    "frxGBPUSD": MarketCategory.FOREX,
    "frxUSDJPY": MarketCategory.FOREX,
    "frxAUDUSD": MarketCategory.FOREX,
    "frxUSDCAD": MarketCategory.FOREX,
    "frxNZDUSD": MarketCategory.FOREX,
    "frxEURGBP": MarketCategory.FOREX,
    "frxEURJPY": MarketCategory.FOREX,
}


class SymbolNotAllowed(ValueError):
    pass


def is_allowed_symbol(symbol: str) -> bool:
    return symbol in ALLOWED_SYMBOLS


def validate_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or symbol not in ALLOWED_SYMBOLS:
        raise SymbolNotAllowed(f"symbol '{symbol}' is not in the SYNCHRO approved list")
    return symbol


def validate_symbol_list(symbols: list[str]) -> list[str]:
    return [validate_symbol(s) for s in symbols]

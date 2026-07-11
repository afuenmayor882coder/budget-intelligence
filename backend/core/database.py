import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "budget.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    hora TEXT,
    tipo TEXT NOT NULL,
    categoria TEXT,
    subcategoria TEXT,
    descripcion TEXT,
    cuenta TEXT,
    monto_bs REAL,
    monto_usd REAL,
    tasa REAL,
    moneda TEXT,
    import_batch_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exchange_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL UNIQUE,
    tasa_binance REAL,
    tasa_bcv REAL,
    dif_pct_paralelo REAL,
    dif_pct_oficial REAL,
    log_return_binance REAL,
    log_return_bcv REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS macro_ipc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    indice REAL,
    var_pct REAL,
    UNIQUE(year, month)
);

CREATE TABLE IF NOT EXISTS macro_liquidity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    m1 REAL,
    m2 REAL,
    billetes_monedas REAL,
    depositos_vista REAL,
    depositos_ahorro REAL,
    UNIQUE(year, month)
);

CREATE TABLE IF NOT EXISTS macro_gdp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    gdp_value REAL,
    pct_change REAL,
    UNIQUE(year, quarter)
);

CREATE TABLE IF NOT EXISTS macro_oil (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL UNIQUE,
    revenue_usd_bn REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS cesta_basica (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_bs REAL,
    total_usd REAL,
    food_bs REAL,
    services_bs REAL,
    source_url TEXT,
    fetched_at TEXT,
    UNIQUE(year, month)
);

CREATE TABLE IF NOT EXISTS income_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    frequency TEXT NOT NULL DEFAULT 'monthly',
    start_date TEXT,
    indexed_to_inflation INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    frequency TEXT NOT NULL DEFAULT 'monthly',
    category TEXT,
    account TEXT,
    active INTEGER DEFAULT 1,
    next_payment_date TEXT,
    essential INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS saving_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    target_currency TEXT NOT NULL DEFAULT 'USD',
    target_date TEXT,
    monthly_contribution REAL,
    priority INTEGER DEFAULT 1,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS import_history (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    date_range_start TEXT,
    date_range_end TEXT,
    row_count INTEGER DEFAULT 0,
    imported_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS model_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    layer TEXT,
    hyperparams TEXT,
    metrics TEXT,
    trained_at TEXT DEFAULT (datetime('now')),
    artifact_path TEXT
);

CREATE TABLE IF NOT EXISTS parallel_rate_monthly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    rate REAL,
    series_type TEXT DEFAULT 'reconstructed',
    UNIQUE(year, month)
);

CREATE TABLE IF NOT EXISTS forecast_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_run_id INTEGER,
    horizon_days INTEGER,
    target TEXT,
    forecast TEXT,
    confidence_bands TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_status (
    id TEXT PRIMARY KEY,
    source TEXT,
    synced_at TEXT,
    new_rows INTEGER DEFAULT 0,
    updated_rows INTEGER DEFAULT 0,
    status TEXT DEFAULT 'success',
    message TEXT
);

CREATE TABLE IF NOT EXISTS user_prefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pref_key TEXT NOT NULL UNIQUE,
    pref_value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights_cache (
    id TEXT PRIMARY KEY,
    context TEXT NOT NULL,
    insight_type TEXT,
    subject TEXT,
    severity TEXT DEFAULT 'info',
    priority_score REAL DEFAULT 0,
    payload TEXT,
    expires_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_transactions_fecha ON transactions(fecha);
CREATE INDEX IF NOT EXISTS idx_transactions_tipo ON transactions(tipo);
CREATE INDEX IF NOT EXISTS idx_transactions_categoria ON transactions(categoria);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_fecha ON exchange_rates(fecha);
CREATE INDEX IF NOT EXISTS idx_insights_cache_context ON insights_cache(context);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_context():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

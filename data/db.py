
# data/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'app.db'

# ===== SCHEMA base (inclui equipamentos e CHECKs atualizados) =====
SCHEMA = '''
PRAGMA foreign_keys = ON;

-- ORDERS com PRIORIDADE nova e STATUS novo
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    equipment TEXT,
    priority TEXT CHECK(priority in ('Emergencial','Urgente','Alta','Média','Baixa')) DEFAULT 'Média',
    status   TEXT CHECK(status   in ('Planejada','Em Execução','Concluída'))       DEFAULT 'Planejada',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    description TEXT NOT NULL,
    unit TEXT DEFAULT 'UN',
    stock REAL DEFAULT 0,
    min_stock REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT
);

CREATE TABLE IF NOT EXISTS material_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    quantity REAL DEFAULT 0,
    FOREIGN KEY(material_id) REFERENCES materials(id) ON DELETE CASCADE,
    FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS library_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    tags TEXT,
    content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    sql_query TEXT NOT NULL,
    chart_type TEXT DEFAULT 'valor',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Tabela hierárquica de equipamentos/subequipamentos
CREATE TABLE IF NOT EXISTS equipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES equipments(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    UNIQUE(name, parent_id)
);
'''

# ===== Seeds mínimos =====
SEED = [
    ("INSERT OR IGNORE INTO orders(code, title, description, equipment, priority, status) VALUES (?,?,?,?,?,?)",
     [
         ("00000000001", "Vazamento em linha hidráulica", "Inspeção e troca de mangueira", "Prensa H-01", "Alta", "Planejada"),
         ("00000000002", "Ruído em rolamento", "Verificação e lubrificação", "Esteira C02", "Média", "Em Execução"),
         ("00000000003", "Troca preventiva de filtro", "Troca filtro alta pressão", "Bomba B03", "Baixa", "Concluída"),
     ]),
    ("INSERT OR IGNORE INTO materials(code, description, unit, stock, min_stock) VALUES (?,?,?,?,?)",
     [
         ("MAT-1001", "Mangueira hidráulica 1/2", "UN", 12, 5),
         ("MAT-1002", "Rolamento 6205 ZZ", "UN", 30, 10),
         ("MAT-1003", "Filtro HP 10 microns", "UN", 8, 4)
     ]),
    ("INSERT OR IGNORE INTO locations(code, name) VALUES (?,?)",
     [
         ("ALM-01", "Almoxarifado Central"),
         ("LIN-01", "Linha de Produção 01")
     ]),
]

LIB_SEED = (
    "INSERT OR IGNORE INTO library_docs(title, tags, content) VALUES (?,?,?)",
    [
        ("Torque em conexões hidráulicas", "hidráulica;torque;conexões",
         "Tabela de torque para conexões JIC, ORFS e NPT. Sempre usar torque adequado e reaperto após 24h."),
        ("Plano de manutenção Bomba B-03", "bomba;b-03;preventiva",
         "Periodicidade mensal. Itens: inspeção de vazamentos, troca de filtro HP, verificação de ruído e temperatura.")
    ]
)

IND_SEED = (
    "INSERT OR IGNORE INTO indicators(name, description, sql_query, chart_type) VALUES (?,?,?,?)",
    [
        ("OM abertas", "Quantidade de ordens em status Planejada", "SELECT COUNT(*) FROM orders WHERE status='Planejada'", "valor"),
        ("Backlog total", "Total de ordens não concluídas", "SELECT COUNT(*) FROM orders WHERE status IN ('Planejada','Em Execução')", "valor")
    ]
)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ===== Migrações (CHECK prioridade e CHECK status) =====
def _needs_priority_migration(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'")
    row = cur.fetchone()
    if not row or not row["sql"]:
        return False
    sql = row["sql"]
    return ("CHECK(priority in ('Baixa','Média','Alta','Crítica'))" in sql)

def _migrate_orders_priority(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders_new_p (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            equipment TEXT,
            priority TEXT CHECK(priority in ('Emergencial','Urgente','Alta','Média','Baixa')) DEFAULT 'Média',
            status TEXT CHECK(status in ('Planejada','Em Execução','Concluída')) DEFAULT 'Planejada',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute("INSERT OR IGNORE INTO orders_new_p (id, code, title, description, equipment, priority, status, created_at, updated_at) SELECT id, code, title, description, equipment, priority, status, created_at, updated_at FROM orders")
    cur.execute("DROP TABLE orders")
    cur.execute("ALTER TABLE orders_new_p RENAME TO orders")
    conn.commit()

def _needs_status_migration(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'")
    row = cur.fetchone()
    if not row or not row["sql"]:
        return False
    sql = row["sql"]
    # Antigo CHECK incluía 'Aberta', 'Pendente', 'Cancelada'
    return ("CHECK(status in ('Aberta','Em Execução','Pendente','Concluída','Cancelada'))" in sql)

def _migrate_orders_status(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders_new_s (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT NOT NULL,
            description TEXT,
            equipment TEXT,
            priority TEXT CHECK(priority in ('Emergencial','Urgente','Alta','Média','Baixa')) DEFAULT 'Média',
            status TEXT CHECK(status in ('Planejada','Em Execução','Concluída')) DEFAULT 'Planejada',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute("INSERT OR IGNORE INTO orders_new_s (id, code, title, description, equipment, priority, status, created_at, updated_at) SELECT id, code, title, description, equipment, priority, status, created_at, updated_at FROM orders")
    cur.execute("DROP TABLE orders")
    cur.execute("ALTER TABLE orders_new_s RENAME TO orders")
    conn.commit()

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # Migrações detectadas
    if _needs_priority_migration(conn):
        _migrate_orders_priority(conn)
    if _needs_status_migration(conn):
        _migrate_orders_status(conn)

    # Seeds
    for sql, rows in SEED:
        cur.executemany(sql, rows)

    cur.executemany(LIB_SEED[0], LIB_SEED[1])
    cur.executemany(IND_SEED[0], IND_SEED[1])

    # Exemplo material->local
    cur.execute("SELECT id FROM materials WHERE code='MAT-1001'")
    m1 = cur.fetchone()
    cur.execute("SELECT id FROM locations WHERE code='ALM-01'")
    l1 = cur.fetchone()
    if m1 and l1:
        cur.execute("INSERT OR IGNORE INTO material_locations(material_id, location_id, quantity) VALUES (?,?,?)", (m1[0], l1[0], 10))

    conn.commit()
    conn.close()

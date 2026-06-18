import sqlite3
import os
import sys
from datetime import datetime
from threading import Lock

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(get_app_dir(), "data.db")


class Database:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            note_type TEXT DEFAULT 'text',
            file_path TEXT,
            category_id INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            quadrant INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            category_id INTEGER DEFAULT 0,
            due_date TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            remind_time TEXT NOT NULL,
            repeat_type TEXT DEFAULT 'none',
            is_lunar INTEGER DEFAULT 0,
            is_important INTEGER DEFAULT 0,
            interval_minutes INTEGER DEFAULT 0,
            category_id INTEGER DEFAULT 0,
            is_triggered INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            detail TEXT,
            old_data TEXT,
            new_data TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            ledger_type TEXT NOT NULL,
            category TEXT,
            note TEXT,
            ledger_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            is_deleted INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS quick_tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tool_type TEXT NOT NULL,
            icon TEXT,
            command TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category_id);
        CREATE INDEX IF NOT EXISTS idx_notes_deleted ON notes(is_deleted);
        CREATE INDEX IF NOT EXISTS idx_todos_category ON todos(category_id);
        CREATE INDEX IF NOT EXISTS idx_todos_deleted ON todos(is_deleted);
        CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(is_completed);
        CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(remind_time);
        CREATE INDEX IF NOT EXISTS idx_reminders_deleted ON reminders(is_deleted);
        CREATE INDEX IF NOT EXISTS idx_timeline_target ON timeline(target_type, target_id);
        """)

        # 插入默认分类
        cursor = self._conn.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            defaults = ["默认", "工作", "个人", "学习", "生活"]
            for i, name in enumerate(defaults):
                self._conn.execute(
                    "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                    (name, i),
                )
            self._conn.commit()

    @property
    def conn(self):
        return self._conn

    def execute(self, sql, params=None):
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)

    def executemany(self, sql, params):
        return self._conn.executemany(sql, params)

    def commit(self):
        self._conn.commit()

    def fetchone(self, sql, params=None):
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        if row:
            return dict(zip([col[0] for col in cursor.description], row))
        return None

    def fetchall(self, sql, params=None):
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(zip([col[0] for col in cursor.description], r)) for r in rows]

    def insert(self, table, data):
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self._conn.execute(sql, tuple(data.values()))
        self._conn.commit()
        return cursor.lastrowid

    def update(self, table, data, where, where_params=None):
        sets = ", ".join([f"{k}=?" for k in data])
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        params = tuple(data.values())
        if where_params:
            params += tuple(where_params)
        self._conn.execute(sql, params)
        self._conn.commit()

    def soft_delete(self, table, id_value, id_column="id"):
        self.update(table, {"is_deleted": 1}, f"{id_column}=?", [id_value])

    def restore(self, table, id_value, id_column="id"):
        self.update(table, {"is_deleted": 0}, f"{id_column}=?", [id_value])


db = Database()

"""
Context managers pour les connexions PostgreSQL.
"""

import os
from contextlib import contextmanager


def get_db_connection():
    """Ouvre et retourne une nouvelle connexion PostgreSQL."""
    import psycopg2
    conn = psycopg2.connect(
        host=os.environ.get('DB_URL', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'k_factur_x'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASS', ''),
    )
    conn.autocommit = False
    return conn


@contextmanager
def db_cursor(commit=False):
    """Context manager qui yield (conn, cursor), gère commit/rollback/close."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        if not conn.closed:
            conn.close()


@contextmanager
def db_connection():
    """Context manager qui yield conn brut (pour les cas avec LOCK TABLE)."""
    conn = get_db_connection()
    try:
        yield conn
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        if not conn.closed:
            conn.close()

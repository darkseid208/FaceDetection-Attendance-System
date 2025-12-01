# db_connection.py
# Simple MySQL connection helper used by student.py
# — configured for your app user 'pythonuser' / '12345'

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": "localhost",
    "user": "pythonuser",   # <- app user
    "password": "12345",    # <- app user password (change if you used a different one)
    "database": "face_attendance",
    "auth_plugin": "mysql_native_password"  # helps on some MySQL installs
}

def get_connection():
    """Return a new MySQL connection. Caller must close it."""
    return mysql.connector.connect(**DB_CONFIG)

def test_connection():
    try:
        con = get_connection()
        ok = getattr(con, "is_connected", lambda: True)()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        cnt = cur.fetchone()[0]
        cur.close(); con.close()
        return True, ok, cnt
    except Error as e:
        return False, None, str(e)

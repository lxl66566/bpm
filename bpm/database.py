import functools

import duckdb as db
from constants import DATABASE_PATH

TABLE_NAME = "package"


def init():
    if not DATABASE_PATH.parent.exists():
        DATABASE_PATH.parent.mkdir(parents=True)
    con: db.DuckDBPyConnection = db.connect(str(DATABASE_PATH))
    con.execute(
        f"""CREATE TABLE {TABLE_NAME} (
            name VARCHAR,
            version TEXT,
            description TEXT
        );"""
    )
    con.close()


def with_connect(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not DATABASE_PATH.exists():
            init()
        con: db.DuckDBPyConnection = db.connect(str(DATABASE_PATH))
        result = func(con, *args, **kwargs)
        con.close()
        return result

    return wrapper


@with_connect
def show(con: db.DuckDBPyConnection):
    con.table(TABLE_NAME).show()

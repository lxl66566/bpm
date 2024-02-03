import functools

import duckdb as db
from constants import DATABASE_PATH

TABLE_NAME = "package"


def with_connect(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        con: db.DuckDBPyConnection = db.connect(str(DATABASE_PATH))
        result = func(con, *args, **kwargs)
        con.close()
        return result

    return wrapper


@with_connect
def show(con: db.DuckDBPyConnection):
    con.table(TABLE_NAME).show()

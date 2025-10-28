import os

from src.modules import PostgreSQL

def main(sql_dbname, sql_user, sql_password, sql_host, sql_port, sql_table):
    sql = PostgreSQL(sql_dbname, sql_user, sql_password, sql_host, sql_port, sql_table)

    sql.get_sql_status()

if __name__ == '__main__':
    sql_dbname = os.environ.get("SQL_DBNAME", "ai_ops_db")
    sql_user = os.environ.get("SQL_USER", "ai_ops")
    sql_password=os.environ.get("SQL_PASSWORD", "Conti12345!")
    sql_host = os.environ.get("SQL_HOST", "10.214.149.31")
    sql_port = os.environ.get("SQL_PORT", "5432")
    sql_table = os.environ.get("SQL_TABLE", "model_pullrequest")

    main(sql_dbname, sql_user, sql_password, sql_host, sql_port, sql_table)
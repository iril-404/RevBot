import logging
import psycopg2
from psycopg2 import OperationalError

class PostgreSQL:
    def __init__(
            self,
            sql_dbname: str,
            sql_user: str,
            sql_password: str,
            sql_host: str,
            sql_port: str,
            sql_table: str
        ):
        self.sql_dbname = sql_dbname
        self.sql_user = sql_user
        self.sql_password = sql_password
        self.sql_host = sql_host
        self.sql_port = sql_port
        self.sql_table = sql_table

        self.conn = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)

        self._connect()
    
    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.sql_dbname,
                user=self.sql_user,
                password=self.sql_password,
                host=self.sql_host,
                port=self.sql_port
            )
            self.conn.autocommit = True  # enable auto-commit
            self.cursor = self.conn.cursor()
        except OperationalError as e:
            self.logger.error("Failed to connect to the database", exc_info=True)

    def execute(self, query: str, params: tuple = None):
        """
        Execute a raw SQL query with optional parameters.
        """
        try:
            self.cursor.execute(query, params)
        except Exception as e:
            self.logger.error("Query execution failed", exc_info=True)
            self.conn.rollback()

    def update(self, data: dict):
        """
        Update Everything
        """
        pr_link = data.get("pr_link")
    
        select_query = f"SELECT id, commit_statuses FROM {self.sql_table} WHERE pr_link = %s LIMIT 1"
        try:
            self.cursor.execute(select_query, (pr_link,))
            result = self.cursor.fetchone()

            if result:
                _, old_commit_statuses = result
                new_commit_status = data.get("commit_statuses")
                combined_commit_statuses = old_commit_statuses + " --> " + new_commit_status

                update_query = f"""
                    UPDATE {self.sql_table}
                    SET ticket_info = %s,
                        changed_files = %s,
                        git_diff = %s,
                        commit_statuses = %s,
                        last_edit = %s,
                        jira_link = %s
                    WHERE pr_link = %s
                """
                self.cursor.execute(update_query, (
                    data.get("ticket_info"),
                    data.get("changed_files"),
                    data.get("git_diff"),
                    combined_commit_statuses,
                    data.get("last_edit"),
                    data.get("jira_link"),
                    pr_link
                ))

            else:
                self.insert(data)

        except Exception as e:
            self.logger.error("Update failed", exc_info=True)
            self.conn.rollback()

    def insert(self, data: dict):
        """
        Insert a record into the given table.
        `data` is a dict mapping column names to values.
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        values = tuple(data.values())

        query = f"INSERT INTO {self.sql_table} ({columns}) VALUES ({placeholders})"
        self.execute(query, values)

    def delete_all(self, table: str):
        '''
        !!!!!!!!!!!WARNING!!!!!!!!!!!!!!!!
        This function is only for development
        IT WILL DELATE ENTIRE SQL DATABASE
        '''
        
        query = f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"
        try:
            self.cursor.execute(query)
        except Exception as e:
            self.logger.error("Delete table {table} failed", exc_info=True)
            self.conn.rollback()

    def print(self, table: str, params: tuple = None):
        """
        Fetch and print all rows from the given table.
        Returns all rows.
        """
        query = f"SELECT * FROM {table}"
        try:
            self.cursor.execute(query, params)
            rows =  self.cursor.fetchall()
            for row in rows:
                print(row)
            return rows
        except Exception as e:
            self.logger.error("Fetch table {table} failed", exc_info=True)
            return []

    def get_sql_header(self, params: tuple = None):
        """
        printing the table header.
        """
        query = f"SELECT * FROM {self.sql_table}"

        try:
            self.cursor.execute(query, params)
            headers = [desc[0] for desc in self.cursor.description]
            print(headers)

        except Exception as e:
            self.logger.error(f"Fetch table {self.sql_table} failed", exc_info=True)
 
    def get_sql_status(self, params: tuple = None):
        """
        Fetch and print all commit_statuses from the given table.
        Returns all rows.
        """
        result = []
        query = f"SELECT commit_statuses FROM {self.sql_table}"

        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            for row in rows:
                result.append(row[0])
            
            self._counter(sql_database=result)

        except Exception as e:
            self.logger.error(f"Fetch table {self.sql_table} failed", exc_info=True)

    def _counter(self, sql_database):
        print("============================")
        categories = {
            "token_too_long" : [],  # Token too long
            "connection_error" : [],  # connection, web service, ...
            "budget_exceeded" : [],  # VIO budget
            "incorrect_score" : [],  # not low/medium/high --> 好的。。。
            "normal_review" : []  # 正常 
        }

        for line in sql_database:
            lower_line = line.lower()

            if "input tokens" in lower_line or "input is too long" in lower_line or "too many total text bytes" in lower_line:
                categories["token_too_long"].append(lower_line)
            elif "could not connect" in lower_line or "timed out" in lower_line or "bedrock" in lower_line or "503" in lower_line or "connection error" in lower_line:
                categories["connection_error"].append(lower_line)
            elif "budget has been exceeded" in lower_line:
                categories["budget_exceeded"].append(lower_line)
            elif any(incorrect_score in lower_line for incorrect_score in ["好的"]):
                categories["incorrect_score"].append(lower_line)
            elif any(level in lower_line for level in ["high", "low", "medium"]):
                categories["normal_review"].append(lower_line)
            else:
                print(line)

        
        total_count = 0
        for category, items in categories.items():
            count = len(items)
            total_count += count
            print(f"Category '{category}': {count} entries")

        print("----------------------------")
        print(f"Total entries: {total_count}")
        print("============================")

    def close(self):
        """
        Close the cursor and database connection.
        """
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
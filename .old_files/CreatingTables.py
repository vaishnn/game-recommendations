import pymysql
from pymysql import cursors
import os
from dotenv import load_dotenv
import yaml

class SchemaCreator:
    def __init__(self, filepath: str):
        load_dotenv()
        self.db_host = str(os.getenv('DB_HOST'))
        self.db_user = str(os.getenv('DB_USER'))
        self.db_password = str(os.getenv('DB_PASSWORD'))
        self.db_name = str(os.getenv('DB_NAME'))

        self.connection = None
        self.schema_config = self._load_schema_config(filepath=filepath)

        if not all([self.db_host, self.db_user, self.db_password, self.db_name]):
            print("Missing required environment variables")
            return

        if not self.schema_config:
            print("Error: Could not load schema configuration from schema.yaml. Aborting.")
            return

        try:
            self.connection = pymysql.connect(
                host = self.db_host,
                user = self.db_user,
                password = self.db_password,
                database = self.db_name,
                cursorclass = cursors.DictCursor
            )
            print("Database connection established")
        except pymysql.Error as e:
            print(f"Error connecting to database: {e}")
            self.connection = None
            return

    def _load_schema_config(self, filepath):
        try:
            with open(filepath, "r") as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Error: Schema config file not found at {filepath}")
            return None
        except yaml.YAMLError as e:
            print(f"Error Parsing YAML file {filepath}: {e}")
            return None

    def _execute_sql(self, sql_query, params = None):
        if not self.connection:
            print("No active database connection")
            return
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)
            self.connection.commit()
        except pymysql.Error as e:
            print(f"Error executing SQL query: {e}")
            self.connection.rollback()
            return

    def drop_all_tables(self):
        print("-- Dropping all tables --")
        if not self.schema_config or 'drop_order' not in self.schema_config:
            print("Error: Missing required schema configuration")
            return
        for table_name in self.schema_config['drop_order']:
            query = f"DROP TABLE IF EXISTS {table_name}"
            try:
                self._execute_sql(query)
                print(f"Table {table_name} dropped successfully")
            except Exception as e:
                print(f"Error dropping table {table_name}: {e}")

        print("All tables dropped successfully")

    def create_all_tables(self):
        print("--Creating all tables--")
        if (not self.schema_config or
        "create_order" not in self.schema_config or
        "tables" not in self.schema_config):
            print("Error: Missing required schema configuration")
            return

        for table_name in self.schema_config['create_order']:
            sql_query = self.schema_config['tables'][table_name]
            if sql_query:
                try:
                    self._execute_sql(sql_query)
                    print(f"Table {table_name} created successfully")
                except Exception as e:
                    print(f"Error creating table {table_name}: {e}")
                    raise
            else:
                print(f"Skipping table {table_name} as no SQL query provided")

        print("All tables created successfully")

    def close(self):
        if self.connection:
            self.connection.close()

if __name__ == "__main__":
    creator = SchemaCreator("schema.yaml")
    if creator.connection:
        try:
            creator.drop_all_tables()
            creator.create_all_tables()
        except Exception as e:
            print(f"Error creating tables: {e}")
        finally:
            creator.close()

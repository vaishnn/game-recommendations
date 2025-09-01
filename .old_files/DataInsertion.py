import pymysql
from pymysql import cursors
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import yaml

class DataInsertion:
    def __init__(self, schema_path):
        load_dotenv()
        self.db_host = str(os.getenv('DB_HOST'))
        self.db_user = str(os.getenv('DB_USER'))
        self.db_password = str(os.getenv('DB_PASSWORD'))
        self.db_name = str(os.getenv('DB_NAME'))
        self.schema_config = self._load_schema_config(schema_path)

        if not all([self.db_host, self.db_user, self.db_password, self.db_name]):
            print("Missing environment variables")
            return

        try:
            self.connection = pymysql.connect(
                host=self.db_host,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                cursorclass=cursors.DictCursor
            )
            print("Connection established")
        except pymysql.Error as e:
            print(f"Error connecting to database: {e}")
            self.connection = None
            return

    def _load_schema_config(self, schema_path):
        if schema_path:
            try:
                with open(schema_path, 'r') as file:
                    return yaml.safe_load(file)
            except FileNotFoundError:
                print("Schema file not found")
                return None
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file: {e}")
                return None

    def _execute_sql(self, sql_query, params = None, fetch_one = False):
        if not self.connection:
            print("No database connection")
            return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query, params)
                if fetch_one:
                    return cursor.fetchone()
                if sql_query.strip().upper().startswith(("INSERT", "UPDATE")):
                    return cursor.lastrowid
                return None
        except pymysql.Error as e:
            print(f"Error executing SQL query: {e}")
            self.connection.rollback()
            raise
        finally:
            if self.connection:
                self.connection.commit()

    def _parse_release_date(self, release_date_str):
        if not release_date_str:
            return None
        formats_to_try = [
            '%b %d, %Y',
             '%Y-%m-%d',
             '%d %b, %Y',
             '%b %Y',
             '%Y'
        ]

        for fmt in formats_to_try:
            try:
                return datetime.strptime(release_date_str, fmt)
            except ValueError:
                continue
        print(f"Can't Parse the date: {release_date_str} So storing the date as Null")
        return None

    def _sanitize_string_to_ascii(self, text):
        if text is None:
            return None
        return text.encode('ascii', 'ignore').decode('ascii')

    def _get_or_insert_id(self, table_name, name_value):
        if not name_value:
            return None
        try:
            with self.connection.cursor() as cursor:
                select_sql = f"SELECT id FROM `{table_name}` WHERE name = %s"
                cursor.execute(select_sql, (name_value,))
                result = cursor.fetchone()

                if result:
                    return result['id']

                insert_sql_lookup = self.schema_config['insert'][table_name]
                cursor.execute(insert_sql_lookup, (name_value,))
                self.connection.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error occurred while inserting/updating `{table_name}`, '{name_value}' data: {e}")
            self.connection.rollback()
            raise

    def insert_item_data(self, app_id, item_data):
        print(f"- Processing item: {item_data.get('name')} (ID: {app_id} -")

        if not self.connection:
            print("No Active Database COnnection")
            return



        # For Game Table
        item_name = self._sanitize_string_to_ascii(item_data.get('name'))
        release_date = self._parse_release_date(item_data.get("release_date"))
        price = item_data.get('price')
        if price is None:
            price = 0.0
        header_image_url = self._sanitize_string_to_ascii(item_data.get('header_image'))
        short_description = self._sanitize_string_to_ascii(item_data.get('short_description'))
        about_the_game = self._sanitize_string_to_ascii(item_data.get('about_the_game'))
        detailed_description = self._sanitize_string_to_ascii(item_data.get('detailed_description'))
        reviews_summary = self._sanitize_string_to_ascii(item_data.get('reviews'))
        website_url = self._sanitize_string_to_ascii(item_data.get('website'))
        support_url = self._sanitize_string_to_ascii(item_data.get('support_url'))
        estimated_owners = self._sanitize_string_to_ascii(item_data.get('estimated_owners'))
        positive_reviews = item_data.get('positive')
        negative_reviews = item_data.get('negative')
        recommendations = item_data.get('recommendations')

        try:
            insert_sql = self.schema_config['insert']['games']
            params = (
                app_id,
                item_name,
                release_date,
                price,
                positive_reviews,
                negative_reviews,
                recommendations,
                item_data.get('peak_ccu'),
                item_data.get('total_hours_played', 0),
                item_data.get('peak_ccu_forever', 0),
                item_data.get('metacritic_score'),
                self._sanitize_string_to_ascii(item_data.get('metacritic_url')),
                item_data.get('required_age'),
                item_data.get('dlc_count'),
                item_data.get('achievements'),
                item_data.get('average_playtime_2weeks'),
                item_data.get('average_playtime_forever'),
                item_data.get('median_playtime_2weeks'),
                item_data.get('median_playtime_forever'),
                int(item_data.get('windows')) if item_data.get('windows') is not None else None,
                int(item_data.get('mac')) if item_data.get('mac') is not None else None,
                int(item_data.get('linux')) if item_data.get('linux') is not None else None,
                header_image_url,
                website_url,
                support_url,
                self._sanitize_string_to_ascii(item_data.get('support_email')),
                estimated_owners,
                item_data.get('user_score'),
                self._sanitize_string_to_ascii(item_data.get('score_rank')),
                about_the_game,
                detailed_description,
                short_description,
                reviews_summary,
                self._sanitize_string_to_ascii(item_data.get('notes'))
            )

            self._execute_sql(insert_sql, params)
            print(f" - Insered/Updated the core game data for '{item_name}' (ID: {app_id})")

            def get_or_insert_id(table_name, name_value):
                if not name_value:
                    return None
                try:
                    with self.connection.cursor() as cursor:
                        select_sql = f"SELECT id FROM `{table_name}` WHERE name = %s"
                        cursor.execute(select_sql, (name_value,))
                        result = cursor.fetchone()

                        if result:
                            return result['id']

                        insert_sql_lookup = self.schema_config['insert'][table_name]
                        cursor.execute(insert_sql_lookup, (name_value,))
                        self.connection.commit()
                        return cursor.lastrowid
                except Exception as e:
                    print(f"Error occurred while inserting/updating '{table_name}', '{name_value}' data: {e}")
                    self.connection.rollback()
                    raise

            for dev_name in item_data.get('developers', []):
                dev_id = get_or_insert_id('developers', dev_name)
                if dev_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_developers'],
                        (app_id, dev_id)
                    )
            for pub_name in item_data.get('publishers', []):
                pub_id = get_or_insert_id('publishers', pub_name)
                if pub_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_publishers'],
                        (app_id, pub_id)
                    )
            for cat_name in item_data.get('categories', []):
                cat_id = get_or_insert_id('categories', cat_name)
                if cat_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_categories'],
                        (app_id, cat_id)
                    )
            for gen_name in item_data.get('genres', []):
                gen_id = get_or_insert_id('genres', gen_name)
                if gen_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_genres'],
                        (app_id, gen_id)
                    )
            for lang_name in item_data.get('full_audio_languages', []):
                lang_id = get_or_insert_id('audio_languages', lang_name)
                if lang_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_audio_languages'],
                        (app_id, lang_id)
                    )
            for lang_name in item_data.get('supported_languages', []):
                lang_id = get_or_insert_id('languages', lang_name)
                if lang_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_supported_languages'],
                        (app_id, lang_id)
                    )
            for tag_name, tag_value in item_data.get('tags', {}).items():
                tag_id = get_or_insert_id('tags', tag_name)
                if tag_id:
                    self._execute_sql(
                        self.schema_config['insert']['game_tags'],
                        (app_id, tag_id, tag_value)
                    )
        except Exception as e:
                    print(f"Error during data insertion for '{item_name}' (ID: {app_id}): {e}")
                    self.connection.rollback() # Ensure rollback on error

    def close(self):
        if self.connection:
            self.connection.close()
            print("Database Connecton is closed for data insertion")


if __name__ == "__main__":
    insertion = DataInsertion("schema.yaml")

    if insertion.connection:
        try:
            path_of_json_file = "data_games/small_games.json" # Small data for trial

            if not os.path.exists(path_of_json_file):
                print(f"Error while fetching the data from {path_of_json_file}, path doesn't exist")
            else:
                with open(path_of_json_file, "r") as file:
                    raw_data = json.load(file)


                if isinstance(raw_data, dict):
                    for app_id_str, item_data in raw_data.items():
                        try:
                            app_id = int(app_id_str)
                            insertion.insert_item_data(app_id, item_data)
                        except ValueError:
                            print(f"Warning: Invalid App ID {app_id_str}, skipping this item")
                else:
                    print("Warning: Invalid data format, expected dictionary")
        except Exception as e:
            print(f"An Error Occurred: {e}")
        finally:
            insertion.close()

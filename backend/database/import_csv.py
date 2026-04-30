from pathlib import Path

import mysql.connector

from db_settings import get_db_name, get_mysql_config, load_environment


BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATION_FILE = BACKEND_DIR / "database" / "migrations" / "001_initial_schema.sql"


def resolve_csv(filename):
    path = BACKEND_DIR / "data" / filename
    if path.exists():
        return path
    raise FileNotFoundError(f"CSV file not found: {path}")


def create_database():
    db_name = get_db_name()
    conn = mysql.connector.connect(**get_mysql_config(include_database=False))
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
        )
        print(f"Database '{db_name}' is ready.")
    finally:
        cursor.close()
        conn.close()


def run_migration():
    if not MIGRATION_FILE.exists():
        raise FileNotFoundError(f"Migration file not found: {MIGRATION_FILE}")

    sql_script = MIGRATION_FILE.read_text(encoding="utf-8")
    conn = mysql.connector.connect(**get_mysql_config(include_database=True))
    cursor = conn.cursor()

    try:
        statements = sql_script.split(";")

        for statement in statements:
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)

        conn.commit()
        print("Schema migration completed.")

    finally:
        cursor.close()
        conn.close()


def load_occupations(cursor, csv_path):
    query = """
        LOAD DATA LOCAL INFILE %s
        REPLACE INTO TABLE occupations
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (@onet_code, @title, @description)
        SET
            onet_code = NULLIF(TRIM(@onet_code), ''),
            title = CASE
                WHEN RIGHT(TRIM(@title), 1) = 's'
                    AND RIGHT(TRIM(@title), 2) != 'ss'
                THEN LEFT(TRIM(@title), LENGTH(TRIM(@title)) - 1)
                ELSE TRIM(@title)
            END,
            description = NULLIF(TRIM(@description), '')
    """
    cursor.execute(query, (csv_path.as_posix(),))


def load_technology_skills(cursor, csv_path):
    query = """
        LOAD DATA LOCAL INFILE %s
        INTO TABLE technology_skills
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\n'
        IGNORE 1 LINES
        (@onet_code, @technology, @trendy, @demand)
        SET
            onet_code = NULLIF(TRIM(@onet_code), ''),
            technology = NULLIF(TRIM(@technology), ''),
            trendy = COALESCE(NULLIF(LEFT(UPPER(TRIM(@trendy)), 1), ''), 'N'),
            demand = COALESCE(NULLIF(LEFT(UPPER(TRIM(@demand)), 1), ''), 'N')
    """
    cursor.execute(query, (csv_path.as_posix(),))


def is_table_empty(cursor, table_name):
    allowed_tables = {"occupations", "technology_skills"}
    if table_name not in allowed_tables:
        raise ValueError(f"Unsupported table name: {table_name}")

    cursor.execute(f"SELECT 1 FROM `{table_name}` LIMIT 1")
    return cursor.fetchone() is None


def import_csv_data():
    occupations_csv = resolve_csv("occupations.csv")
    technology_csv = resolve_csv("technology_skills.csv")

    conn = mysql.connector.connect(
        **get_mysql_config(include_database=True, allow_local_infile=True)
    )
    cursor = conn.cursor()
    try:
        if is_table_empty(cursor, "occupations"):
            print("[INFO] Occupations table is empty. Loading data...")
            load_occupations(cursor, occupations_csv)
            print(f"[INFO] Loaded: {occupations_csv}")
        else:
            print("[INFO] Occupations already loaded. Skipping.")

        if is_table_empty(cursor, "technology_skills"):
            print("[INFO] Technology skills table is empty. Loading data...")
            load_technology_skills(cursor, technology_csv)
            print(f"[INFO] Loaded: {technology_csv}")
        else:
            print("[INFO] Technology skills already loaded. Skipping.")

        conn.commit()
        print("[INFO] CSV import step completed.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def main():
    print("Starting CSV bulk import setup...")
    load_environment()
    try:
        print("[1/3] Creating database...")
        create_database()
        print("[2/3] Running migration...")
        run_migration()
        print("[3/3] Loading CSV files with LOAD DATA LOCAL INFILE...")
        import_csv_data()
        print("Done. Database and CSV data are ready.")
        return 0
    except Exception as exc:
        print(f"Import failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

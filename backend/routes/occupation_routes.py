from flask import Blueprint, request, jsonify
import mysql.connector

from db_settings import get_mysql_config, load_environment

occupation_bp = Blueprint("occupation", __name__)
load_environment()

def get_connection():
    return mysql.connector.connect(**get_mysql_config(include_database=True))


@occupation_bp.route("/api/occupations/search", methods=["GET"])
def search_occupations():
    query = request.args.get("q", "")

    if not query:
        return jsonify([])

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT title, onet_code
        FROM occupations
        WHERE title LIKE %s
        LIMIT 20
    """

    cursor.execute(sql, (f"%{query}%",))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(results)

@occupation_bp.route("/api/occupations/skills/<onet_code>", methods=["GET"])
def get_skills_by_onet(onet_code):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT technology
            FROM technology_skills
            WHERE onet_code = %s AND demand = 'Y'
        """, (onet_code,))

        results = cursor.fetchall()

        if len(results) < 10:
            cursor.execute("""
                SELECT technology
                FROM technology_skills
                WHERE onet_code = %s 
                AND (demand = 'Y' OR trendy = 'Y')
            """, (onet_code,))
            
            results = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
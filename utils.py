import psycopg2

def run_sql_query(sql_query: str):
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="financial_db",
            user="financial_user",
            password="financial-agent"
        )
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()
        if not results:
            return []
        return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        return f"Database error: {str(e)}"
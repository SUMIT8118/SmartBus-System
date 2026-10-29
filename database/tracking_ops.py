import pandas as pd
from database.connection import get_connection

# Popular stops coordinates (Shirpur region & connections)
CITY_COORDINATES = {
    "shirpur": (21.3500, 74.8800),
    "dhule": (20.9042, 74.7749),
    "malegaon": (20.5579, 74.5289),
    "nashik": (19.9975, 73.7898),
    "pune": (18.5204, 73.8567),
    "mumbai": (19.0760, 72.8777),
    "surat": (21.1702, 72.8311),
    "indore": (22.7196, 75.8577),
    "aurangabad": (19.8762, 75.3433),
    "chalisgaon": (20.4634, 75.0169)
}

def update_bus_location(bus_id, latitude, longitude):
    """Admin ya Driver dwara bus ki latest GPS location update karna."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO bus_locations (bus_id, latitude, longitude)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (bus_id, latitude, longitude))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Bus Live Location successfully update ho gayi!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Location Update Error: {e}"

def get_latest_bus_location(bus_id):
    """Bus ki sabse latest location return karta hai."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT latitude, longitude, recorded_at 
            FROM bus_locations 
            WHERE bus_id = %s 
            ORDER BY recorded_at DESC LIMIT 1
        """
        cursor.execute(query, (bus_id,))
        loc = cursor.fetchone()
        cursor.close()
        conn.close()
        return loc
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return None

def add_route_stop(route_id, stop_name, stop_order):
    """Route ke intermediates stops add karna."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO bus_stops (route_id, stop_name, stop_order)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (route_id, stop_name, stop_order))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Stop successfully add ho gaya!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Stop Error: {e}"

def get_route_stops(route_id):
    """Route ke assigned stops list fetch karta hai."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT stop_id, stop_name, stop_order 
            FROM bus_stops 
            WHERE route_id = %s 
            ORDER BY stop_order ASC
        """
        df = pd.read_sql(query, conn, params=(route_id,))
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()
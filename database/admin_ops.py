import pandas as pd
from database.connection import get_connection

# ----------------- BUS OPERATIONS -----------------

def add_bus(bus_number, bus_name, bus_type, total_seats, ac, wifi, charging_point):
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO buses (bus_number, bus_name, bus_type, total_seats, ac, wifi, charging_point, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
        """
        cursor.execute(query, (bus_number, bus_name, bus_type, total_seats, int(ac), int(wifi), int(charging_point)))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Bus '{bus_name} ({bus_number})' successfully add ho gayi!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Error: {e}"

def get_all_buses():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = "SELECT bus_id, bus_number, bus_name, bus_type, total_seats, ac, wifi, charging_point, active FROM buses"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

# ----------------- ROUTE OPERATIONS -----------------

def add_route(source, destination, distance_km, estimated_minutes, base_fare):
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO routes (source, destination, distance_km, estimated_minutes, base_fare)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (source, destination, distance_km, estimated_minutes, base_fare))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Route '{source} ➡️ {destination}' successfully add ho gaya!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Error: {e}"

def get_all_routes():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = "SELECT route_id, source, destination, distance_km, estimated_minutes, base_fare FROM routes"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

# ----------------- TRIP OPERATIONS -----------------

def add_trip(bus_id, route_id, departure_time, arrival_time):
    conn = get_connection()
    if not conn:
        return False, "Database connection failed."
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO trips (bus_id, route_id, departure_time, arrival_time)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (bus_id, route_id, departure_time, arrival_time))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Trip successfully schedule ho gayi!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Error: {e}"

def get_all_trips():
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                t.trip_id,
                b.bus_number,
                b.bus_name,
                b.bus_type,
                b.total_seats,
                r.source,
                r.destination,
                t.departure_time,
                t.arrival_time,
                r.base_fare
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            ORDER BY t.departure_time ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

def search_trips(source, destination, travel_date):
    """Passenger ke liye trips filter karke laata hai."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                t.trip_id,
                b.bus_id,
                b.bus_number,
                b.bus_name,
                b.bus_type,
                b.total_seats,
                b.ac,
                b.wifi,
                b.charging_point,
                r.source,
                r.destination,
                t.departure_time,
                t.arrival_time,
                r.estimated_minutes,
                r.base_fare
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE LOWER(r.source) = LOWER(%s)
              AND LOWER(r.destination) = LOWER(%s)
              AND DATE(t.departure_time) = %s
            ORDER BY t.departure_time ASC
        """
        df = pd.read_sql(query, conn, params=(source, destination, str(travel_date)))
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

# ----------------- ANALYTICS & EXCEL OPS -----------------

def get_analytics_metrics():
    """Admin dashboard ke key business metrics calculate karta hai."""
    conn = get_connection()
    if not conn:
        return {"total_revenue": 0, "total_bookings": 0, "active_buses": 0}
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total_revenue FROM payments WHERE payment_status = 'Completed'")
        rev = cursor.fetchone()["total_revenue"]
        
        cursor.execute("SELECT COUNT(*) AS total_bookings FROM bookings WHERE status = 'Confirmed'")
        books = cursor.fetchone()["total_bookings"]
        
        cursor.execute("SELECT COUNT(*) AS active_buses FROM buses WHERE active = 1")
        buses = cursor.fetchone()["active_buses"]
        
        cursor.close()
        conn.close()
        return {
            "total_revenue": rev,
            "total_bookings": books,
            "active_buses": buses
        }
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return {"total_revenue": 0, "total_bookings": 0, "active_buses": 0}

def get_all_bookings_report():
    """Excel export aur detailed view ke liye complete bookings data laata hai."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                b.booking_id AS 'Booking ID',
                b.ticket_code AS 'Ticket Code',
                u.full_name AS 'Passenger Name',
                u.email AS 'Passenger Email',
                u.phone AS 'Phone Number',
                bk.bus_name AS 'Bus Name',
                bk.bus_number AS 'Bus Number',
                r.source AS 'Source',
                r.destination AS 'Destination',
                t.departure_time AS 'Departure Time',
                b.seat_number AS 'Seat Number',
                b.fare AS 'Fare (INR)',
                p.payment_method AS 'Payment Method',
                p.payment_status AS 'Payment Status',
                b.status AS 'Booking Status',
                b.booked_at AS 'Booking Timestamp'
            FROM bookings b
            JOIN users u ON b.user_id = u.user_id
            JOIN trips t ON b.trip_id = t.trip_id
            JOIN buses bk ON t.bus_id = bk.bus_id
            JOIN routes r ON t.route_id = r.route_id
            LEFT JOIN payments p ON b.booking_id = p.booking_id
            ORDER BY b.booked_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()
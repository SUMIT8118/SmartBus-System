import io
import uuid
import qrcode
import pandas as pd
from database.connection import get_connection

def get_booked_seats(trip_id):
    """Trip ke liye already confirmed booked seats ki list return karta hai."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        query = "SELECT seat_number FROM bookings WHERE trip_id = %s AND status = 'confirmed'"
        cursor.execute(query, (trip_id,))
        seats = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return seats
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return []

def book_ticket_with_payment(user_id, trip_id, seat_number, fare, payment_method):
    """Confirmed ticket book karta hai aur payment record banata hai."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed.", None

    try:
        cursor = conn.cursor()
        check_query = "SELECT booking_id FROM bookings WHERE trip_id = %s AND seat_number = %s AND status = 'confirmed'"
        cursor.execute(check_query, (trip_id, seat_number))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, f"Seat {seat_number} pehle se book ho chuki hai! Kripya dusri seat chunein.", None

        ticket_code = "SB-" + uuid.uuid4().hex[:8].upper()

        book_sql = """
            INSERT INTO bookings (ticket_code, user_id, trip_id, seat_number, fare, status)
            VALUES (%s, %s, %s, %s, %s, 'confirmed')
        """
        cursor.execute(book_sql, (ticket_code, user_id, trip_id, seat_number, fare))
        booking_id = cursor.lastrowid

        pay_sql = """
            INSERT INTO payments (booking_id, amount, payment_status, payment_method)
            VALUES (%s, %s, 'Completed', %s)
        """
        cursor.execute(pay_sql, (booking_id, fare, payment_method))

        conn.commit()
        cursor.close()
        conn.close()

        ticket_details = {
            "booking_id": booking_id,
            "ticket_code": ticket_code,
            "seat_number": seat_number,
            "fare": fare,
            "payment_method": payment_method
        }
        return True, "Ticket Successfully Booked!", ticket_details
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Booking Error: {e}", None

def get_user_bookings(user_id):
    """User ki sari bookings fetch karta hai."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                b.booking_id,
                b.ticket_code,
                bk.bus_name,
                bk.bus_number,
                r.source,
                r.destination,
                t.departure_time,
                b.seat_number,
                b.fare,
                b.status,
                b.booked_at
            FROM bookings b
            JOIN trips t ON b.trip_id = t.trip_id
            JOIN buses bk ON t.bus_id = bk.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE b.user_id = %s
            ORDER BY b.booked_at DESC
        """
        df = pd.read_sql(query, conn, params=(user_id,))
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

def cancel_ticket(booking_id):
    """Ticket status ko 'cancelled' karta hai."""
    conn = get_connection()
    if not conn:
        return False, "Database connection error."
    try:
        cursor = conn.cursor()
        query = "UPDATE bookings SET status = 'cancelled' WHERE booking_id = %s"
        cursor.execute(query, (booking_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Ticket successfully cancel ho gaya! Seat ab available hai."
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Cancellation Error: {e}"

def get_alternative_buses(source, destination, travel_date, exclude_trip_id):
    """Selected bus ke alawa usi route par bachi hui available buses fetch karta hai."""
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                t.trip_id,
                b.bus_name,
                b.bus_number,
                b.bus_type,
                b.total_seats,
                r.source,
                r.destination,
                t.departure_time,
                t.arrival_time,
                r.base_fare,
                (b.total_seats - (
                    SELECT COUNT(*) FROM bookings 
                    WHERE trip_id = t.trip_id AND status = 'confirmed'
                )) AS available_seats
            FROM trips t
            JOIN buses b ON t.bus_id = b.bus_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE LOWER(r.source) = LOWER(%s)
              AND LOWER(r.destination) = LOWER(%s)
              AND DATE(t.departure_time) = %s
              AND t.trip_id != %s
            HAVING available_seats > 0
            ORDER BY t.departure_time ASC
        """
        df = pd.read_sql(query, conn, params=(source, destination, str(travel_date), exclude_trip_id))
        conn.close()
        return df
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return pd.DataFrame()

def join_waiting_list(user_id, trip_id, fare):
    """Bus full hone par waiting list status ke sath ticket allocate karta hai."""
    conn = get_connection()
    if not conn:
        return False, "Database connection error."
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE trip_id = %s AND status = 'waiting'", (trip_id,))
        wait_count = cursor.fetchone()[0] + 1
        
        ticket_code = "WL-" + uuid.uuid4().hex[:8].upper()
        seat_label = f"WL-{wait_count}"

        query = """
            INSERT INTO bookings (ticket_code, user_id, trip_id, seat_number, fare, status)
            VALUES (%s, %s, %s, %s, %s, 'waiting')
        """
        cursor.execute(query, (ticket_code, user_id, trip_id, seat_label, fare))
        booking_id = cursor.lastrowid

        pay_sql = """
            INSERT INTO payments (booking_id, amount, payment_status, payment_method)
            VALUES (%s, %s, 'Completed', 'Online / Waiting')
        """
        cursor.execute(pay_sql, (booking_id, fare))

        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Aap Waiting List me add ho gaye hain! Ticket Code: {ticket_code} ({seat_label})"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Waiting List Error: {e}"

def generate_ticket_qr(ticket_data_str):
    """QR Code image bytes banata hai."""
    qr = qrcode.QRCode(version=1, box_size=10, border=3)
    qr.add_data(ticket_data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
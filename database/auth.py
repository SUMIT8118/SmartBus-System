import hashlib
from database.connection import get_connection

def hash_password(password: str) -> str:
    """Password ko SHA-256 se hash karta hai."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(full_name, email, phone, password, role="Passenger"):
    """Naya user register karta hai."""
    conn = get_connection()
    if not conn:
        return False, "Database connection error."
    
    try:
        cursor = conn.cursor(dictionary=True)
        # Check karein ki email pehle se exist toh nahi karta
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, "Yeh email pehle se registered hai!"
        
        # Hash password and insert
        hashed = hash_password(password)
        query = """
            INSERT INTO users (full_name, email, phone, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (full_name, email, phone, hashed, role))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Registration successful! Ab aap login kar sakte hain."
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return False, f"Error: {e}"

def login_user(email, password):
    """User credentials verify karke user object return karta hai."""
    conn = get_connection()
    if not conn:
        return None, "Database connection error."
    
    try:
        cursor = conn.cursor(dictionary=True)
        hashed = hash_password(password)
        query = "SELECT user_id, full_name, email, phone, role FROM users WHERE email = %s AND password_hash = %s"
        cursor.execute(query, (email, hashed))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return user, "Login successful!"
        else:
            return None, "Galat Email ya Password!"
    except Exception as e:
        if conn and conn.is_connected():
            conn.close()
        return None, f"Error: {e}"
# app.py
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import requests
import json
import re # For parsing Gemini's response
import os # For SECRET_KEY

app = Flask(__name__)
# IMPORTANT: Set a strong secret key for session management!
# In a production environment, use an environment variable: os.environ.get('FLASK_SECRET_KEY')
app.secret_key = os.urandom(24) # Generates a random 24-byte key for development

# Allow CORS for frontend to communicate with backend
# For production, restrict origins to your frontend's domain
CORS(app, supports_credentials=True) # supports_credentials is crucial for sending cookies/sessions

DATABASE = 'bill_warranty.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database schema if it doesn't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL -- In production, store hashed passwords!
            )
        ''')
        # Create bills table (linked to user)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                bill_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create warranties table (linked to user)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warranties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                end_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create settings table for target amount (linked to user)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                target_amount REAL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()

# Initialize the database when the app starts
with app.app_context():
    init_db()

# --- User Authentication Functions (Simplified for example) ---
def get_user_id():
    """Retrieves the user ID from the session."""
    return session.get('user_id')

def login_required(f):
    """Decorator to protect routes that require authentication."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_user_id() is None:
            return jsonify({'error': 'Authentication required. Please log in.'}), 401
        return f(*args, **kwargs)
    return decorated_function

# --- Email Notification Placeholder ---
def send_email_notification(recipient_email, username, total_spent, target_amount, time_frame):
    """
    Placeholder function to simulate sending an email notification.
    This function currently prints the email content to the Flask console.
    
    To send actual emails, you would need to integrate a real email sending service
    or library (e.g., smtplib, Flask-Mail, SendGrid, Mailgun) and configure it
    with your email server details and credentials.
    """
    subject = "Spending Alert: You've Exceeded Your Target!"
    body = f"""
    Dear {username},

    This is an automated notification from your Bill & Warranty Tracker.

    Your total spending in the last {time_frame} week(s) is ₹ {total_spent:.2f},
    which has exceeded your target amount of ₹ {target_amount:.2f}.

    Consider reviewing your recent expenses.

    Best regards,
    Your Tracker App
    """
    print(f"\n--- SIMULATED EMAIL SENT ---")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print(f"---------------------------\n")
    # Example of how you might use smtplib (requires configuration):
    # import smtplib
    # from email.mime.text import MIMEText
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = "your_app_email@example.com" # Replace with your sender email
    # msg['To'] = recipient_email
    # try:
    #     with smtplib.SMTP('smtp.example.com', 587) as server: # Replace with your SMTP server and port
    #         server.starttls()
    #         server.login("your_app_email@example.com", "your_app_password") # Replace with your email credentials
    #         server.send_message(msg)
    #     print(f"Real email sent to {recipient_email}")
    # except Exception as e:
    #     print(f"Failed to send real email to {recipient_email}: {e}")


# --- Flask Routes for serving HTML and static files ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

# --- User Authentication Endpoints ---
@app.route('/api/register', methods=['POST'])
def register():
    """Registers a new user."""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password') # In production, hash this password!

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required.'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                       (username, email, password))
        conn.commit()
        user_id = cursor.lastrowid
        # Initialize settings for the new user
        conn.execute('INSERT INTO settings (user_id, target_amount) VALUES (?, ?)', (user_id, 0.0))
        conn.commit()

        session['user_id'] = user_id
        session['username'] = username
        session['email'] = email
        return jsonify({'message': 'Registration successful', 'user': {'id': user_id, 'username': username, 'email': email}}), 201
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Username or email already exists.'}), 409
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error during registration: {e}")
        return jsonify({'error': 'Database error during registration.'}), 500
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    """Logs in an existing user."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password') # In production, compare with hashed password!

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, username, email, password FROM users WHERE username = ?', (username,)).fetchone()
        if user and user['password'] == password: # In production: bcrypt.checkpw(password, user['password_hash'])
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            return jsonify({'message': 'Login successful', 'user': {'id': user['id'], 'username': user['username'], 'email': user['email']}})
        else:
            return jsonify({'error': 'Invalid username or password.'}), 401
    except sqlite3.Error as e:
        print(f"Database error during login: {e}")
        return jsonify({'error': 'Database error during login.'}), 500
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Logs out the current user."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('email', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/user_status', methods=['GET'])
def user_status():
    """Returns the current user's login status and info."""
    user_id = get_user_id()
    if user_id:
        return jsonify({'isLoggedIn': True, 'user': {'id': user_id, 'username': session.get('username'), 'email': session.get('email')}})
    return jsonify({'isLoggedIn': False})


# --- API Endpoints for Bill Tracking (Protected) ---

@app.route('/api/target', methods=['GET'])
@login_required
def get_target_amount():
    """Retrieves the current target spending amount for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    target = conn.execute('SELECT target_amount FROM settings WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return jsonify({'targetAmount': target['target_amount'] if target else 0.0})

@app.route('/api/target', methods=['POST'])
@login_required
def set_target_amount():
    """Sets or updates the target spending amount for the logged-in user."""
    user_id = get_user_id()
    data = request.get_json()
    amount = data.get('amount')
    if amount is None or not isinstance(amount, (int, float)) or amount < 0:
        return jsonify({'error': 'Invalid target amount'}), 400

    conn = get_db_connection()
    try:
        # UPSERT: Try to update, if not found, insert
        conn.execute('INSERT OR REPLACE INTO settings (user_id, target_amount) VALUES (?, ?)', (user_id, amount))
        conn.commit()
        return jsonify({'message': 'Target amount updated successfully', 'targetAmount': amount})
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error setting target amount for user {user_id}: {e}")
        return jsonify({'error': 'Database error setting target amount.'}), 500
    finally:
        conn.close()


@app.route('/api/bills', methods=['GET'])
@login_required
def get_bills():
    """Retrieves all stored bills for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    try:
        bills_data = conn.execute('SELECT id, amount, bill_date FROM bills WHERE user_id = ? ORDER BY bill_date DESC', (user_id,)).fetchall()
        bills_list = [dict(bill) for bill in bills_data]
        return jsonify(bills_list)
    except sqlite3.Error as e:
        print(f"Database error getting bills for user {user_id}: {e}")
        return jsonify({'error': 'Database error retrieving bills.'}), 500
    finally:
        conn.close()

@app.route('/api/bills', methods=['POST'])
@login_required
def add_bill():
    """Adds a new bill to the database for the logged-in user."""
    user_id = get_user_id()
    data = request.get_json()
    amount = data.get('amount')
    bill_date = data.get('date')

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({'error': 'Invalid bill amount. Must be a positive number.'}), 400
    if not bill_date:
        return jsonify({'error': 'Bill date is required.'}), 400

    try:
        datetime.strptime(bill_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bills (user_id, amount, bill_date) VALUES (?, ?, ?)', (user_id, amount, bill_date))
        conn.commit()
        bill_id = cursor.lastrowid
        return jsonify({'message': 'Bill added successfully', 'id': bill_id, 'amount': amount, 'date': bill_date}), 201
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding bill for user {user_id}: {e}")
        return jsonify({'error': 'Database error adding bill.'}), 500
    finally:
        conn.close()

@app.route('/api/bills/<int:bill_id>', methods=['DELETE'])
@login_required
def delete_bill(bill_id):
    """Deletes a bill by its ID for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bills WHERE id = ? AND user_id = ?', (bill_id, user_id))
        conn.commit()
        rows_affected = cursor.rowcount
        if rows_affected == 0:
            return jsonify({'error': 'Bill not found or not authorized to delete.'}), 404
        return jsonify({'message': 'Bill deleted successfully'})
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error deleting bill for user {user_id}: {e}")
        return jsonify({'error': 'Database error deleting bill.'}), 500
    finally:
        conn.close()

@app.route('/api/spending', methods=['GET'])
@login_required
def check_spending():
    """Calculates total spending within a specified time frame for the logged-in user."""
    user_id = get_user_id()
    time_frame = request.args.get('timeFrame', type=int) # In weeks
    if time_frame not in [1, 2, 3]:
        return jsonify({'error': 'Invalid time frame. Must be 1, 2, or 3 weeks.'}), 400

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(weeks=time_frame)

    conn = get_db_connection()
    try:
        bills_data = conn.execute(
            'SELECT amount FROM bills WHERE user_id = ? AND bill_date BETWEEN ? AND ?',
            (user_id, start_date.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))
        ).fetchall()

        total_spent = sum(bill['amount'] for bill in bills_data)

        target = conn.execute('SELECT target_amount FROM settings WHERE user_id = ?', (user_id,)).fetchone()
        target_amount = target['target_amount'] if target else 0.0

        response_message = f"Total spending in the last {time_frame} week(s): ₹ {total_spent:.2f}."
        notification_type = 'info'

        if target_amount > 0:
            if total_spent > target_amount:
                response_message = f"Warning: Your total spending (₹ {total_spent:.2f}) in the last {time_frame} week(s) has exceeded your target (₹ {target_amount:.2f})!"
                notification_type = 'warning'
                # Trigger email notification
                user_email = session.get('email') # Get user's email from session
                username = session.get('username')
                if user_email and username:
                    send_email_notification(user_email, username, total_spent, target_amount, time_frame)
            else:
                response_message = f"Good job! Your spending (₹ {total_spent:.2f}) is within your target (₹ {target_amount:.2f}) for the last {time_frame} week(s)."
                notification_type = 'success'

        return jsonify({
            'totalSpending': total_spent,
            'message': response_message,
            'notificationType': notification_type,
            'targetAmount': target_amount
        })
    except sqlite3.Error as e:
        print(f"Database error checking spending for user {user_id}: {e}")
        return jsonify({'error': 'Database error checking spending.'}), 500
    finally:
        conn.close()


# --- New: API Endpoint for Bill Photo Upload and OCR (Protected) ---
@app.route('/api/bills/upload', methods=['POST'])
@login_required
def upload_bill_photo():
    """
    Receives a bill photo (base64 encoded), sends it to Gemini API for analysis,
    and attempts to extract the bill amount and date.
    """
    data = request.get_json()
    image_data = data.get('imageData')
    mime_type = data.get('mimeType')

    if not image_data or not mime_type:
        return jsonify({'error': 'No image data or mime type provided.'}), 400

    # **************************************************************************
    # IMPORTANT: YOU MUST REPLACE THE EMPTY STRING BELOW WITH YOUR ACTUAL
    # GEMINI API KEY FOR THE IMAGE READING FEATURE TO WORK LOCALLY.
    # You can get one from Google AI Studio: https://aistudio.google.com/app/apikey
    #
    # Example: api_key = "AIzaSyB-YOUR-ACTUAL-API-KEY-HERE"
    # **************************************************************************
    api_key = "" # If you want to use models other than gemini-2.0-flash or imagen-3.0-generate-002, provide an API key here. Otherwise, leave this as-is.
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # Construct the payload for Gemini API
    prompt = "Extract the total bill amount from this image. If you find a date, extract that too. Respond only with a JSON object like: {\"amount\": <number>, \"date\": \"YYYY-MM-DD\"} or {\"amount\": null, \"date\": null} if not found. If there are multiple amounts, try to identify the final total. If no amount is found, return null for amount. If no date is found, return null for date."
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "amount": {"type": "NUMBER", "nullable": True},
                    "date": {"type": "STRING", "nullable": True}
                },
                "propertyOrdering": ["amount", "date"]
            }
        }
    }

    try:
        # Make sure you have 'requests' library installed: pip install requests
        response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        gemini_result = response.json()

        extracted_amount = None
        extracted_date = None

        if gemini_result.get('candidates') and len(gemini_result['candidates']) > 0:
            content_parts = gemini_result['candidates'][0].get('content', {}).get('parts')
            if content_parts and len(content_parts) > 0:
                try:
                    # Gemini is instructed to return JSON, so parse it directly
                    parsed_json = json.loads(content_parts[0]['text'])
                    extracted_amount = parsed_json.get('amount')
                    extracted_date = parsed_json.get('date')
                    
                    # Ensure amount is a number
                    if extracted_amount is not None:
                        try:
                            extracted_amount = float(extracted_amount)
                        except ValueError:
                            extracted_amount = None # Not a valid number
                    
                    # Basic date validation (YYYY-MM-DD)
                    if extracted_date:
                        try:
                            datetime.strptime(extracted_date, '%Y-%m-%d')
                        except ValueError:
                            extracted_date = None # Not a valid date format
                            
                except json.JSONDecodeError:
                    print(f"Warning: Gemini response was not valid JSON. Attempting regex. Raw response: {content_parts[0]['text']}")
                    # Fallback to regex if JSON parsing fails, though structured output is preferred
                    text_response = content_parts[0]['text']
                    amount_match = re.search(r'\"amount\":\s*(\d+\.?\d*)', text_response)
                    if amount_match:
                        try:
                            extracted_amount = float(amount_match.group(1))
                        except ValueError:
                            pass # Keep as None
                    date_match = re.search(r'\"date\":\s*\"(\d{4}-\d{2}-\d{2})\"', text_response)
                    if date_match:
                        extracted_date = date_match.group(1)
                
        return jsonify({
            'message': 'Bill photo processed.',
            'extractedAmount': extracted_amount,
            'extractedDate': extracted_date
        })

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error communicating with Gemini API: {http_err} - Response: {http_err.response.text}")
        return jsonify({'error': f'AI service HTTP error: {http_err.response.text}'}), http_err.response.status_code
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error communicating with Gemini API: {conn_err}")
        return jsonify({'error': 'Failed to connect to AI service. Check network or API endpoint.'}), 500
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error communicating with Gemini API: {timeout_err}")
        return jsonify({'error': 'AI service request timed out.'}), 500
    except requests.exceptions.RequestException as req_err:
        print(f"General request error communicating with Gemini API: {req_err}")
        return jsonify({'error': f'An error occurred with AI service request: {req_err}'}), 500
    except Exception as e:
        print(f"An unexpected error occurred during bill photo upload: {e}")
        return jsonify({'error': f'An unexpected error occurred during photo processing: {e}'}), 500


# --- API Endpoints for Warranty Tracking (Protected) ---

@app.route('/api/warranties', methods=['GET'])
@login_required
def get_warranties():
    """Retrieves all stored warranties for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    try:
        warranties_data = conn.execute('SELECT id, item_name, end_date FROM warranties WHERE user_id = ? ORDER BY end_date ASC', (user_id,)).fetchall()
        warranties_list = [dict(warranty) for warranty in warranties_data]
        return jsonify(warranties_list)
    except sqlite3.Error as e:
        print(f"Database error getting warranties for user {user_id}: {e}")
        return jsonify({'error': 'Database error retrieving warranties.'}), 500
    finally:
        conn.close()

@app.route('/api/warranties', methods=['POST'])
@login_required
def add_warranty():
    """Adds a new warranty to the database for the logged-in user."""
    user_id = get_user_id()
    data = request.get_json()
    item_name = data.get('item')
    end_date = data.get('endDate')

    if not item_name or not end_date:
        return jsonify({'error': 'Item name and end date are required'}), 400

    try:
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO warranties (user_id, item_name, end_date) VALUES (?, ?, ?)', (user_id, item_name, end_date))
        conn.commit()
        warranty_id = cursor.lastrowid
        return jsonify({'message': 'Warranty added successfully', 'id': warranty_id, 'item': item_name, 'endDate': end_date}), 201
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding warranty: {e}")
        return jsonify({'error': 'Database error adding warranty.'}), 500
    finally:
        conn.close()

@app.route('/api/warranties/<int:warranty_id>', methods=['DELETE'])
@login_required
def delete_warranty(warranty_id):
    """Deletes a warranty by its ID for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM warranties WHERE id = ? AND user_id = ?', (warranty_id, user_id))
        conn.commit()
        rows_affected = cursor.rowcount
        if rows_affected == 0:
            return jsonify({'error': 'Warranty not found or not authorized to delete.'}), 404
        return jsonify({'message': 'Warranty deleted successfully'})
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error deleting warranty: {e}")
        return jsonify({'error': 'Database error deleting warranty.'}), 500
    finally:
        conn.close()

@app.route('/api/warranties/check', methods=['GET'])
@login_required
def check_all_warranties():
    """Checks all warranties for expiration and expiring soon for the logged-in user."""
    user_id = get_user_id()
    conn = get_db_connection()
    try:
        warranties_data = conn.execute('SELECT id, item_name, end_date FROM warranties WHERE user_id = ?', (user_id,)).fetchall()

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        notifications = []
        expired_count = 0
        expiring_soon_count = 0

        for warranty in warranties_data:
            end_date = datetime.strptime(warranty['end_date'], '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)

            if end_date < today:
                notifications.append({
                    'message': f'Warranty for "{warranty["item_name"]}" expired on {end_date.strftime("%B %d, %Y")}.',
                    'type': 'error'
                })
                expired_count += 1
            else:
                days_remaining = (end_date - today).days
                if days_remaining <= 30:
                    notifications.append({
                        'message': f'Warranty for "{warranty["item_name"]}" is expiring in {days_remaining} days (on {end_date.strftime("%B %d, %Y")}).',
                        'type': 'warning'
                    })
                    expiring_soon_count += 1
        
        if not notifications:
            notifications.append({
                'message': 'No warranties expired or expiring soon.',
                'type': 'success'
            })

        notifications.append({
            'message': f'Checked all warranties. {expired_count} expired, {expiring_soon_count} expiring soon.',
            'type': 'info'
        })

        return jsonify({'notifications': notifications, 'warranties': [dict(w) for w in warranties_data]})
    except sqlite3.Error as e:
        print(f"Database error checking warranties: {e}")
        return jsonify({'error': 'Database error checking warranties.'}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

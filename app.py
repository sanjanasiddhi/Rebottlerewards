from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flaskext.mysql import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import random
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Sanjusharma@22'
app.config['MYSQL_DATABASE_DB'] = 'user_auth'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

mysql = MySQL(app)


# Password Validation Function
def is_valid_password(password):
    if len(password) < 8:
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char.islower() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char in "!@#$%^&*()" for char in password):
        return False
    return True
@app.route('/connect', methods=['GET', 'POST'])
def connect():
    return render_template('connect.html')

@app.route('/newpage')
def newpage():
    # Check if the user is logged in
    if 'userid' not in session:
        flash('You need to log in first!', 'danger')
        return redirect(url_for('login'))  # Redirect to login page if not logged in
    
    # If logged in, render the new page
    return render_template('newpage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = mysql.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user[3], password):
                session['userid'] = user[0]
                session['username'] = user[1]
                session['email'] = user[2]
                session['points'] = user[7]  # Fetch points from the correct column
                session['address'] = user[8]
                flash('Login successful!', 'success')

                # Redirect to stored URL if it exists
                intended_url = session.pop('intended_url', None)
                if intended_url:
                    return redirect(intended_url)
                return redirect(url_for('home'))

            else:
                flash('Invalid Username or Password', 'danger')
                return render_template('login.html')

        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred. Please try again.', 'danger')
            return render_template('login.html')

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('login.html')


@app.route('/check_login', methods=['GET'])

@app.route('/', methods=['GET', 'POST'])
def home():
    userid = session.get('userid')
    username = session.get('username', '')
    email = session.get('email', '')
    


    if request.method == 'POST':
        if 'shop_now' in request.form:
            if userid:
                return redirect(url_for('shop_now'))
            else:
                flash('You must be logged in to shop!', 'danger')
                session['intended_url'] = url_for('shop_now')
                return redirect(url_for('login'))

    return render_template('home.html', username=username, email=email)

@app.route('/shop_now')
def shop_now():
    
    if 'userid' not in session:
        flash('You need to log in first!', 'danger')
        session['intended_url'] = url_for('shop_now')  # Store intended destination
        return redirect(url_for('login'))
    points = session.get('points', 0)
    return render_template('shop_now.html', points=points)


# Route: Logout


@app.route('/shopping')
def shopping():
    points = session.get('points', 0)
    return render_template('shopping.html', points=points) 

@app.route('/profile')
def profile():
    userid = session.get('userid')
    username = session.get('username', '')
    email = session.get('email', '')
    points = session.get('points', 0)
    address = session.get('address')
    return render_template('profile.html', points=points, username=username, email=email, address=address) 

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return jsonify({"success": False, "error": "User not authenticated."})

    userid = session.get('username')  # Fetch username from session
    data = request.json
    new_name = data.get('new_name')
    new_email = data.get('new_email')
    new_address = data.get('new_address')

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (userid,))
    user_data = cursor.fetchone()

    if not user_data:
        return jsonify({"success": False, "error": "User not found."})

    user_id = user_data[0]  # Extract user_id

    # Update name and email if provided
    if new_name:
        cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_name, user_id))  # Use 'name' instead of 'username'
    if new_email:
        cursor.execute("UPDATE users SET email = %s WHERE id = %s", (new_email, user_id))
    if new_address:
        cursor.execute("UPDATE users SET address = %s WHERE id = %s", (new_address, user_id))

    conn.commit()
    
    return jsonify({"success": True, "message": "Profile updated successfully!"})

@app.route('/list_products', methods=['GET'])
def list_products():
   
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, category, seller, image FROM products;")
    products = cursor.fetchall()

    if not products:
        return jsonify([])  # ✅ Return an empty list if no products

    product_list = [{"name": p[0], "price": p[1], "category": p[2], "seller": p[3], "image": p[4]} for p in products]

    cursor.close()
    conn.close()

    return jsonify(product_list)  # ✅ Ensures proper JSON response


@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

# Route: Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        security_question = request.form['security_question']
        security_answer = request.form['security_answer']

        if password != confirm_password:
            flash('Passwords do not match!', 'warning')
            return redirect(url_for('signup'))

        if not is_valid_password(password):
            flash('Password must be at least 8 characters long, include uppercase, lowercase, a digit, and a special character.', 'warning')
            return redirect(url_for('signup'))
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format.", "danger")
            return redirect(url_for('signup'))


        hashed_password = generate_password_hash(password)

        conn = mysql.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password, security_question, security_answer) VALUES (%s, %s, %s, %s, %s)",
                (username, email, hashed_password, security_question, security_answer)
            )
            conn.commit()
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            error_message = str(e)

            # Check for specific duplicate entry errors
            if 'Duplicate entry' in error_message:
                if 'for key \'username\'' in error_message:
                    flash('Username already exists! Please choose a different username.', 'danger')
                elif 'for key \'email\'' in error_message:
                    flash('Email already exists! Please use a different email address.', 'danger')
                else:
                    flash('Duplicate value detected! Please check your input.', 'danger')
            else:
                flash('An error occurred. Please try again later.', 'danger')
            return redirect(url_for('signup'))
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')

# Route: Forgot Password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        security_question = request.form['security_question']
        security_answer = request.form['security_answer']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Connect to MySQL
        conn = mysql.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = %s AND email = %s AND security_question = %s AND security_answer = %s",
                    (username, email, security_question, security_answer))
        user = cursor.fetchone()

        if not user:
            flash("No matching user found.", "danger")
            return redirect(url_for('forgot_password'))

        if new_password != confirm_password:
            flash("Passwords do not match.", "warning")
            return redirect(url_for('forgot_password'))

        if not is_valid_password(new_password):
            flash('Password must be at least 8 characters long, include uppercase, lowercase, a digit, and a special character.', 'warning')
            return redirect(url_for('forgot_password'))

        hashed_password = generate_password_hash(new_password)

        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username))
        conn.commit()

        flash("Password updated successfully! You can now login with the new password.", "success")
        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/products')
def products():
    if 'userid' not in session:
        flash('You need to log in first!', 'danger')
        return redirect(url_for('login'))
    return render_template('products.html')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'rebottlerewards@gmail.com'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'qybw heru tmji tljy'  # Your Gmail app password
app.config['MAIL_USE_TLS'] = True

def generate_ticket_id():
    """Generate a shorter unique ticket ID"""
    timestamp = datetime.now().strftime('%y%m%d')  # Using 2-digit year instead of 4-digit
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))  # Reduced from 5 to 4
    return f'TK{timestamp}{random_str}'  # Changed from 'TKT' to 'TK'
def send_confirmation_email(recipient_email, ticket_id, name, message):
    """Send confirmation email to customer"""
    try:
        sender_email = app.config['MAIL_USERNAME']
        password = app.config['MAIL_PASSWORD']

        msg = MIMEMultipart()
        msg['From'] = f'ReBottle Rewards <{sender_email}>'
        msg['To'] = recipient_email
        msg['Subject'] = f'Complaint Ticket #{ticket_id} - ReBottle Rewards'

        body = f"""Dear {name},

Thank you for contacting ReBottle Rewards. We have received your complaint and it has been registered with ticket number: {ticket_id}

Your message:
{message}

We are committed to addressing your concerns as quickly as possible. Our team will review your complaint and get back to you soon.

Please keep this ticket number for future reference.

Best regards,
Customer Support Team
ReBottle Rewards"""

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        print("Attempting to login with:", sender_email)  # Debug print
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully")  # Debug print
        return True

    except Exception as e:
        print(f"Email error details: {str(e)}")  # Debug print
        return False


@app.route('/redeem_points', methods=['POST'])
def redeem_points():
    data = request.json
    points_to_redeem = int(data.get('points_to_redeem', 0))
    userid = session.get('username')  # Fetch user email from request

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, points FROM users WHERE username = %s", (userid))
    user_data = cursor.fetchone()
    
    if not user_data:
        return jsonify({"success": False, "error": "User not found."})
    
    user_id, current_points = user_data
    
    if points_to_redeem > current_points:
        return jsonify({"success": False, "error": "Not enough points to redeem."})
    
    new_points = current_points - points_to_redeem
    discount = points_to_redeem * 0.1  # Example conversion rate
    
    #cursor.execute("UPDATE users SET points = %s WHERE id = %s", (new_points, user_id))
    #conn.commit()
    
    return jsonify({"success": True, "message": "Points redeemed successfully!", "discount": discount, "remaining_points": new_points})



@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')
            
            if not all([name, email, message]):
                return jsonify({
                    'status': 'error',
                    'message': 'All fields are required'
                }), 400

            ticket_id = generate_ticket_id()

            try:
                # First, save to database
                conn = mysql.connect()
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO contact_submissions (ticket_id, name, email, message) VALUES (%s, %s, %s, %s)",
                    (ticket_id, name, email, message)
                )
                conn.commit()

                # Then, try to send email
                email_sent = send_confirmation_email(email, ticket_id, name, message)

                if email_sent:
                    return jsonify({
                        'status': 'success',
                        'message': f'Your complaint has been successfully registered with ticket number: {ticket_id}. A confirmation email has been sent to your email address.',
                        'ticket_id': ticket_id
                    })
                else:
                    return jsonify({
                        'status': 'partial',
                        'message': f'Your complaint has been registered with ticket number: {ticket_id}, but we could not send the confirmation email. Please save this ticket number for reference.',
                        'ticket_id': ticket_id
                    })

            except Exception as db_error:
                print(f"Database error details: {str(db_error)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Database error: {str(db_error)}'
                }), 500

            finally:
                if cursor:
                    cursor.close()
                if conn and conn.open:
                    conn.close()

        except Exception as e:
            print(f"General error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }), 500
                

if __name__ == '__main__':
    app.run(debug=True)
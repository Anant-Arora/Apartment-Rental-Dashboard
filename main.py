#import libraries
# --- Step 1: Updated Imports ---
# Removed old MySQL libraries, added SQLAlchemy for modern database management
from flask import Flask, redirect, render_template, flash, request, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import uuid
from werkzeug.utils import secure_filename
import os
import shutil
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# --- Step 2: Updated Configuration for Deployment ---
# Uses a single DATABASE_URL from the Render environment
app.secret_key = "apartment_rental"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the new database connection
db = SQLAlchemy(app)

# --- Main Public Routes ---
@app.route('/')
def home():
    return render_template('welcome.html')

# --- Authentication Routes (Updated to use SQLAlchemy) ---
@app.route('/AdminLogin', methods=['GET', 'POST'])
def AdminLogin():
    error = None
    if request.method == 'POST':
        if request.form.get('adminUsername') == 'admin' and \
           request.form.get('adminPass') == 'secret@123' and \
           request.form.get('securityPass') == 'apartment':
            session['admin_loggedin'] = True
            flash('You have logged in successfully!', 'success')
            return redirect(url_for('AdminDashboard'))
        else:
            error = 'Invalid credentials'
    return render_template('AdminLogin.html', error=error)

@app.route('/AdminLogout')
def AdminLogout():
    session.pop('admin_loggedin', None)
    flash('You have logged out successfully!', 'success')
    return redirect(url_for('AdminLogin'))

@app.route('/TenantLogin', methods=['GET', 'POST'])
def TenantLogin():
    error = None
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('pswd1')
        
        # Updated query syntax for SQLAlchemy
        query = text("SELECT * FROM TENANT WHERE EMAIL = :email")
        result = db.session.execute(query, {'email': email})
        account = result.fetchone()
        
        if account and check_password_hash(account.pswd, password):
            session['loggedin'] = True
            session['id'] = account.t_id
            session['username'] = account.email
            return redirect(url_for('TenantDashboard'))
        else:
            error = 'Invalid Username or Password!'
    return render_template('TenantLogin.html', error=error)

@app.route('/Logout')
def Logout():
    session.clear()
    flash('You have logged out successfully!', 'success')
    return redirect(url_for('TenantLogin'))

@app.route('/Register', methods=['GET','POST'])
def Register():
    msg1 = ''
    if request.method == 'POST':
        fname = request.form.get('firstname')
        lname = request.form.get('lastname')
        ph = request.form.get('phNo')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        occupation = request.form.get('occupation')
        email = request.form.get('email')
        pswd = request.form.get('pswd')

        if len(ph) != 10:
            msg1 = 'Phone No. must be 10 digits!'
            return render_template('tenantRegister.html', msg1=msg1)

        query = text("SELECT * FROM TENANT WHERE EMAIL = :email")
        result = db.session.execute(query, {'email': email})
        account = result.fetchone()

        if account:
            msg1 = 'Email already exists!'
        else:
            hashed_pswd = generate_password_hash(pswd)
            insert_query = text("""
                INSERT INTO TENANT (FNAME, LNAME, PH_NO, EMAIL, GENDER, DOB, OCCUPATION, PSWD) 
                VALUES (:fname, :lname, :ph, :email, :gender, :dob, :occupation, :pswd)
            """)
            db.session.execute(insert_query, {'fname': fname, 'lname': lname, 'ph': ph, 'email': email, 'gender': gender, 'dob': dob, 'occupation': occupation, 'pswd': hashed_pswd})
            db.session.commit()
            flash('You have successfully registered!', 'success')
            return redirect(url_for('TenantLogin'))
    return render_template('tenantRegister.html', msg1=msg1)

# --- Admin Dashboard Routes (All updated with security and SQLAlchemy) ---
@app.route('/AdminDashboard')
def AdminDashboard():
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))

    t_users = db.session.execute(text('SELECT COUNT(T_ID) FROM TENANT')).scalar()
    t_tenants = db.session.execute(text('SELECT COUNT(T_ID) FROM TENANT WHERE ROOM_NO IS NOT NULL')).scalar()
    occ_apts = db.session.execute(text('SELECT COUNT(ROOM_NO) FROM APARTMENT WHERE APT_STATUS = \'Occupied\'')).scalar()
    unocc_apts = db.session.execute(text('SELECT COUNT(ROOM_NO) FROM APARTMENT WHERE APT_STATUS = \'Unoccupied\'')).scalar()
    tot_apt = (occ_apts or 0) + (unocc_apts or 0)
    tot_blck = db.session.execute(text('SELECT COUNT(BLOCK_NO) FROM APARTMENT_BLOCK')).scalar()
    tot_rent = db.session.execute(text('SELECT SUM(R.RENT_FEE) FROM RENT AS R, RENT_STATUS AS S WHERE R.RENT_ID = S.RENT_ID AND S.R_STATUS = \'Paid\'')).scalar() or 0
        
    return render_template('AdminDashboard.html', occ_apts=occ_apts, unocc_apts=unocc_apts, t_tenants=t_tenants, t_users=t_users, tot_apt=tot_apt, tot_blck=tot_blck, tot_rent=tot_rent)

@app.route('/TotalUsers')
def TotalUsers():
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))
    result = db.session.execute(text('SELECT FNAME, LNAME, GENDER, PH_NO, EMAIL, ROOM_NO FROM TENANT'))
    users = result.fetchall()
    return render_template('TotalUsers.html', msg5=users)

# ... (Include all other admin and tenant routes, similarly refactored for SQLAlchemy and security) ...
# --- For brevity, I'll show the refactored ApartmentRooms as a final example ---

@app.route('/ApartmentRooms', methods=['POST','GET'])
def ApartmentRooms():
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))

    if request.method == 'POST':
        Room = request.form['room']
        Block = request.form['block']
        # ... (rest of form processing) ...

        check_query = text("SELECT * FROM APARTMENT WHERE ROOM_NO = :room")
        existing_apartment = db.session.execute(check_query, {'room': Room}).fetchone()

        if existing_apartment:
            flash(f"Error: Apartment with Room No. {Room} already exists!", "danger")
        else:
            # ... (file handling logic remains the same) ...
            
            insert_apt_query = text("INSERT INTO APARTMENT (ROOM_NO, BLOCK_NO, RENT_PER_MONTH, APT_STATUS) VALUES (:room, :block, :rent, :status)")
            db.session.execute(insert_apt_query, {'room': Room, 'block': Block, 'rent': Rent, 'status': Status})

            # ... (other inserts for details and photos) ...
            
            db.session.commit()
            flash(f"Apartment {Room} has been successfully added!", "success")
        
        return redirect(url_for('ApartmentRooms'))

    # GET request logic
    apartments_query = text("""
        SELECT A.ROOM_NO, A.BLOCK_NO, A.RENT_PER_MONTH, A.APT_STATUS, AD.APT_TITLE 
        FROM APARTMENT A 
        JOIN APARTMENT_DETAILS AD ON A.ROOM_NO = AD.ROOM_NO
    """)
    apartments = db.session.execute(apartments_query).fetchall()
    return render_template('ApartmentRoomsadmin.html', apartments=apartments)

# --- ---
# NOTE: All other functions would need to be similarly converted.
# The code for Details, Contract, Payment, etc., would follow the same pattern:
# 1. Add security check `if 'loggedin' not in session: ...`
# 2. Replace `cursor = mysql.connection.cursor(...)`
# 3. Replace `cursor.execute(...)` with `db.session.execute(text(...), {'param': value}))`
# 4. Replace `mysql.connection.commit()` with `db.session.commit()`
# 5. Replace `cursor.fetchone()` with `result.fetchone()` or `result.scalar()`
# 6. Replace `cursor.fetchall()` with `result.fetchall()`
# --- ---

# --- Step 3: REMOVE the old app.run() block ---
# The deployment server (Gunicorn) will run the app.


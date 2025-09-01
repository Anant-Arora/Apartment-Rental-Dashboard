#import libraries
from flask import Flask, redirect, render_template, flash, request, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import uuid
from werkzeug.utils import secure_filename
import os
import shutil
from werkzeug.security import generate_password_hash
# Add this line at the top of your file
from werkzeug.security import check_password_hash

app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
# app.secret_key = 'your secret key'
app.secret_key = "apartment_rental"

#code for connection
app.config['MYSQL_HOST'] = 'localhost' #hostname
app.config['MYSQL_USER'] = 'root' #username
app.config['MYSQL_PASSWORD'] = '' #password
#in my case password is null so i am keeping empty
app.config['MYSQL_DB'] = 'apartmentRental' #database name
# Intialize MySQL
mysql = MySQL(app)
           
@app.route('/')
def home() :
    return render_template('welcome.html')
    
    
@app.route('/AdminLogin', methods=['GET', 'POST'])
def AdminLogin() :
    error = None
    if request.method == 'POST' and 'adminUsername' in request.form and 'adminPass' in request.form and 'securityPass' in request.form:
        if request.form['adminUsername'] != 'admin' or \
                request.form['adminPass'] != 'secret@123' or \
                request.form['securityPass'] != 'apartment':
            error = 'Invalid credentials'
        else:
            # Set the session variable upon successful login
            session['admin_loggedin'] = True
            flash('You have logged in successfully!!', 'success')
            return redirect(url_for('AdminDashboard'))
            
    return render_template('AdminLogin.html', error=error)


@app.route('/AdminLogout')
def AdminLogout() :
    # Remove the admin session variable to log them out
    session.pop('admin_loggedin', None)
    flash('You have logged out successfully!!', 'success')
    return redirect(url_for('AdminLogin'))

@app.route('/TenantLogin', methods=['GET', 'POST'])
def TenantLogin() :
    error = None
    if request.method == 'POST' and 'username' in request.form and 'pswd1' in request.form :
        username = request.form['username']
        password = request.form['pswd1']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # 2. Fetch the user by email only
        cursor.execute('SELECT * FROM TENANT WHERE EMAIL = % s', (username, ))
        account = cursor.fetchone()
        
        # 3. Check if account exists AND if the password hash matches
        if account and check_password_hash(account['PSWD'], password):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['T_ID']
            session['username'] = account['EMAIL']
            # Redirect to home page
            flash('You have logged in successfully!!', 'success')
            return redirect(url_for('TenantDashboard'))
        else:
            # Account doesnt exist or username/password incorrect
            error = ' Invalid Username or Password !!'
            
    return render_template('TenantLogin.html', error=error)


@app.route('/Logout')
def Logout() :
    session.clear() # Clears all session data at once
    flash('You have logged out successfully!!', 'success')
    return redirect(url_for('TenantLogin'))


@app.route('/Register', methods=['GET','POST'])
def Register():
    msg1 = ''
    log = ''
    #applying empty validation
    if request.method == 'POST' and 'firstname' in request.form and 'lastname' in request.form and 'phNo' in request.form and 'dob' in request.form and 'occupation' in request.form and 'gender' in request.form and 'email' in request.form and 'pswd' in request.form:
        #passing HTML form data into python variable
        fname = request.form['firstname']
        lname = request.form['lastname']
        ph = request.form['phNo']
        dob = request.form['dob']
        gender = request.form['gender']
        occupation = request.form['occupation']
        email = request.form['email']
        pswd = request.form['pswd']

        if len(ph) != 10 :
            msg1 = 'Phone No. must be of 10 digits!!'
            return render_template('TenantRegister.html', msg1=msg1)

        #creating variable for connection
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        #query to check given data is present in database or no
        cursor.execute('SELECT * FROM TENANT WHERE EMAIL = % s', (email,))
        #fetching data from MySQL
        result = cursor.fetchone()
        
        if result:
            msg1 = 'Email already exists !'
        else:
            # 2. Hash the password from the form
            hashed_pswd = generate_password_hash(pswd)

            # 3. Use the hashed password in the database query
            cursor.execute('INSERT INTO TENANT VALUES (% s, % s, NULL , % s, % s, % s , % s , % s , NULL, % s)', (fname, lname, ph, email, gender ,dob, occupation, hashed_pswd))
            mysql.connection.commit()

            #displaying message
            flash('You have successfully registered!', 'success')
            return redirect(url_for('TenantLogin'))
            
    elif request.method == 'POST':
        msg1 = 'Please fill out the form !'
    
    return render_template('TenantRegister.html', msg1=msg1)


@app.route('/TenantRegister')
def tregister() :
    return render_template('TenantRegister.html')


#----------- ADMIN DASHBOARD----------------


@app.route('/AdminDashboard')
def AdminDashboard():
    # 1. Added security check to protect the route
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))

    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 2. Removed all unnecessary mysql.connection.commit() calls after SELECT queries
    cursor.execute('SELECT COUNT(T_ID) AS T_USERS FROM TENANT')
    result1 = cursor.fetchone()
    t_users = result1['T_USERS']
    
    cursor.execute('SELECT COUNT(T_ID) AS T_TENANTS FROM TENANT WHERE ROOM_NO IS NOT NULL')
    result2 = cursor.fetchone()
    t_tenants = result2['T_TENANTS']
    
    cursor.execute('SELECT COUNT(ROOM_NO) AS T_APTS FROM APARTMENT WHERE APT_STATUS = "Occupied"')
    result3 = cursor.fetchone()
    occ_apts = result3['T_APTS']
    
    cursor.execute('SELECT COUNT(ROOM_NO) AS T_APTS FROM APARTMENT WHERE APT_STATUS = "Unoccupied"')
    result4 = cursor.fetchone()
    unocc_apts = result4['T_APTS']
    
    tot_apt = unocc_apts + occ_apts
    
    cursor.execute('SELECT COUNT(BLOCK_NO) AS T_BLOCK FROM APARTMENT_BLOCK')
    result5 = cursor.fetchone()
    tot_blck = result5['T_BLOCK']
    
    cursor.execute('SELECT SUM(R.RENT_FEE) AS T_RENT FROM RENT AS R, RENT_STATUS AS S WHERE R.RENT_ID = S.RENT_ID AND S.R_STATUS = "Paid"')
    result6 = cursor.fetchone()
    tot_rent = result6['T_RENT']
    
    if tot_rent is None:
        tot_rent = 0
        
    return render_template('AdminDashboard.html', occ_apts=occ_apts, unocc_apts=unocc_apts, t_tenants=t_tenants, t_users=t_users, tot_apt=tot_apt, tot_blck=tot_blck, tot_rent=tot_rent)
@app.route('/TotalUsers')
def TotalUsers() :
    msg5=''   
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT FNAME, LNAME, GENDER, PH_NO, EMAIL, ROOM_NO FROM TENANT')
    mysql.connection.commit()
    msg5=cursor.fetchall()
    return render_template('TotalUsers.html', msg5=msg5)


@app.route('/tenantReport', methods=['GET','POST'])
def tenantReport() :
    tenantReport=''
    msg6=''
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #applying empty validation
    if request.method == 'POST' and 'tid' in request.form :
        #passing HTML form data into python variable
        T_ID = request.form['tid']
        #query to check given data is present in database or no
        cursor.execute('SELECT * FROM TENANT WHERE T_ID = % s', (T_ID,))
        #fetching data from MySQL
        result = cursor.fetchone()
        if result:
            #executing query to insert new data into MySQL
            cursor.execute('DELETE FROM TENANT WHERE T_ID = % s',(T_ID,))
            mysql.connection.commit()
        else:
            msg6 = 'Tenant doesn\'t exists !'
    elif request.method == 'POST':
        msg6 = 'Please fill out the details !'
    cursor.execute('SELECT T_ID, FNAME, LNAME, GENDER, PH_NO, EMAIL, ROOM_NO FROM TENANT WHERE ROOM_NO IS NOT NULL')
    mysql.connection.commit()
    tenantReport=cursor.fetchall()
    return render_template('tenantReport.html', msg6=msg6,tenantReport=tenantReport)

@app.route('/ApartmentRooms', methods=['POST','GET'])
def ApartmentRooms():
    # Security First: Ensure only a logged-in admin can access this page.
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # This part runs when you submit the "Add Apartment" form
    if request.method == 'POST' and 'room' in request.form:
        # Get all the data from the form
        Room = request.form['room']
        Block = request.form['block']
        Status = request.form['status']
        Rent = request.form['rentPerMonth']
        aptTitle = request.form['apartmentTitle'] 
        description = request.form.get('desc')
        area = request.form['area']
        
        # Check if an apartment with this room number already exists
        cursor.execute('SELECT * FROM APARTMENT WHERE ROOM_NO = %s', (Room,))
        existing_apartment = cursor.fetchone()

        if existing_apartment:
            flash(f"Error: Apartment with Room No. {Room} already exists!", "danger")
        else:
            # Handle the file uploads
            file1 = request.files['hall']
            file2 = request.files['kitchen']
            file3 = request.files['bedroom']
            file4 = request.files['extra']

            path = os.path.join('static', 'images', 'apartment' + Room)
            if not os.path.exists(path):
                os.makedirs(path)
            
            file1.save(os.path.join(path, secure_filename(file1.filename)))
            file2.save(os.path.join(path, secure_filename(file2.filename)))
            file3.save(os.path.join(path, secure_filename(file3.filename)))
            if file4 and file4.filename != '':
                file4.save(os.path.join(path, secure_filename(file4.filename)))

            # Insert the new apartment data into the database
            cursor.execute('INSERT INTO APARTMENT (ROOM_NO, BLOCK_NO, RENT_PER_MONTH, APT_STATUS) VALUES (%s, %s, %s, %s)', (Room, Block, Rent, Status))
            cursor.execute('INSERT INTO APARTMENT_DETAILS (ROOM_NO, APT_TITLE, AREA, APARTMENT_DESC) VALUES (%s, %s, %s, %s)', (Room, aptTitle, area, description))
            
            Image_url = 'images/apartment' + Room
            photo4_filename = secure_filename(file4.filename) if file4 else None
            cursor.execute('INSERT INTO APARTMENT_PHOTOS (ROOM_NO, PATHNAME, PHOTO1, PHOTO2, PHOTO3, PHOTO4) VALUES (%s, %s, %s, %s, %s, %s)', 
                           (Room, Image_url, secure_filename(file1.filename), secure_filename(file2.filename), secure_filename(file3.filename), photo4_filename))
            
            mysql.connection.commit()
            flash(f"Apartment {Room} has been successfully added!", "success")
        
        return redirect(url_for('ApartmentRooms'))

    # This part runs when you first visit the page
    # Fetch all existing apartments to display in a table
    cursor.execute('SELECT A.ROOM_NO, A.BLOCK_NO, A.RENT_PER_MONTH, A.APT_STATUS, AD.APT_TITLE FROM APARTMENT A JOIN APARTMENT_DETAILS AD ON A.ROOM_NO = AD.ROOM_NO')
    apartments = cursor.fetchall()
    
    # Render the correct template
    return render_template('ApartmentRoomsadmin.html', apartments=apartments)



@app.route('/UpdateApartment', methods=['GET','POST'])
def UpdateApartment():
    msg2=''
    msg3=''
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #applying empty validation
    if request.method == 'POST' and 'room1' in request.form and 'status1' in request.form and 'rentPerMonth1' in request.form :
        #passing HTML form data into python variable
        Room1 = request.form['room1']
        Status1 = request.form['status1']
        Rent1 = request.form['rentPerMonth1']
        area1 = request.form['up_area']
        title1 = request.form['up_title']
        #query to check given data is present in database or no
        cursor.execute('SELECT * FROM APARTMENT WHERE ROOM_NO = % s', (Room1,))
        #fetching data from MySQL
        result = cursor.fetchone()
        if result:
            #executing query to insert new data into MySQL
            cursor.execute('UPDATE APARTMENT SET RENT_PER_MONTH = % s, APT_STATUS = % s WHERE ROOM_NO = % s',(Rent1,Status1,Room1))
            mysql.connection.commit()
            cursor.execute('UPDATE APARTMENT_DETAILS SET AREA = % s, APT_TITLE = % s WHERE ROOM_NO = % s',(area1,title1,Room1))
            mysql.connection.commit()
        else:
            msg2 = 'Apartment doesn\'t exists !'
    elif request.method == 'POST':
        msg2 = 'Please fill out the form !'
    cursor.execute('SELECT APT_TITLE, A.ROOM_NO, AREA, RENT_PER_MONTH, APARTMENT_DESC FROM APARTMENT AS A, APARTMENT_DETAILS AS AD WHERE A.ROOM_NO = AD.ROOM_NO AND A.APT_STATUS = "Unoccupied"')
    mysql.connection.commit()
    msg3=cursor.fetchall() 
    cursor.execute('SELECT * FROM APARTMENT_PHOTOS')
    mysql.connection.commit()
    img_url = cursor.fetchall()
    return render_template('ApartmentRooms.html', msg2=msg2,msg3=msg3,img_url=img_url)


@app.route('/DeleteApartment', methods=['GET','POST'])
def DeleteApartment() :
    msg2=''
    msg3=''
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #applying empty validation
    if request.method == 'POST' and 'room2' in request.form :
        #passing HTML form data into python variable
        Room2 = request.form['room2']
        #query to check given data is present in database or no
        cursor.execute('SELECT * FROM APARTMENT WHERE ROOM_NO = % s', (Room2,))
        #fetching data from MySQL
        result = cursor.fetchone()
        if result:
            #executing query to insert new data into MySQL
            cursor.execute('SELECT PATHNAME FROM APARTMENT_PHOTOS WHERE ROOM_NO = % s',(Room2,))
            mysql.connection.commit()
            path = cursor.fetchone()
            pathname = 'static/'+path['PATHNAME']
            shutil.rmtree(pathname, ignore_errors=False, onerror=None)
            cursor.execute('DELETE FROM APARTMENT WHERE ROOM_NO = % s',(Room2,))
            mysql.connection.commit()
        else:
            msg2 = 'Apartment doesn\'t exists !'
    elif request.method == 'POST':
        msg2 = 'Please fill out the form !'
    cursor.execute('SELECT APT_TITLE, A.ROOM_NO, AREA, RENT_PER_MONTH, APARTMENT_DESC FROM APARTMENT AS A, APARTMENT_DETAILS AS AD WHERE A.ROOM_NO = AD.ROOM_NO AND A.APT_STATUS = "Unoccupied"')
    mysql.connection.commit()
    msg3=cursor.fetchall() 
    cursor.execute('SELECT * FROM APARTMENT_PHOTOS')
    mysql.connection.commit()
    img_url = cursor.fetchall()
    return render_template('ApartmentRooms.html', msg2=msg2,msg3=msg3,img_url=img_url)


@app.route('/RentStatus')
def RentStatus() :
    rent_status=''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT FNAME, LNAME, T.ROOM_NO, RENT_PER_MONTH, DUE_DATE, R_STATUS, LATE_FEE FROM RENT AS R, APARTMENT AS A, RENT_STATUS AS RS, TENANT AS T WHERE R.RENT_ID = RS.RENT_ID AND T.T_ID = R.T_ID AND A.ROOM_NO = T.ROOM_NO')
    mysql.connection.commit()
    rent_status=cursor.fetchall()
    # cursor.execute('CALL RENTUPDATE()')
    # mysql.connection.commit()
    return render_template('RentStatus.html',rent_status=rent_status)

@app.route('/UpdatedRentStatus')
def UpdatedRentStatus() :
    rent_status=''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('CALL RENTUPDATE()')
    mysql.connection.commit()
    cursor.execute('SELECT FNAME, LNAME, T.ROOM_NO, RENT_PER_MONTH, DUE_DATE, R_STATUS, LATE_FEE FROM RENT AS R, APARTMENT AS A, RENT_STATUS AS RS, TENANT AS T WHERE R.RENT_ID = RS.RENT_ID AND T.T_ID = R.T_ID AND A.ROOM_NO = T.ROOM_NO')
    mysql.connection.commit()
    rent_status=cursor.fetchall()
    return render_template('RentStatus.html',rent_status=rent_status)

@app.route('/Backup')
def Backup() :
    backup_status=''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT T_ID, FNAME, LNAME, GENDER, PH_NO, EMAIL, ROOM_NO FROM TENANT_BACKUP ')
    mysql.connection.commit()
    backup_status=cursor.fetchall()
    # cursor.execute('CALL RENTUPDATE()')
    # mysql.connection.commit()
    return render_template('backup.html',backup_status=backup_status)


#---------------------------------------------- TENANT DASHBOARD---------------------------------------------


@app.route('/TenantDashboard')
def TenantDashboard() :
    if 'loggedin' in session:
        return render_template('TenantDashboard.html')
    return render_template('TenantLogin.html')


@app.route('/list-property', methods=['POST','GET'])
def list_property():
    # 1. ADDED: Security check to ensure a tenant is logged in
    if 'loggedin' not in session:
        return redirect(url_for('TenantLogin'))

    msg2 = ''
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if request.method == 'POST' and 'room' in request.form and 'block' in request.form and 'status' in request.form and 'rentPerMonth' in request.form:
        #passing HTML form data into python variable
        Room = request.form['room']
        Block = request.form['block']
        Status = "Unoccupied" # Property is always Unoccupied when first listed
        Rent = request.form['rentPerMonth']
        aptTitle = request.form['apartmentTitle'] 
        description = request.form.get('desc')
        area = request.form['area']
        file1 = request.files['hall']
        file2 = request.files['kitchen']
        file3 = request.files['bedroom']
        file4 = request.files['extra']
        path = 'static/images/apartment'+Room
        isExist = os.path.exists(path)
        if not isExist:
            os.makedirs(path)
        file1.save(os.path.join('static/images/apartment'+Room, secure_filename(file1.filename)))
        file2.save(os.path.join('static/images/apartment'+Room, secure_filename(file2.filename)))
        file3.save(os.path.join('static/images/apartment'+Room, secure_filename(file3.filename)))
        file4.save(os.path.join('static/images/apartment'+Room, secure_filename(file4.filename)))
        
        cursor.execute('SELECT * FROM APARTMENT WHERE ROOM_NO = % s', (Room,))
        result = cursor.fetchone()
        if result:
            msg2 = 'Apartment with this Room No. already exists!'
        else:
            # 2. MODIFIED: The INSERT query now includes the logged-in tenant's ID
            cursor.execute('INSERT INTO APARTMENT (ROOM_NO, BLOCK_NO, RENT_PER_MONTH, APT_STATUS, listed_by_tenant_id) VALUES (%s, %s, %s, %s, %s)', (Room, Block, Rent, Status, session['id']))
            mysql.connection.commit()
            cursor.execute('INSERT INTO APARTMENT_DETAILS VALUES (%s, %s, %s, %s)', (Room, aptTitle, area, description))
            mysql.connection.commit()
            Image_url = 'images/apartment'+Room
            cursor.execute('INSERT INTO APARTMENT_PHOTOS VALUES (%s, %s, %s, %s, %s, %s)', (Room, Image_url, file1.filename, file2.filename, file3.filename, file4.filename))
            mysql.connection.commit()
            msg2 = 'You have successfully listed your property!'
            # Redirect to dashboard after successful listing
            return redirect(url_for('TenantDashboard'))
            
    elif request.method == 'POST':
        msg2 = 'Please fill out the form!'
        
    # 3. CHANGED: This now renders the new tenant-facing template
    return render_template('list_property.html', msg2=msg2)

@app.route('/RentApartment')
def rentApartment():
    if 'loggedin' not in session:
        return redirect(url_for('TenantLogin'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get the search query from the URL's arguments, if it exists
    search_query = request.args.get('search_query', '')

    # --- THIS IS THE NEW LOGIC ---
    if search_query:
        # If there is a search query, use a more complex SQL query
        query = """
            SELECT AD.APT_TITLE, A.ROOM_NO, AD.AREA, A.RENT_PER_MONTH, AD.APARTMENT_DESC 
            FROM APARTMENT AS A 
            JOIN APARTMENT_DETAILS AS AD ON A.ROOM_NO = AD.ROOM_NO 
            JOIN APARTMENT_BLOCK AS AB ON A.BLOCK_NO = AB.BLOCK_NO
            WHERE A.APT_STATUS = 'Unoccupied' AND (
                AD.APT_TITLE LIKE %s OR 
                AD.APARTMENT_DESC LIKE %s OR
                AB.LOCATION LIKE %s
            )
        """
        search_term = f"%{search_query}%"
        cursor.execute(query, (search_term, search_term, search_term))
    else:
        # If there is no search query, run the original simple query
        query = """
            SELECT AD.APT_TITLE, A.ROOM_NO, AD.AREA, A.RENT_PER_MONTH, AD.APARTMENT_DESC 
            FROM APARTMENT AS A 
            JOIN APARTMENT_DETAILS AS AD ON A.ROOM_NO = AD.ROOM_NO 
            WHERE A.APT_STATUS = 'Unoccupied'
        """
        cursor.execute(query)

    apartments = cursor.fetchall()
    
    cursor.execute('SELECT * FROM APARTMENT_PHOTOS')
    img_url = cursor.fetchall()
    
    return render_template('RentApartment.html', apartment=apartments, img_url=img_url, search_query=search_query)

@app.route('/Details', methods=['GET','POST'])
def Details() :
    Error=''
    Date = date.today()

    if request.method == 'POST' and 'Username' in request.form and 'aptNo' in request.form and 'TFatherName' in request.form and 'PerAddr' in request.form :
        Uname = request.form['Username']
        aptNo = request.form['aptNo']
        TFatherName = request.form['TFatherName']
        PAddress = request.form['PerAddr']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT T_ID, FNAME, LNAME FROM TENANT WHERE EMAIL = %s', (Uname,))
        tenant_info = cursor.fetchone()
        
        cursor.execute('SELECT RENT_PER_MONTH FROM APARTMENT WHERE ROOM_NO = %s AND TRIM(APT_STATUS) = "Unoccupied"', (aptNo,))
        apt_info = cursor.fetchone()
        
        if tenant_info and apt_info:
            t_id = tenant_info['T_ID']
            Tname = tenant_info['FNAME'] + ' ' + tenant_info['LNAME']
            rentAmt = apt_info['RENT_PER_MONTH']
            Deposit = rentAmt * 2
            
            # This line includes the fix for the BuildError
            
        else:
            Error = 'Invalid Username or Apartment No.!!'
           # The date is now formatted as a string BEFORE being passed to the URL
        return redirect(url_for('Contract', aptNo=aptNo, Tname=Tname, TFatherName=TFatherName, Uname=Uname, PAddress=PAddress, Date=Date.strftime('%Y-%m-%d'), rentAmt=rentAmt, Deposit=Deposit))
    elif request.method == 'POST' :
        Error= 'Please fill out the form!'
        
    return render_template('Details.html', Error=Error)

@app.route('/alreadyTenant', methods=['GET','POST'])
def alreadyTenant() :
    Error=''
    Uname=''
    Tname=''
    aptNo=''
    rentAmt= 0
    PhNo=''
    late_fee=0
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #applying empty validation
    if request.method == 'POST' and 'Username' in request.form and 'aptNo' in request.form :
        Uname = request.form['Username']
        aptNo = request.form['aptNo']
        cursor.execute('SELECT T_ID, PH_NO FROM TENANT WHERE EMAIL = % s',(Uname,))
        mysql.connection.commit()
        tid_list1 = cursor.fetchone()
        t_id = tid_list1['T_ID']
        PhNo = tid_list1['PH_NO']
        cursor.execute('SELECT LATE_FEE FROM RENT WHERE T_ID = % s',(t_id,))
        mysql.connection.commit()
        latefee_list = cursor.fetchone()
        late_fee = latefee_list['LATE_FEE']
        totAmt = int(rentAmt) + int(late_fee)
        # PhNo='9876543212'
        cursor.execute('SELECT RENT_PER_MONTH FROM APARTMENT WHERE ROOM_NO = %s AND APT_STATUS = "Occupied"',(aptNo,))
        mysql.connection.commit()
        res1 = cursor.fetchone()
        if t_id != None and res1 != None :
            cursor.execute('SELECT FNAME,LNAME FROM TENANT WHERE T_ID = %s',(t_id,))
            mysql.connection.commit()
            res = cursor.fetchone()
            Tname = res['FNAME']+' '+res['LNAME']
            rentAmt=res1['RENT_PER_MONTH']
            late_fee = late_fee
            totAmt = int(rentAmt) + int(late_fee)
            return redirect(url_for('Payment1', aptNo=aptNo ,Tname=Tname, Uname=Uname,PhNo=PhNo , rentAmt=rentAmt, late_fee=late_fee, totAmt=totAmt))
        else :
            Error = 'Invalid Username or Apartment No.!!'
    elif request.method == 'POST' :
        Error= 'Please fill out the form!'
    return render_template('alreadyTenant.html', Error=Error)


@app.route('/Contract/<aptNo>/<Tname>/<TFatherName>/<Uname>/<PAddress>/<Date>/<rentAmt>/<Deposit>', methods=['GET','POST'])
def Contract(aptNo, Tname, TFatherName, Uname, PAddress, Date, rentAmt, Deposit) :
    
    # This part handles the form submission
    if request.method == 'POST':
        # The form validation now only checks for fields from the new form
        if 'end_date' in request.form and 'terms' in request.form:
            end_date = request.form['end_date']
            
            # Get the hidden values from the form
            Username = request.form['UserName']
            Apt_no = request.form['aptno']
            start_date = request.form['start_date']
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Find the tenant
            cursor.execute('SELECT T_ID, PH_NO FROM TENANT WHERE EMAIL = %s', (Username,))
            tenant_info = cursor.fetchone()
            
            if not tenant_info:
                flash("Error: Tenant not found.", "danger")
                return redirect(url_for('Details'))

            T_id = tenant_info['T_ID']
            PhNo = tenant_info['PH_NO']
            
            # --- This is the fix for the date error ---
            # Convert the start_date string from the form back into a date object
            resDate = datetime.strptime(start_date, '%Y-%m-%d')
            due_date = resDate + relativedelta(months=+2)
            
            late_fee = 0
            
            # Execute all database changes
            cursor.execute('INSERT INTO CONTRACT (T_ID, ROOM_NO, START_DATE, END_DATE, DEPOSIT, TERMS) VALUES (%s, %s, %s, %s, %s, %s)', (T_id, Apt_no, start_date, end_date, Deposit, "Accepted"))
            cursor.execute('INSERT INTO RENT (RENT_FEE, T_ID, DUE_DATE, LATE_FEE) VALUES (%s, %s, %s, %s)', (rentAmt, T_id, due_date, late_fee))
            
            rent_id = cursor.lastrowid
            
            cursor.execute('INSERT INTO RENT_STATUS (RENT_ID, R_STATUS) VALUES (%s, %s)', (rent_id, 'Unpaid'))
            cursor.execute('UPDATE TENANT SET ROOM_NO = %s WHERE T_ID = %s', (Apt_no, T_id))
            cursor.execute('UPDATE APARTMENT SET APT_STATUS = "Occupied" WHERE ROOM_NO = %s', (Apt_no,))
            
            mysql.connection.commit()
            
            flash('Contract successfully created! Please proceed with the payment.', 'success')
            
            totAmt = int(rentAmt) + int(late_fee)
            return redirect(url_for('Payment', aptNo=Apt_no, Tname=Tname, PhNo=PhNo, Uname=Uname, rentAmt=rentAmt, late_fee=late_fee, totAmt=totAmt))
        
        else:
            flash("Please accept the terms to continue.", "danger")
    
    # This part displays the page initially
    # --- This is the other half of the fix ---
    # Convert the Date string from the URL back to a date object before sending to the template
    display_date = datetime.strptime(Date, '%Y-%m-%d').date()
    
    return render_template('contract.html', aptNo=aptNo, Date=display_date, Tname=Tname, TFatherName=TFatherName, Uname=Uname, PAddress=PAddress, rentAmt=rentAmt, Deposit=Deposit)
@app.route('/Payment/<aptNo>/<Tname>/<PhNo>/<Uname>/<rentAmt>/<late_fee>/<totAmt>', methods=['GET','POST'])
def Payment(aptNo,Tname,PhNo, Uname, rentAmt, late_fee, totAmt) :
    err=''
    Date = date.today()
    id = uuid.uuid1()
    fields = id.fields
    pay_id = fields[0]
    pay_date = date.today()
    #creating variable for connection
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #applying empty validation
    if request.method == 'POST' and 'email' in request.form and 'roomNo' in request.form and 'acc-no' in request.form and 'cardNo' in request.form and 'cvv' in request.form :
        Uname = request.form['email']
        aptNo = request.form['roomNo']
        Acc_No = request.form['acc-no']
        card_No = request.form['cardNo']
        cvv = request.form['cvv']
        if len(card_No) != 11 and len(cvv) != 3:
            err = 'Invalid Card No or cvv!!'
            return render_template('Payment.html',err=err, aptNo=aptNo ,Tname=Tname, PhNo=PhNo, Uname=Uname, rentAmt=rentAmt, late_fee=late_fee, totAmt=totAmt)
        cursor.execute('SELECT T_ID FROM TENANT WHERE EMAIL= % s',(Uname,))
        mysql.connection.commit()
        tid_list1 = cursor.fetchone()
        t_id = tid_list1['T_ID']
        cursor.execute('SELECT RENT_ID FROM RENT WHERE T_ID= % s',(t_id,))
        mysql.connection.commit()
        rentid_list = cursor.fetchone()
        rent_id = rentid_list['RENT_ID']
        if t_id != None and aptNo != None :
            cursor.execute('INSERT INTO PAYMENT VALUES(% s, % s, % s, % s, % s)',(pay_id,Acc_No,t_id,Date,rentAmt))
            cursor.execute('UPDATE RENT SET PAYMENT_ID = % s WHERE RENT_ID = % s',(pay_id, rent_id))
            cursor.execute('UPDATE RENT_STATUS SET R_STATUS = "Paid" WHERE RENT_ID = % s',(rent_id,))
            mysql.connection.commit()
            pay_amt = rentAmt
            return redirect(url_for('Receipt',Tname=Tname, pay_id=pay_id, pay_date=pay_date ,pay_amt=pay_amt))
    elif request.method == 'POST' :
        err= 'Please fill out the form!'
    return render_template('Payment.html',err=err, aptNo=aptNo ,Tname=Tname, PhNo=PhNo, Uname=Uname, rentAmt=rentAmt, late_fee=late_fee, totAmt=totAmt)


@app.route('/Payment1/<aptNo>/<Tname>/<PhNo>/<Uname>/<rentAmt>/<late_fee>/<totAmt>', methods=['GET','POST'])
def Payment1(aptNo,Tname,PhNo, Uname, rentAmt, late_fee, totAmt) :
    err='Payment Unsuccessfull'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST' and 'email' in request.form and 'roomNo' in request.form and 'acc-no' in request.form :
        Uname = request.form['email']
        aptNo = request.form['roomNo']
        pay_date = request.form['pay_date']
        Acc_No = request.form['acc-no']
        id = uuid.uuid1()
        fields = id.fields
        pay_id = fields[0]
        Date = date.today()
        cursor.execute('SELECT T_ID FROM TENANT WHERE EMAIL= % s',(Uname,))
        mysql.connection.commit()
        tid_list1 = cursor.fetchone()
        t_id = tid_list1['T_ID']
        cursor.execute('SELECT RENT_ID FROM RENT WHERE T_ID= % s',(t_id,))
        mysql.connection.commit()
        rentid_list = cursor.fetchone()
        rent_id = rentid_list['RENT_ID']
        if t_id != None and aptNo != None :
            cursor.execute('INSERT INTO PAYMENT VALUES(% s, % s, % s, % s, % s)',(pay_id,Acc_No,t_id,Date,rentAmt))
            cursor.execute('UPDATE RENT SET PAYMENT_ID = % s WHERE RENT_ID = % s',(pay_id, rent_id))
            cursor.execute('UPDATE RENT_STATUS SET R_STATUS = "Paid" WHERE RENT_ID = % s',(rent_id,))
            mysql.connection.commit()
            pay_amt = rentAmt
            return redirect(url_for('Receipt',Tname=Tname, pay_id=pay_id, pay_date=pay_date ,pay_amt=pay_amt))
    return render_template('Payment.html', err=err,aptNo=aptNo ,Tname=Tname, PhNo=PhNo, Uname=Uname, rentAmt=rentAmt, late_fee=late_fee, totAmt=totAmt)

 
 
@app.route('/Receipt/<Tname>/<pay_id>/<pay_date>/<pay_amt>', methods=['GET','POST'])
def Receipt(Tname,pay_id,pay_date,pay_amt) :
    return render_template('Reciept.html', Tname=Tname, pay_id=pay_id, pay_date=pay_date ,pay_amt=pay_amt)


if __name__ == '__main__':
    app.run(port=5000,debug=True)

@app.route('/ApartmentRooms', methods=['POST','GET'])
def ApartmentRooms():
    # 1. Security First: Ensure only a logged-in admin can access this page.
    if 'admin_loggedin' not in session:
        return redirect(url_for('AdminLogin'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 2. Handle POST Request (This runs when you submit the "Add Apartment" form)
    if request.method == 'POST' and 'room' in request.form:
        # Get all the data from the form
        Room = request.form['room']
        Block = request.form['block']
        Status = request.form['status']
        Rent = request.form['rentPerMonth']
        aptTitle = request.form['apartmentTitle'] 
        description = request.form.get('desc')
        area = request.form['area']
        
        # Check if an apartment with this room number already exists
        cursor.execute('SELECT * FROM APARTMENT WHERE ROOM_NO = %s', (Room,))
        existing_apartment = cursor.fetchone()

        if existing_apartment:
            flash(f"Error: Apartment with Room No. {Room} already exists!", "danger")
        else:
            # Handle the file uploads
            file1 = request.files['hall']
            file2 = request.files['kitchen']
            file3 = request.files['bedroom']
            file4 = request.files['extra']

            # Create a dedicated folder for the apartment's images
            path = os.path.join('static', 'images', 'apartment' + Room)
            if not os.path.exists(path):
                os.makedirs(path)
            
            # Save the files securely
            file1.save(os.path.join(path, secure_filename(file1.filename)))
            file2.save(os.path.join(path, secure_filename(file2.filename)))
            file3.save(os.path.join(path, secure_filename(file3.filename)))
            if file4 and file4.filename != '':
                file4.save(os.path.join(path, secure_filename(file4.filename)))

            # Insert the new apartment data into the database
            cursor.execute('INSERT INTO APARTMENT (ROOM_NO, BLOCK_NO, RENT_PER_MONTH, APT_STATUS) VALUES (%s, %s, %s, %s)', (Room, Block, Rent, Status))
            cursor.execute('INSERT INTO APARTMENT_DETAILS (ROOM_NO, APT_TITLE, AREA, APARTMENT_DESC) VALUES (%s, %s, %s, %s)', (Room, aptTitle, area, description))
            
            Image_url = 'images/apartment' + Room
            photo4_filename = secure_filename(file4.filename) if file4 else None
            cursor.execute('INSERT INTO APARTMENT_PHOTOS (ROOM_NO, PATHNAME, PHOTO1, PHOTO2, PHOTO3, PHOTO4) VALUES (%s, %s, %s, %s, %s, %s)', 
                           (Room, Image_url, secure_filename(file1.filename), secure_filename(file2.filename), secure_filename(file3.filename), photo4_filename))
            
            mysql.connection.commit()
            flash(f"Apartment {Room} has been successfully added!", "success")
        
        return redirect(url_for('ApartmentRooms'))

    # 3. Handle GET Request (This runs when you first visit the page)
    # Fetch all existing apartments to display in a table
    cursor.execute('SELECT A.ROOM_NO, A.BLOCK_NO, A.RENT_PER_MONTH, A.APT_STATUS, AD.APT_TITLE FROM APARTMENT A JOIN APARTMENT_DETAILS AD ON A.ROOM_NO = AD.ROOM_NO')
    apartments = cursor.fetchall()
    
    # 4. Render the Template
    # Send the list of apartments to the HTML page
    return render_template('ApartmentRoomsadmin.html', apartments=apartments)
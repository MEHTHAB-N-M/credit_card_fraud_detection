from flask import Flask, render_template, request, url_for, session, redirect
import csv
from flask_socketio import SocketIO

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTEBOOKS_DIR = os.path.join(BASE_DIR, "notebooks")
if NOTEBOOKS_DIR not in sys.path:
    sys.path.append(NOTEBOOKS_DIR)

from model import predict_transaction


app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = 'C16'


# Home page route
@app.route('/')
def home():
    return render_template('home.html')


# About page route
@app.route('/about')
def about():
    if 'loggedin' in session:
        return render_template('about.html')
    return redirect(url_for('home'))


# Overview page route
@app.route('/overview')
def overview():
    if 'loggedin' in session:
        return render_template('overview.html')
    return redirect(url_for('home'))


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    # GET: just render the detection form
    if request.method == 'GET':
        if 'loggedin' in session:
            return render_template('detection.html')  # detection.html contains the new form
        return redirect(url_for('home'))

    # POST: read form, build record, call model
    # All fields should match the names in your updated detection.html form
    record = {
        "Unnamed: 0": 0,  # dummy index, will be dropped in preprocessing
        "trans_date_trans_time": request.form.get("trans_date_trans_time", ""),
        "cc_num": float(request.form["cc_num"]),
        "merchant": request.form["merchant"],
        "category": request.form["category"],
        "amt": float(request.form["amt"]),
        "first": request.form["first"],
        "last": request.form["last"],
        "gender": request.form["gender"],
        "street": request.form["street"],
        "city": request.form["city"],
        "state": request.form["state"],
        "zip": int(request.form["zip"]),
        "lat": float(request.form["lat"]),
        "long": float(request.form["long"]),
        "city_pop": int(request.form["city_pop"]),
        "job": request.form["job"],
        "dob": request.form["dob"],
        "trans_num": request.form["trans_num"],
        "unix_time": int(request.form["unixtime"]),
        "merch_lat": float(request.form["merch_lat"]),
        "merch_long": float(request.form["merch_long"]),
    }

    result = predict_transaction(record)  # {'prob_fraud': float, 'is_fraud': int}
    return render_template('result.html', result=result)


# Result page route (optional old style)
@app.route('/result/<prediction>')
def result(prediction):
    # Keep for backward compatibility, but you can remove if not used
    return render_template('result.html', result={"is_fraud": int(prediction)})


# Contact page route
@app.route('/contact')
def contact():
    if 'loggedin' in session:
        return render_template('contact.html')
    return redirect(url_for('home'))


# Signup page route
@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirmpassword = request.form['confirmpassword']

        if password != confirmpassword:
            return "Passwords do not match. Please try again."

        # Save user data to CSV
        with open('users.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([fullname, email, username, password])

        return redirect(url_for('home'))
    return render_template('signup.html')


# Login page route with simple validation
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Validate login with CSV file
    try:
        with open('users.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 4 and row[2] == username and row[3] == password:
                    session['loggedin'] = True
                    return redirect(url_for('overview'))
    except FileNotFoundError:
        pass

    return render_template('home.html', error='Invalid username or password.')


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    socketio.run(app, debug=True)

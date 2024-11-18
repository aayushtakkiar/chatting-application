from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify, make_response
import base64
import hashlib
import json
import os
import pika
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

CREDENTIALS_FILE = 'user_credentials.json'
GROUPS_FILE = 'groups.json'
PROFILE_IMAGES_FOLDER = 'static/profile_images'
RABBITMQ_HOST = 'localhost'

# Function to load user credentials from a file
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Function to save user credentials to a file
def save_credentials(credentials):
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f)

# Function to load groups from a file
def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, 'r') as f:
            return json.load(f)
    return []

# Function to save groups to a file
def save_groups(groups):
    with open(GROUPS_FILE, 'w') as f:
        json.dump(groups, f)

user_credentials = load_credentials()
groups = load_groups()

# Function to create a RabbitMQ exchange for a group
def create_rabbitmq_exchange(group_name):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange=group_name, exchange_type='fanout')
    connection.close()

# Function to delete a RabbitMQ exchange for a group
def delete_rabbitmq_exchange(group_name):
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_delete(exchange=group_name)
    connection.close()

if not os.path.exists(PROFILE_IMAGES_FOLDER):
    os.makedirs(PROFILE_IMAGES_FOLDER)

# HTML Templates
welcome_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Chat App</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            background-color: #f5f5f5;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
        }

        .container {
            text-align: center;
            z-index: 1;
            position: relative;
        }

        .logo img {
            width: 200px;
            height: 200px;
            margin-bottom: 30px;
        }

        .greeting {
            font-size: 24px;
            font-weight: bold;
            color: #4b2354;
            margin-bottom: 10px;
        }

        .description {
            font-size: 14px;
            color: #4b2354;
            margin-bottom: 20px;
        }

        .welcome-button {
            padding: 10px 30px;
            font-size: 16px;
            font-weight: bold;
            color: #4b2354;
            background-color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: background-color 0.3s;
        }

        .welcome-button:hover {
            background-color: #e0e0e0;
        }

        .curved-background {
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 250px;
            background-color: #c0f8ee;
            border-radius: 50% 50% 0 0;
            z-index: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="data:image/png;base64,{{ logo_image }}" alt="Logo">
        </div>
        <div class="greeting">Hello, Let's Chat</div>
        <div class="description">What's on your mind?<br>Chat Anywhere, Anytime</div>
        <button class="welcome-button" onclick="location.href='/signin'">WELCOME</button>
    </div>
    <div class="curved-background"></div>
</body>
</html>
"""

signin_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            background: linear-gradient(to bottom right, #e0f7fa, #e0f7fa);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .signin-container {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 40px;
            text-align: center;
            width: 300px;
        }

        .signin-container h2 {
            color: #4b2354;
            margin-bottom: 20px;
            font-size: 24px;
        }

        .form-group {
            margin-bottom: 20px;
            position: relative;
        }

        .form-group input {
            width: 100%;
            padding: 10px;
            border: 2px solid #4b2354;
            border-radius: 5px;
            outline: none;
            font-size: 14px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }

        .form-group input:focus {
            border-color: #00695c;
        }

        .form-group label {
            position: absolute;
            top: -20px;
            left: 10px;
            font-size: 12px;
            color: #4b2354;
            background-color: white;
            padding: 0 5px;
        }

        .signin-button {
            width: 100%;
            padding: 10px;
            background-color: #00695c;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .signin-button:hover {
            background-color: #004d40;
        }

        .signup-link {
            margin-top: 20px;
            font-size: 14px;
            color: #4b2354;
            text-decoration: none;
            display: block;
        }

        .signup-link:hover {
            text-decoration: underline;
        }

        .curved-background {
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 150px;
            background-color: #c0f8ee;
            border-radius: 50% 50% 0 0;
            z-index: -1;
        }

        .flash-message {
            color: red;
            font-size: 14px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="signin-container">
        <h2>Sign In</h2>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-message">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <form method="post" action="/signin">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="signin-button">Sign In</button>
        </form>
        <a href="/signup" class="signup-link">Not currently signed up? Sign up first</a>
    </div>
    <div class="curved-background"></div>
</body>
</html>
"""

signup_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            background: linear-gradient(to bottom right, #e0f7fa, #e0f7fa);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .signup-container {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 40px;
            text-align: center;
            width: 300px;
        }

        .signup-container h2 {
            color: #4b2354;
            margin-bottom: 20px;
            font-size: 24px;
        }

        .form-group {
            margin-bottom: 20px;
            position: relative;
        }

        .form-group input {
            width: 100%;
            padding: 10px;
            border: 2px solid #4b2354;
            border-radius: 5px;
            outline: none;
            font-size: 14px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }

        .form-group input:focus {
            border-color: #00695c;
        }

        .form-group label {
            position: absolute;
            top: -20px;
            left: 10px;
            font-size: 12px;
            color: #4b2354;
            background-color: white;
            padding: 0 5px;
        }

        .signup-button {
            width: 100%;
            padding: 10px;
            background-color: #00695c;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .signup-button:hover {
            background-color: #004d40;
        }

        .signup-link {
            margin-top: 20px;
            font-size: 14px;
            color: #4b2354;
            text-decoration: none;
            display: block;
        }

        .signup-link:hover {
            text-decoration: underline;
        }

        .curved-background {
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 150px;
            background-color: #c0f8ee;
            border-radius: 50% 50% 0 0;
            z-index: -1;
        }

        .flash-message {
            color: red;
            font-size: 14px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="signup-container">
        <h2>Sign Up</h2>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash-message">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <form method="post" action="/signup">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <div class="form-group">
                <label for="retype_password">Retype Password</label>
                <input type="password" id="retype_password" name="retype_password" placeholder="Retype your password" required>
            </div>
            <button type="submit" class="signup-button">Sign Up</button>
        </form>
        <a href="/signin" class="signup-link">Already signed up? Go to Sign In</a>
    </div>
    <div class="curved-background"></div>
</body>
</html>
"""

groups_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Available Groups</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            background: linear-gradient(to bottom right, #e0f7fa, #e0f7fa);
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: start;
            padding-top: 50px;
        }

        .group-container {
            width: 90%;
            max-width: 400px;
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 20px;
            text-align: center;
        }

        .group-container h2 {
            color: #4b2354;
            margin-bottom: 20px;
            font-size: 24px;
        }

        .group-list {
            list-style: none;
            padding: 0;
        }

        .group-list li {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
            background-color: #f5f5f5;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: background-color 0.3s;
            cursor: pointer;
        }

        .group-list li:hover {
            background-color: #e0e0e0;
        }

        .create-group-button {
            width: 100%;
            padding: 10px;
            background-color: #00695c;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .create-group-button:hover {
            background-color: #004d40;
        }

        .curved-background {
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 150px;
            background-color: #c0f8ee;
            border-radius: 50% 50% 0 0;
            z-index: -1;
        }

        .select-button {
            width: 100%;
            padding: 10px;
            background-color: #00695c;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .select-button:hover {
            background-color: #004d40;
        }

        .delete-button {
            background-color: #ff1744;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .delete-button:hover {
            background-color: #d50000;
        }

        .profile-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            margin-bottom: 20px;
        }

        .profile-avatar img {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
        }

        .no-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background-color: #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            cursor: pointer;
        }

        .view-profile-button {
            background-color: #4b2354;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }

        .view-profile-button:hover {
            background-color: #2e0833;
        }
    </style>
    <script>
        function selectGroup(groupName) {
            fetch('/select_group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ group_name: groupName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.location.href = '/chat/' + groupName;
                } else {
                    alert('Error selecting group');
                }
            })
            .catch(error => console.error('Error:', error));
        }

        function deleteGroup(groupName) {
            fetch('/delete_group', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ group_name: groupName })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    location.reload();
                } else {
                    alert('Error deleting group');
                }
            })
            .catch(error => console.error('Error:', error));
        }
    </script>
</head>
<body>
    <div class="group-container">
        <div class="profile-section">
            <div class="profile-avatar">
                {% if profile_image %}
                    <img src="{{ profile_image }}" alt="Profile Avatar" onclick="document.getElementById('profile-image-upload').click();">
                {% else %}
                    <div class="no-avatar" onclick="document.getElementById('profile-image-upload').click();">No Image</div>
                {% endif %}
            </div>
            <form id="profile-form" action="/upload_profile_image" method="post" enctype="multipart/form-data" style="display: none;">
                <input type="file" id="profile-image-upload" name="profile_image" onchange="document.getElementById('profile-form').submit();">
            </form>
            <button class="view-profile-button" onclick="location.href='/profile'">View Profile</button>
        </div>
        <h2>Available Groups to Join!</h2>
        <ul class="group-list">
            {% for group in groups %}
            <li>
                <span onclick="selectGroup('{{ group.name }}')">{{ group.name }}</span>
                <button class="delete-button" onclick="deleteGroup('{{ group.name }}')">Delete</button>
            </li>
            {% endfor %}
        </ul>
        <form method="post" action="/available_groups">
            <input type="text" name="group_name" placeholder="Enter new group name" required>
            <button type="submit" class="create-group-button">Create Group</button>
        </form>
    </div>
    <div class="curved-background"></div>
</body>
</html>
"""

profile_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Profile</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            background: linear-gradient(to bottom right, #e0f7fa, #e0f7fa);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .profile-container {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 40px;
            text-align: center;
            width: 300px;
        }

        .profile-avatar img {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin-bottom: 20px;
        }

        .no-avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background-color: #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin-bottom: 20px;
        }

        .profile-info {
            font-size: 18px;
            color: #4b2354;
            margin-bottom: 20px;
        }

        .back-button {
            width: 100%;
            padding: 10px;
            background-color: #00695c;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .back-button:hover {
            background-color: #004d40;
        }

        .delete-profile-button {
            width: 100%;
            padding: 10px;
            background-color: #ff1744;
            color: white;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
            margin-top: 10px;
        }

        .delete-profile-button:hover {
            background-color: #d50000;
        }
    </style>
</head>
<body>
    <div class="profile-container">
        <div class="profile-avatar">
            {% if profile_image %}
                <img src="{{ profile_image }}" alt="Profile Avatar">
            {% else %}
                <div class="no-avatar">No Image</div>
            {% endif %}
        </div>
        <div class="profile-info">Username: {{ username }}</div>
        <button class="back-button" onclick="location.href='/available_groups'">Back to Groups</button>
        <button class="delete-profile-button" onclick="location.href='/delete_profile'">Delete Profile</button>
    </div>
</body>
</html>
"""

chat_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ group_name }} Chat Room</title>
    <style>
        body {
            margin: 0;
            font-family: 'Helvetica', sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: #e0f7fa;
        }

        .chat-container {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            margin: 0 20px;
            border-radius: 10px;
            overflow: hidden;
        }

        .messages {
            flex-grow: 1;
            padding: 20px;
            overflow-y: scroll;
            border: 1px solid #ccc;
            border-radius: 10px 10px 0 0;
            background-color: #fff;
        }

        .messages p {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
            background-color: #f1f1f1;
            word-wrap: break-word;
        }

        .username {
            font-weight: bold;
            margin-bottom: 5px;
        }

        .chat-input {
            display: flex;
            border-radius: 0 0 10px 10px;
            border: 1px solid #ccc;
        }

        .chat-input input {
            flex-grow: 1;
            padding: 10px;
            border: none;
            border-radius: 0 0 0 10px;
            outline: none;
        }

        .chat-input button {
            padding: 10px 20px;
            background-color: #00695c;
            color: white;
            border: none;
            border-radius: 0 0 10px 0;
            cursor: pointer;
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', (event) => {
            var socket = io.connect('http://' + document.domain + ':' + location.port);
            var groupName = "{{ group_name }}";
            var username = "{{ username }}";

            socket.emit('join', {'room': groupName, 'username': username});

            socket.on('message', function(data) {
                var messages = document.getElementById('messages');
                var message = document.createElement('p');
                var user = document.createElement('span');
                user.className = 'username';
                user.textContent = data.username + ': ';
                message.appendChild(user);
                message.appendChild(document.createTextNode(data.message));
                messages.appendChild(message);
                messages.scrollTop = messages.scrollHeight;
            });

            document.getElementById('send').onclick = function() {
                var text = document.getElementById('message').value;
                socket.emit('text', {'message': text, 'room': groupName, 'username': username});
                document.getElementById('message').value = '';
            };
        });
    </script>
</head>
<body>
    <div class="chat-container">
        <div id="messages" class="messages"></div>
        <div class="chat-input">
            <input type="text" id="message" placeholder="Type a message..." />
            <button id="send">Send</button>
        </div>
    </div>
</body>
</html>
"""

def get_base64_image():
    # Base64 encoding of your image
    with open("images 1.png", "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

@app.route('/')
def index():
    return render_template_string(welcome_template, logo_image=get_base64_image())

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if username in user_credentials and user_credentials[username] == hashed_password:
            response = redirect(url_for('available_groups'))
            response.set_cookie('username', username)
            return response
        else:
            flash('Invalid credentials. Please sign up or check your username/password.', 'error')
            return redirect(url_for('signin'))

    return render_template_string(signin_template)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        retype_password = request.form['retype_password']

        if password != retype_password:
            flash('Passwords do not match. Please try again.', 'error')
            return redirect(url_for('signup'))

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user_credentials[username] = hashed_password
        save_credentials(user_credentials)
        flash('Signed up successfully! Please sign in.', 'info')
        return redirect(url_for('signin'))

    return render_template_string(signup_template)

@app.route('/available_groups', methods=['GET', 'POST'])
def available_groups():
    username = request.cookies.get('username', 'Guest')
    profile_image_path = os.path.join(PROFILE_IMAGES_FOLDER, f'{username}.png')
    profile_image = url_for('static', filename=f'profile_images/{username}.png') if os.path.exists(profile_image_path) else None

    if request.method == 'POST':
        group_name = request.form['group_name']
        groups.append({'name': group_name})
        save_groups(groups)
        create_rabbitmq_exchange(group_name)
        return redirect(url_for('available_groups'))

    return render_template_string(groups_template, groups=groups, profile_image=profile_image)

@app.route('/upload_profile_image', methods=['POST'])
def upload_profile_image():
    username = request.cookies.get('username', 'Guest')
    if 'profile_image' in request.files:
        profile_image = request.files['profile_image']
        if profile_image:
            filename = f'{username}.png'
            filepath = os.path.join(PROFILE_IMAGES_FOLDER, filename)
            profile_image.save(filepath)
    return redirect(url_for('available_groups'))

@app.route('/select_group', methods=['POST'])
def select_group():
    data = request.json
    group_name = data.get('group_name', None)
    if group_name and any(group['name'] == group_name for group in groups):
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

@app.route('/delete_group', methods=['POST'])
def delete_group():
    data = request.json
    group_name = data.get('group_name', None)
    if group_name and any(group['name'] == group_name for group in groups):
        groups[:] = [group for group in groups if group['name'] != group_name]
        save_groups(groups)
        delete_rabbitmq_exchange(group_name)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'})

@app.route('/delete_profile')
def delete_profile():
    username = request.cookies.get('username', 'Guest')
    if username in user_credentials:
        del user_credentials[username]
        save_credentials(user_credentials)
        profile_image_path = os.path.join(PROFILE_IMAGES_FOLDER, f'{username}.png')
        if os.path.exists(profile_image_path):
            os.remove(profile_image_path)
    response = make_response(redirect(url_for('signup')))
    response.delete_cookie('username')
    return response

@app.route('/proceed')
def proceed():
    return "<h1>Welcome to the selected group chat!</h1>"

@app.route('/profile')
def profile():
    username = request.cookies.get('username', 'Guest')
    profile_image_path = os.path.join(PROFILE_IMAGES_FOLDER, f'{username}.png')
    profile_image = url_for('static', filename=f'profile_images/{username}.png') if os.path.exists(profile_image_path) else None
    return render_template_string(profile_template, username=username, profile_image=profile_image)

@app.route('/chat/<group_name>')
def chat(group_name):
    username = request.cookies.get('username', 'Guest')
    return render_template_string(chat_template, group_name=group_name, username=username)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('message', {'username': 'System', 'message': f'{username} has joined the room.'}, room=room)

@socketio.on('text')
def on_text(data):
    message = data['message']
    room = data['room']
    username = data['username']
    
    # Send the message to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    channel.basic_publish(exchange=room, routing_key='', body=f'{username}: {message}')
    connection.close()
    
    emit('message', {'username': username, 'message': message}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
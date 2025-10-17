# ✅ MUST BE FIRST
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import MySQLdb.cursors
import time
import gevent
import base64
import os

# ---- App Setup ----
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/*": {"origins": "*"}})

flask_app.config.update(
    MYSQL_HOST='127.0.0.1',
    MYSQL_PORT=3306,
    MYSQL_USER='launcher_user',
    MYSQL_PASSWORD='baboushka',
    MYSQL_DB='launcher_db'
)

mysql = MySQL(flask_app)
bcrypt = Bcrypt(flask_app)
socketio = SocketIO(flask_app, cors_allowed_origins="*", async_mode="gevent")

# ---- State ----
online_users = set()
sid_to_user = {}
user_to_sid = {}
messages = []
ROOM_NAME = "Europe DOTA 1 Room"
active_hosts = {}  # {username: {"address": "ip:port", "game_name": "Custom Game", "players": 8, "max_players": 10, "status": "Waiting", "map": "dota", "created_at": timestamp}}
user_profiles = {}  # {username: {"age": "", "nationality": "", "nation_code": None, "gender": "", "status": "Online", "role": "Basic Member", "avatar_b64"?}}
last_seen = {}  # username -> unix timestamp of last heartbeat/activity
GRACE_SECONDS = 12  # delay before declaring a user truly offline
kicked_users = {}  # username -> kicked_until (unix timestamp)
banned_ips = {}  # ip -> banned_until (unix timestamp, 0 = forever)

# ---- Chat Styling ----
SYSTEM_COLOR = "#ff3b30"  # red

# Monotonic message sequence to preserve ordering across clients
message_seq = 0

def _next_seq():
    global message_seq
    message_seq += 1
    return message_seq

def _get_role_for_user(username):
    profile = user_profiles.get(username) or {}
    return profile.get('role', 'Basic Member')

def _color_for_role(role):
    rl = str(role or '').lower()
    if rl == 'super admin':
        return "#1e5bb8"  # dark blue
    if rl == 'channel admin':
        return "#cc0000"  # red
    return None

def _make_system_message(text):
    return {
        "user": "SYSTEM",
        "msg": text,
        "type": "system",
        "color": SYSTEM_COLOR,
        "ts": time.time(),
        "seq": _next_seq(),
    }

def _make_user_message(username, text):
    role = _get_role_for_user(username)
    color = _color_for_role(role)
    payload = {"user": username, "msg": text, "type": "user", "ts": time.time(), "seq": _next_seq()}
    if role:
        payload["role"] = role
    if color:
        payload["color"] = color
    return payload

# ---- Lobbies ----
# lobbies: host_username -> {"max_players": int, "members": set([usernames]), "chat": [(user, msg, ts)]}
lobbies = {}

# ---- Optional: seed fake users for lobby presence ----
SEED_FAKE_USERS = []  # will be generated at startup
EXTRA_NAMED_FAKE_USERS = [
    {"username": "farid_elbaklawi", "age": "25", "nationality": "Jordan", "nation_code": "jo", "gender": "", "status": "Online", "avatar": "server_avatars/jo1.jpg"},
    {"username": "mohamedhaz", "age": "27", "nationality": "Egypt", "nation_code": "eg", "gender": "", "status": "Online", "avatar": "server_avatars/eg1.jpg"},
    {"username": "hassan", "age": "24", "nationality": "Morocco", "nation_code": "ma", "gender": "", "status": "Online", "avatar": "server_avatars/ma1.jpg"},
    {"username": "noura", "age": "22", "nationality": "Tunisia", "nation_code": "tn", "gender": "", "status": "Online", "avatar": "server_avatars/tn1.jpg"},
    {"username": "ahmed", "age": "26", "nationality": "Algeria", "nation_code": "dz", "gender": "", "status": "Online", "avatar": "server_avatars/dz1.jpg"},
    {"username": "youssef", "age": "23", "nationality": "Saudi Arabia", "nation_code": "sa", "gender": "", "status": "Online", "avatar": "server_avatars/sa1.jpg"},
    {"username": "salma", "age": "21", "nationality": "United Arab Emirates", "nation_code": "ae", "gender": "", "status": "Online", "avatar": "server_avatars/ae1.jpg"},
    {"username": "omar", "age": "28", "nationality": "Qatar", "nation_code": "qa", "gender": "", "status": "Online", "avatar": "server_avatars/qa1.jpg"},
    {"username": "fatima", "age": "20", "nationality": "Turkey", "nation_code": "tr", "gender": "", "status": "Online", "avatar": "server_avatars/tr1.jpg"},
    {"username": "khaled", "age": "29", "nationality": "Iraq", "nation_code": "iq", "gender": "", "status": "Online", "avatar": "server_avatars/iq1.jpg"},
]

def _file_to_b64(path):
    try:
        if not path:
            return None
        # Resolve relative to server file directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if not os.path.exists(abs_path):
            return None
        with open(abs_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('ascii')
    except Exception:
        return None

def seed_fake_users():
    # Generate ~50 diverse fake users with flags, ages, and optional avatars
    import random
    random.seed(42)
    countries = [
        ("United States", "us"), ("United Kingdom", "gb"), ("Germany", "de"), ("France", "fr"),
        ("Italy", "it"), ("Spain", "es"), ("Portugal", "pt"), ("Netherlands", "nl"),
        ("Sweden", "se"), ("Norway", "no"), ("Denmark", "dk"), ("Poland", "pl"),
        ("Russia", "ru"), ("Ukraine", "ua"), ("Finland", "fi"), ("Brazil", "br"),
        ("Argentina", "ar"), ("Canada", "ca"), ("Japan", "jp"), ("South Korea", "kr"),
        ("India", "in"), ("Australia", "au"), ("New Zealand", "nz"), ("China", "cn")
    ]
    first_names = [
        "steve","undertaker","edward","gretel","arthur","marie","sven","akira","priya","carlos",
        "mike","daniel","lena","sofia","yuri","ivan","olga","marco","anna","nina",
        "finn","erik","peter","john","lucas","mateo","diego","sara","emily","sam",
        "leo","max","noah","liam","oliver","elijah","taro","yuna","mina","wei",
        "arjun","raj","mia","ava","zoe","lily","victor","pavel","johan","tomas"
    ]
    now = time.time()
    generated = []
    for i in range(50):
        fname = first_names[i % len(first_names)]
        # ensure unique usernames
        uname = f"{fname}{100 + i}"
        country_name, code = random.choice(countries)
        age = str(random.randint(18, 35))
        # Try to map avatar file per code; allow multiple variations
        avatar_candidate = None
        for idx in (1, 2, 3):
            p = f"server_avatars/{code}{idx}.jpg"
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.exists(os.path.join(base_dir, p)):
                avatar_candidate = p
                break
        u = {
            "username": uname,
            "age": age,
            "nationality": country_name,
            "nation_code": code,
            "gender": "",
            "status": "Online",
            "avatar": avatar_candidate,
        }
        generated.append(u)
    # persist generated into the global list for reference and add extra named users (no numeric suffixes)
    SEED_FAKE_USERS.extend(generated)
    # ensure no duplicates when adding named users
    existing_names = set(u["username"] for u in SEED_FAKE_USERS)
    for u in EXTRA_NAMED_FAKE_USERS:
        if u["username"] not in existing_names:
            SEED_FAKE_USERS.append(u)
            existing_names.add(u["username"])

    # apply to presence structures
    for u in SEED_FAKE_USERS:
        name = u["username"]
        online_users.add(name)
        user_profiles[name] = {
            "age": u.get("age", ""),
            "nationality": u.get("nationality", ""),
            "nation_code": u.get("nation_code"),
            "gender": u.get("gender", ""),
            "status": "Online",
        }
        last_seen[name] = now
        avatar_b64 = _file_to_b64(u.get("avatar"))
        if avatar_b64:
            user_profiles[name]["avatar_b64"] = avatar_b64

def _simulate_fake_chat_loop():
    import random
    templates = [
        "hi",
        "hello",
        "how are u doing",
        "any game?",
        "anyone hosting?",
        "join europe pls",
        "brb",
        "gg",
        "ready",
        "start?",
    ]
    replies = [
        "fine",
        "good and u?",
        "yes",
        "no",
        "hosting soon",
        "coming",
        "ok",
        "let's go",
    ]
    while True:
        try:
            if not SEED_FAKE_USERS:
                gevent.sleep(60)
                continue
            # pick 1-3 random users to say something
            n = random.randint(1, 3)
            speakers = random.sample(SEED_FAKE_USERS, min(n, len(SEED_FAKE_USERS)))
            for u in speakers:
                msg = random.choice(templates)
                entry = _make_user_message(u["username"], msg)
                messages.append(entry)
                socketio.emit('new_message', entry)
                # 30% chance someone else replies shortly after
                if random.random() < 0.3 and len(SEED_FAKE_USERS) > 1:
                    gevent.sleep(random.uniform(0.5, 2.0))
                    v = random.choice([x for x in SEED_FAKE_USERS if x is not u])
                    r = random.choice(replies)
                    entry2 = _make_user_message(v["username"], r)
                    messages.append(entry2)
                    socketio.emit('new_message', entry2)
            # wait a few minutes before next batch
            gevent.sleep(random.randint(120, 300))
        except Exception:
            gevent.sleep(120)

def _set_user_online(username):
    try:
        if username in online_users:
            return
        online_users.add(username)
        if username in user_profiles:
            user_profiles[username]['status'] = 'Online'
            socketio.emit('profile_updated', {username: user_profiles[username]})
        last_seen[username] = time.time()
        socketio.emit('online_users', list(online_users))
        msg = _make_system_message(f'⭐ {username} has joined {ROOM_NAME}')
        messages.append(msg)
        socketio.emit('new_message', msg)
    except Exception:
        pass

def _set_user_offline(username):
    try:
        if username not in online_users:
            return
        online_users.discard(username)
        active_hosts.pop(username, None)
        if username in user_profiles:
            user_profiles[username]['status'] = 'Offline'
            socketio.emit('profile_updated', {username: user_profiles[username]})
        socketio.emit('online_users', list(online_users))
        socketio.emit('update_hosts', active_hosts)
        msg = _make_system_message(f'❌ {username} left {ROOM_NAME}')
        messages.append(msg)
        socketio.emit('new_message', msg)
    except Exception:
        pass

def _simulate_presence_loop():
    import random
    while True:
        try:
            # Wait 2-4 minutes between presence events
            gevent.sleep(random.randint(120, 240))

            population = [u['username'] for u in SEED_FAKE_USERS]
            if not population:
                continue

            event_type = random.choice(['join_small', 'leave_mid', 'join_big', 'chat_sequence'])

            if event_type == 'join_small':
                k = random.randint(2, 3)
                for name in random.sample(population, min(k, len(population))):
                    _set_user_online(name)

            elif event_type == 'join_big':
                k = 10
                picks = random.sample(population, min(k, len(population)))
                for name in picks:
                    _set_user_online(name)

            elif event_type == 'leave_mid':
                # leave up to 7 currently online users
                current = list(online_users)
                if current:
                    k = min(7, len(current))
                    for name in random.sample(current, k):
                        _set_user_offline(name)

            elif event_type == 'chat_sequence':
                # one user asks, then after ~2 minutes another user replies
                askers = [u for u in online_users] or [u['username'] for u in SEED_FAKE_USERS]
                if askers:
                    asker = random.choice(askers)
                    entry = _make_user_message(asker, "any game?")
                    messages.append(entry)
                    socketio.emit('new_message', entry)
                    # reply after ~2 minutes
                    def _reply_later():
                        try:
                            gevent.sleep(120)
                            responders = [u for u in online_users if u != asker] or [u['username'] for u in SEED_FAKE_USERS if u['username'] != asker]
                            if responders:
                                responder = random.choice(responders)
                                entry2 = _make_user_message(responder, "please someone host?")
                                messages.append(entry2)
                                socketio.emit('new_message', entry2)
                        except Exception:
                            pass
                    gevent.spawn(_reply_later)
        except Exception:
            gevent.sleep(120)


# ---- REST APIs ----
@flask_app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "ok",
        "online_users": len(online_users),
        "active_hosts": len(active_hosts)
    })


@flask_app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"status": "error", "msg": "Missing fields"}), 400

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        return jsonify({"status": "error", "msg": "User already exists"}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    cur.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
        (username, f"{username}@dummy.com", pw_hash)
    )
    mysql.connection.commit()
    return jsonify({"status": "success", "msg": "Registered successfully"})


@flask_app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    if user and bcrypt.check_password_hash(user['password_hash'], password):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "msg": "Invalid credentials"}), 401


# ---- Socket.IO Events ----
@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    if username:
        # Check if user is kicked
        until = kicked_users.get(username)
        if until and time.time() < until:
            emit('kicked', {
                'by': 'SYSTEM',
                'reason': 'You are temporarily kicked',
                'remaining_sec': int(max(0, until - time.time()))
            })
            return
        
        # Check if IP is banned (simplified - in real implementation you'd track actual IPs)
        client_ip = request.environ.get('REMOTE_ADDR', '127.0.0.1')
        ban_until = banned_ips.get(client_ip)
        if ban_until is not None:
            if ban_until == 0:  # Permanent ban
                emit('kicked', {
                    'by': 'SYSTEM',
                    'reason': 'Your IP address is permanently banned',
                    'remaining_sec': -1
                })
                return
            elif time.time() < ban_until:  # Temporary ban still active
                emit('kicked', {
                    'by': 'SYSTEM',
                    'reason': 'Your IP address is temporarily banned',
                    'remaining_sec': int(max(0, ban_until - time.time()))
                })
                return
        sid_to_user[request.sid] = username
        user_to_sid[username] = request.sid
        online_users.add(username)
        last_seen[username] = time.time()

        if username not in user_profiles:
            user_profiles[username] = {
                "age": "",
                "nationality": "",
                "nation_code": None,
                "gender": "",
                "status": "Online",
                "role": "Basic Member"
            }
        else:
            user_profiles[username]["status"] = "Online"

        socketio.emit('online_users', list(online_users))
        emit('recent_messages', messages)

        msg = _make_system_message(f'⭐ {username} has joined {ROOM_NAME}')
        messages.append(msg)
        socketio.emit('new_message', msg)
        socketio.emit('profile_updated', {username: user_profiles[username]})
        
        # broadcast welcome audio to all users when someone joins
        socketio.emit('play_audio', {'audio_file': 'welcome.mp3'})


@socketio.on('send_message')
def handle_message(data):
    username = data.get('username')
    msg = data.get('message')
    if username and msg:
        # block if kicked
        until = kicked_users.get(username)
        if until and time.time() < until:
            sid = user_to_sid.get(username)
            if sid:
                emit('kicked', {'by': 'SYSTEM', 'reason': 'You are temporarily kicked', 'remaining_sec': int(until - time.time())}, room=sid)
            return
        # If a user sends a message but isn't marked online (e.g., transient disconnect), ensure presence
        if username not in online_users:
            online_users.add(username)
            socketio.emit('online_users', list(online_users))
        # Activity counts as a heartbeat
        last_seen[username] = time.time()
        entry = _make_user_message(username, msg)
        messages.append(entry)
        socketio.emit('new_message', entry)


@socketio.on('private_message')
def handle_private_message(data):
    sender = data.get('from')
    recipient = data.get('to')
    msg = data.get('message')
    if not sender or not recipient or not msg:
        return
    entry = {"from": sender, "to": recipient, "message": msg}
    # deliver to recipient if online
    sid = user_to_sid.get(recipient)
    if sid:
        socketio.emit('private_message', entry, room=sid)
    # echo back to sender so their UI updates
    sid_sender = user_to_sid.get(sender) or request.sid
    if sid_sender:
        socketio.emit('private_message', entry, room=sid_sender)


@socketio.on('host_game')
def handle_host(data):
    username = data.get('username')
    address = data.get('address')
    game_name = data.get('game_name', 'Custom Game')
    players = int(data.get('players', 0))
    max_players = int(data.get('max_players', 10))
    status = data.get('status', 'Waiting')
    map_name = data.get('map', 'dota')
    
    if username and address:
        active_hosts[username] = {
            "address": address,
            "game_name": game_name,
            "players": players,
            "max_players": max_players,
            "status": status,
            "map": map_name,
            "created_at": time.time()
        }
        socketio.emit('update_hosts', active_hosts)
        
        # Broadcast game creation message
        msg = _make_system_message(f'🎮 {username} is hosting "{game_name}" ({players}/{max_players} players) - {status}')
        messages.append(msg)
        socketio.emit('new_message', msg)

        # Create lobby structure for host
        try:
            lobbies[username] = {"max_players": max_players, "members": set([username]), "chat": []}
            socketio.emit('lobby_update', {"host": username, "members": list(lobbies[username]["members"]), "max_players": max_players})
        except Exception:
            pass


@socketio.on('get_hosts')
def handle_get_hosts():
    emit('update_hosts', active_hosts)

@socketio.on('lobby_join')
def handle_lobby_join(data):
    host = data.get('host')
    user = sid_to_user.get(request.sid)
    if not host or not user:
        return
    lob = lobbies.get(host)
    if not lob:
        return
    if len(lob['members']) >= int(active_hosts.get(host, {}).get('max_players', lob.get('max_players', 10))):
        return
    lob['members'].add(user)
    # update host players count
    if host in active_hosts:
        active_hosts[host]['players'] = len(lob['members'])
        socketio.emit('update_hosts', active_hosts)
    socketio.emit('lobby_update', {"host": host, "members": list(lob['members']), "max_players": lob.get('max_players', 10)})

@socketio.on('lobby_leave')
def handle_lobby_leave(data):
    host = data.get('host')
    user = sid_to_user.get(request.sid)
    if not host or not user:
        return
    lob = lobbies.get(host)
    if not lob:
        return
    if user in lob['members']:
        lob['members'].discard(user)
        if host in active_hosts:
            active_hosts[host]['players'] = max(0, len(lob['members']))
            socketio.emit('update_hosts', active_hosts)
        socketio.emit('lobby_update', {"host": host, "members": list(lob['members']), "max_players": lob.get('max_players', 10)})

@socketio.on('lobby_message')
def handle_lobby_message(data):
    host = data.get('host')
    msg = data.get('message')
    user = sid_to_user.get(request.sid)
    if not host or not msg or not user:
        return
    lob = lobbies.get(host)
    if not lob or user not in lob['members']:
        return
    entry = _make_user_message(user, msg)
    lob['chat'].append(entry)
    # send to lobby members only
    for m in list(lob['members']):
        sid = user_to_sid.get(m)
        if sid:
            socketio.emit('lobby_message', {"host": host, "message": entry}, room=sid)

@socketio.on('lobby_kick')
def handle_lobby_kick(data):
    host = data.get('host')
    target = data.get('target')
    user = sid_to_user.get(request.sid)
    if not host or not target or not user:
        return
    if user != host:
        return
    lob = lobbies.get(host)
    if not lob or target not in lob['members']:
        return
    lob['members'].discard(target)
    if host in active_hosts:
        active_hosts[host]['players'] = max(0, len(lob['members']))
        socketio.emit('update_hosts', active_hosts)
    socketio.emit('lobby_update', {"host": host, "members": list(lob['members']), "max_players": lob.get('max_players', 10)})
    sid = user_to_sid.get(target)
    if sid:
        socketio.emit('lobby_kicked', {"host": host, "by": host}, room=sid)

@socketio.on('lobby_start')
def handle_lobby_start(data):
    host = data.get('host')
    user = sid_to_user.get(request.sid)
    if not host or not user or user != host:
        return
    lob = lobbies.get(host)
    if not lob:
        return
    # Notify host to start immediately
    sid_host = user_to_sid.get(host)
    if sid_host:
        socketio.emit('lobby_start_now', {"host": host}, room=sid_host)
    # Notify others to start in 10 seconds
    for m in list(lob['members']):
        if m == host:
            continue
        sid = user_to_sid.get(m)
        if sid:
            socketio.emit('lobby_start_delayed', {"host": host, "delay_sec": 10}, room=sid)

@socketio.on('update_game_status')
def handle_update_game_status(data):
    username = data.get('username')
    players = data.get('players')
    max_players = data.get('max_players')
    status = data.get('status')
    
    if username and username in active_hosts:
        if players is not None:
            active_hosts[username]['players'] = int(players)
        if max_players is not None:
            active_hosts[username]['max_players'] = int(max_players)
        if status:
            active_hosts[username]['status'] = status
            
        socketio.emit('update_hosts', active_hosts)
        
        # Broadcast status update if significant change
        if status and status != 'Waiting':
            msg = _make_system_message(f'🎮 {username}\'s game status: {status} ({active_hosts[username]["players"]}/{active_hosts[username]["max_players"]} players)')
            messages.append(msg)
            socketio.emit('new_message', msg)

@socketio.on('stop_hosting')
def handle_stop_hosting(data):
    username = data.get('username')
    if username and username in active_hosts:
        game_info = active_hosts.pop(username)
        socketio.emit('update_hosts', active_hosts)
        
        # Broadcast game ended message
        msg = _make_system_message(f'🏁 {username} stopped hosting "{game_info.get("game_name", "Custom Game")}"')
        messages.append(msg)
        socketio.emit('new_message', msg)
        # Remove lobby if exists
        try:
            if username in lobbies:
                lobbies.pop(username, None)
                socketio.emit('lobby_closed', {"host": username})
        except Exception:
            pass


@socketio.on('get_profiles_all')
def handle_get_profiles_all():
    # Send a full snapshot of known profiles to the requester
    emit('profiles_snapshot', user_profiles)


@socketio.on('update_profile')
def handle_update_profile(data):
    username = data.get('username')
    if not username:
        return
    
    print(f"Profile update for {username}: {data}")
    profile = user_profiles.get(username, {
        "age": "",
        "nationality": "",
        "nation_code": None,
        "gender": "",
        "status": "Online",
        "role": "Basic Member"
    })
    # Update fields; accept nation_code and avatar_b64 if provided
    if 'age' in data:
        profile['age'] = data.get('age')
    if 'nationality' in data:
        profile['nationality'] = data.get('nationality')
    if 'nation_code' in data:
        profile['nation_code'] = data.get('nation_code')
    if 'gender' in data:
        profile['gender'] = data.get('gender')
    if 'status' in data:
        profile['status'] = data.get('status')
    if 'avatar_b64' in data:
        profile['avatar_b64'] = data.get('avatar_b64')
    if 'role' in data:
        profile['role'] = data.get('role')
    user_profiles[username] = profile
    socketio.emit('profile_updated', {username: profile})
    # Any profile update indicates presence
    last_seen[username] = time.time()


@socketio.on('client_heartbeat')
def handle_client_heartbeat(data):
    username = data.get('username') or sid_to_user.get(request.sid)
    if not username:
        return
    # block if kicked
    until = kicked_users.get(username)
    if until and time.time() < until:
        sid = user_to_sid.get(username)
        if sid:
            emit('kicked', {'by': 'SYSTEM', 'reason': 'You are temporarily kicked', 'remaining_sec': int(until - time.time())}, room=sid)
        return
    # Update last seen and recover presence if needed
    last_seen[username] = time.time()
    if username not in online_users:
        online_users.add(username)
        socketio.emit('online_users', list(online_users))


def _get_admin_level(role):
    """Return admin level: 0=Basic Member, 1=Channel Admin, 2=Super Admin"""
    role_lower = str(role).lower()
    if role_lower == 'super admin':
        return 2
    elif role_lower == 'channel admin':
        return 1
    else:
        return 0

@socketio.on('admin_kick')
def handle_admin_kick(data):
    admin = sid_to_user.get(request.sid)
    target = data.get('target')
    minutes = int(data.get('minutes') or 0)
    reason = data.get('reason', 'No reason provided')
    
    print(f"Admin kick attempt: admin={admin}, target={target}, minutes={minutes}, reason={reason}")
    
    if not admin or not target or minutes < 0:
        print(f"Kick validation failed: admin={admin}, target={target}, minutes={minutes}")
        return
    
    # Get admin and target roles
    admin_role = user_profiles.get(admin, {}).get('role', 'Basic Member')
    target_role = user_profiles.get(target, {}).get('role', 'Basic Member')
    admin_level = _get_admin_level(admin_role)
    target_level = _get_admin_level(target_role)
    
    # Check permissions
    if admin_level == 0:  # Basic Member can't kick anyone
        print(f"Kick denied: {admin} is not an admin (level {admin_level})")
        return
    elif admin_level == 1:  # Channel Admin restrictions
        if target_level >= 1:  # Can't kick other admins
            print(f"Kick denied: {admin} cannot kick other admins")
            return
        if minutes > 30:  # Max 30 minutes
            minutes = 30
    elif admin_level == 2:  # Super Admin restrictions
        if target_level == 2:  # Can't kick other Super Admins
            print(f"Kick denied: {admin} cannot kick other Super Admins")
            return
        if minutes > 1000:  # Max 1000 minutes
            minutes = 1000
    
    until = time.time() + minutes * 60
    kicked_users[target] = until
    print(f"Kick successful: {target} kicked for {minutes} minutes by {admin}")
    
    # disconnect target if online
    sid = user_to_sid.get(target)
    if sid:
        emit('kicked', {'by': admin, 'reason': reason, 'remaining_sec': int(minutes * 60)}, room=sid)
        try:
            # schedule immediate disconnect
            socketio.server.disconnect(sid)
        except Exception:
            pass
    
    # broadcast notice
    admin_title = "Super Admin" if admin_level == 2 else "Channel Admin"
    notice = _make_system_message(f'🚫 {target} has been kicked by {admin_title} {admin} (Reason: {reason})')
    messages.append(notice)
    socketio.emit('new_message', notice)
    
    # broadcast audio event to all users
    socketio.emit('play_audio', {'audio_file': 'kicked.mp3'})

@socketio.on('admin_ban')
def handle_admin_ban(data):
    admin = sid_to_user.get(request.sid)
    target = data.get('target')
    minutes = int(data.get('minutes') or 0)
    reason = data.get('reason', 'No reason provided')
    
    print(f"Admin ban attempt: admin={admin}, target={target}, minutes={minutes}, reason={reason}")
    
    if not admin or not target:
        print(f"Ban validation failed: admin={admin}, target={target}")
        return
    
    # Only Super Admins can ban
    admin_role = user_profiles.get(admin, {}).get('role', 'Basic Member')
    if _get_admin_level(admin_role) != 2:
        print(f"Ban denied: {admin} is not a Super Admin (role: {admin_role})")
        return
    
    # Get target's IP - try to get from user_to_sid mapping or use placeholder
    target_ip = "127.0.0.1"  # Default fallback
    target_sid = user_to_sid.get(target)
    if target_sid:
        # Try to get the actual IP from the socket connection
        # This is a simplified approach - in production you'd want more robust IP tracking
        try:
            # Get IP from the request context if available
            target_ip = request.environ.get('REMOTE_ADDR', '127.0.0.1')
        except:
            pass
    
    if minutes == 0:
        # Permanent ban
        banned_ips[target_ip] = 0
        ban_msg = "permanently"
    else:
        # Temporary ban
        until = time.time() + minutes * 60
        banned_ips[target_ip] = until
        ban_msg = f"for {minutes} minutes"
    
    print(f"Ban successful: {target} banned {ban_msg} by {admin} (IP: {target_ip})")
    
    # Kick the user immediately
    sid = user_to_sid.get(target)
    if sid:
        emit('kicked', {'by': admin, 'reason': f'Banned {ban_msg} - {reason}', 'remaining_sec': int(minutes * 60) if minutes > 0 else -1}, room=sid)
        try:
            socketio.server.disconnect(sid)
        except Exception:
            pass
    
    # broadcast notice
    notice = _make_system_message(f'🔨 {target} has been banned by Super Admin {admin} {ban_msg} (Reason: {reason})')
    messages.append(notice)
    socketio.emit('new_message', notice)
    
    # broadcast audio event to all users
    socketio.emit('play_audio', {'audio_file': 'banned.mp3'})

@socketio.on('admin_promote')
def handle_admin_promote(data):
    admin = sid_to_user.get(request.sid)
    target = data.get('target')
    
    if not admin or not target:
        return
    
    # Only Super Admins can promote to Channel Admin
    admin_role = user_profiles.get(admin, {}).get('role', 'Basic Member')
    if _get_admin_level(admin_role) != 2:
        return
    
    # Can't promote other Super Admins
    target_role = user_profiles.get(target, {}).get('role', 'Basic Member')
    if _get_admin_level(target_role) >= 2:
        return
    
    # Promote to Channel Admin
    user_profiles[target] = {**user_profiles.get(target, {}), 'role': 'Channel Admin'}
    socketio.emit('profile_updated', {target: user_profiles[target]})
    
    # broadcast notice
    notice = _make_system_message(f'👑 {target} has been promoted to Channel Admin by Super Admin {admin}')
    messages.append(notice)
    socketio.emit('new_message', notice)

@socketio.on('admin_demote')
def handle_admin_demote(data):
    admin = sid_to_user.get(request.sid)
    target = data.get('target')
    
    if not admin or not target:
        return
    
    # Only Super Admins can demote
    admin_role = user_profiles.get(admin, {}).get('role', 'Basic Member')
    if _get_admin_level(admin_role) != 2:
        return
    
    # Can only demote Channel Admins (not other Super Admins)
    target_role = user_profiles.get(target, {}).get('role', 'Basic Member')
    if _get_admin_level(target_role) != 1:  # Only Channel Admins
        return
    
    # Demote to Basic Member
    user_profiles[target] = {**user_profiles.get(target, {}), 'role': 'Basic Member'}
    socketio.emit('profile_updated', {target: user_profiles[target]})
    
    # broadcast notice
    notice = _make_system_message(f'📉 {target} has been demoted to Basic Member by Super Admin {admin}')
    messages.append(notice)
    socketio.emit('new_message', notice)


def _confirm_offline(username):
    # If the user reconnected (has a sid), abort
    if username in user_to_sid:
        return
    # If we received a heartbeat recently, abort
    last = last_seen.get(username, 0)
    if time.time() - last < GRACE_SECONDS:
        return
    # Now mark offline and broadcast leave message
        online_users.discard(username)
        active_hosts.pop(username, None)
        if username in user_profiles:
            user_profiles[username]['status'] = 'Offline'
            socketio.emit('profile_updated', {username: user_profiles[username]})
        socketio.emit('online_users', list(online_users))
        socketio.emit('update_hosts', active_hosts)
        msg = _make_system_message(f'❌ {username} left {ROOM_NAME}')
        messages.append(msg)
        socketio.emit('new_message', msg)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    username = sid_to_user.pop(sid, None)
    if username:
        user_to_sid.pop(username, None)
        # record last seen and delay the offline announcement
        last_seen[username] = time.time()
        gevent.spawn_later(GRACE_SECONDS, _confirm_offline, username)


if __name__ == "__main__":
    # Seed fake users before starting the server so clients see them immediately
    try:
        seed_fake_users()
    except Exception:
        pass
    # Broadcast initial state shortly after startup
    def _broadcast_seed():
        try:
            socketio.emit('online_users', list(online_users))
            socketio.emit('profile_updated', {u: user_profiles[u] for u in user_profiles})
        except Exception:
            pass
    gevent.spawn_later(0.5, _broadcast_seed)
    # Start fake chat background loop
    gevent.spawn(_simulate_fake_chat_loop)
    # Start presence simulation loop (joins/leaves + scripted chats)
    gevent.spawn(_simulate_presence_loop)
    socketio.run(flask_app, host="0.0.0.0", port=5000)

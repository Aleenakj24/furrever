
#http://127.0.0.1:5000/
from flask import Flask, render_template, request, redirect,session, url_for
import mysql.connector
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask import jsonify
from werkzeug.utils import secure_filename
import os
import requests
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS ")
EMAIL_PASSWORD =  os.getenv("EMAIL_PASSWORD ")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def send_abuse_email(abuse_type, location, date, description):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS
    msg["Subject"] = " Animal Abuse Report - FurrEver"
    body = f"""
    A new animal abuse report has been submitted.

    Type of Abuse: {abuse_type}
    Location: {location}
    Date: {date}

    Description:
    {description}

    Please take appropriate action.
    """

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Abuse report email sent successfully")

    except Exception as e:
        print("Email error:", e)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)
app.secret_key = "pawcare_secret_key"
app.permanent_session_lifetime = timedelta(days=7)  # keep login for 7 days
#UPLOAD_FOLDER = 'static/uploads'
#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
#PROFILE_PIC_FOLDER = "static/profile_pics"
PROFILE_PIC_FOLDER = os.path.join(app.root_path, "static", "profile_pics")
app.config["PROFILE_PIC_FOLDER"] = PROFILE_PIC_FOLDER
#app.config["PROFILE_PIC_FOLDER"] = os.path.join("static", "profile_pics")
app.config["PROFILE_PIC_FOLDER"] = os.path.join(app.root_path, "static", "profile_pics")
os.makedirs(app.config["PROFILE_PIC_FOLDER"], exist_ok=True)




# -------- DATABASE CONNECTION --------

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password = os.getenv("DB_PASSWORD"),
        database="pawcare_db",
        autocommit=True
    )

db=get_db()
cursor = db.cursor(dictionary=True)

# -------- HOME PAGE --------
@app.route('/')
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    return render_template("index.html", pets=pets)

# -------- ADD PET PAGE --------
@app.route('/add-pet', methods=['GET', 'POST'])
def add_pet():
    if request.method == 'POST':
        db = get_db()
        cursor = db.cursor()

        name = request.form['name']
        age = request.form['age']
        pet_type = request.form['type']
        breed = request.form['breed']
        description = request.form['description']
        vaccinated = request.form['vaccinated']
        owner_name = request.form['owner_name']
        contact = request.form['contact']
        email = request.form['email']
        location = request.form['location']

        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        cursor.execute("""
            INSERT INTO pets 
            (name, age, type, breed, description, vaccinated,
             owner_name, contact, email, location, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name, age, pet_type, breed, description,
            vaccinated, owner_name, contact, email, location,
            filename
        ))

        db.commit()
        cursor.close()
        db.close()

        return redirect('/adopt')

    return render_template('add_pet.html')

# -------- ADOPT PAGE --------
@app.route('/adopt')
def adopt():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()
    cursor.close()
    return render_template("adopt.html", pets=pets)
    pet_type = request.args.get('type')

    if pet_type:
        cursor.execute("SELECT * FROM pets WHERE type=%s", (pet_type,))
    else:
        cursor.execute("SELECT * FROM pets")

    pets = cursor.fetchall()
    return render_template("adopt.html", pets=pets, pet_type=pet_type)

# -------- PET DETAILS PAGE --------

@app.route('/pet/<int:pet_id>')
def pet_details(pet_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
    pet = cursor.fetchone()

    cursor.close()
    db.close()

    if not pet:
        return "Pet not found", 404

    return render_template("pet_details.html", pet=pet)

# -------- REPORT ABUSE PAGE --------

@app.route("/report-abuse", methods=["GET", "POST"])
def report_abuse():
    if request.method == "POST":
        abuse_type = request.form["abuse_type"]
        location = request.form["location"]
        date = request.form["date"]
        description = request.form["description"]

        evidence = request.files["evidence"]
        filename = None

        if evidence and evidence.filename != "":
            filename = secure_filename(evidence.filename)
            evidence.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO abuse_reports
            (abuse_type, location, incident_date, description, evidence)
            VALUES (%s, %s, %s, %s, %s)
        """, (abuse_type, location, date, description, filename))

        db.commit()

        send_abuse_email(abuse_type, location, date, description)


        cursor.close()

        return render_template("abuse_success.html")


    return render_template("report.html")



@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot-start')
def chatbot_start():
    return render_template('start.html')

# ---------------- GET USERNAME ----------------
def get_username(user_id):
    query = "SELECT username FROM users WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    return result["username"] if result else None

# ---------------- GET USER PREFERENCE ----------------
def get_user_preference(user_id):
    query = "SELECT pet_type, pet_age FROM preferences WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()

# ---------------- GEMINI CHATBOT ----------------
def ask_gemini_petcare(question, pet_type=None, pet_age=None):
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={API_KEY}"

        if pet_type and pet_age:
            prompt = (
                f"You are a PetCare chatbot. "
                f"The user has a {pet_age} {pet_type}. "
                f"Answer only pet-related questions like food, grooming, health, vaccination. "
                f"Question: {question}"
            )
        else:
            prompt = (
                "You are a PetCare chatbot. "
                "Answer only pet-related questions. "
                f"Question: {question}"
            )

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }]
        }

        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code != 200:
            return f"API Error: Status {response.status_code}"
            
        data = response.json()

        if "error" in data:
            return f"API Error: {data['error'].get('message', 'Unknown')}"

        reply = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "Sorry, I could not generate a response.")
        )
        return reply
        
    except Exception as e:
        return f"Sorry, API call failed. Please try again."


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").lower()

    # TEMP: logged-in user
    user_id = 1

    username = None
    preference = None
    
    try:
        username = get_username(user_id)
        preference = get_user_preference(user_id)
    except:
        pass

    # -------- GREETING LOGIC --------
    if user_message.startswith(("hi", "hello", "hey")):
        if username:
            return jsonify({
                "reply": f"Hi {username} 👋🐾 I’m your PetCare Assistant. How can I help you today?"
            })
        else:
            return jsonify({
                "reply": "Hi 👋🐾 I’m your PetCare Assistant. How can I help you today?"
            })

    # -------- NORMAL CHAT --------
    try:
        if preference:
            reply = ask_gemini_petcare(
                user_message,
                preference["pet_type"],
                preference["pet_age"]
            )
        else:
            reply = ask_gemini_petcare(user_message)
    except Exception as e:
        reply = "Sorry, I couldn't process that. Please try again."

    return jsonify({"reply": reply})

# -------- PET MATCH PAGE --------



def get_ai_pet_match(home, experience, time, pets):

    if not pets:
        return []

    pet_list_text = ""
    for pet in pets:
        pet_list_text += f"""
    ID: {pet['id']} 
    Name: {pet.get('name', '')}
    Type: {pet.get('type', '')}
    Age: {pet.get('age', '')}
    Temperament: {pet.get('temperament', 'Unknown')}
    Description: {pet.get('description', 'No description')}
    ---
"""

    prompt = f"""
    You are a pet adoption recommendation engine.

    User Details:
    Home type: {home}
    Experience level: {experience}
    Free time available: {time}

    Available Pets:
    {pet_list_text}

    Select up to 3 most suitable pets.

    IMPORTANT:
        - Only return numeric IDs.
        - Separate them using commas.
        - If none are suitable, return exactly: NONE

    Example:
    1,5,8



    Do not explain anything.
    Only return the numbers.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()

        print("FULL GEMINI RESPONSE:")
        print(result)

        text = ""

        if "candidates" in result and result["candidates"]:
            content = result["candidates"][0].get("content", {})
            parts = content.get("parts", [])
        if parts and "text" in parts[0]:
            text = parts[0]["text"]

        print("AI RAW OUTPUT:", text)

        if not text:
            return []

        if "NONE" in text.upper():
            return []

        ids = [int(num) for num in re.findall(r"\d+", text)]

        print("Extracted IDs:", ids)

        return ids




    except Exception as e:
        print("AI Matching Error:", e)
        return []




@app.route('/pet-match', methods=['GET', 'POST'])
def pet_match():
    if request.method == 'POST':

        home = request.form.get('home', '')
        experience = request.form.get('experience', '')
        time = request.form.get('time', '')

        # 1️⃣ Get all pets from DB
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pets")
        all_pets = cursor.fetchall()

        # 2️⃣ Send to AI
        matched_ids = get_ai_pet_match(home, experience, time, all_pets)

        # 3️⃣ Filter matched pets
        matched_pets = [
            pet for pet in all_pets
            if pet["id"] in matched_ids
        ]

        return render_template(
            'pet_match_result.html',
            pets=matched_pets
        )

    return render_template('pet_match.html')



# -------- PAW-GRAM (SOCIAL FEED) --------

@app.route("/paw-gram", methods=["GET", "POST"])
def paw_gram():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # TEMP logged-in user
    #session["user_id"] = 1
    if "user_id" not in session:
        return redirect(url_for("auth"))

    # Now proceed with real user_id
    user_id = session["user_id"]

    if request.method == "POST":
        caption = request.form.get("caption")
        image = request.files.get("image")
        user_id = session.get("user_id")

        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            cursor.execute(
                "INSERT INTO paw_posts (caption, image, user_id) VALUES (%s,%s,%s)",
                (caption, filename, user_id)
            )

        cursor.close()
        db.close()
        return redirect(url_for("paw_gram"))

    cursor.execute("""
        SELECT paw_posts.id, paw_posts.caption, paw_posts.image,
        paw_posts.created_at, users.name,users.profile_pic
        FROM paw_posts
        JOIN users ON paw_posts.user_id = users.id
        ORDER BY paw_posts.created_at DESC
    """)
    posts = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("paw-gram.html", posts=posts)



@app.route("/auth", methods=["GET", "POST"])
def auth():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    error = None
    if request.method == "POST":
        action = request.form.get("action")  # "login" or "signup"
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if action == "signup":
            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                error = "Email already registered."
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,'adopter')",
                    (name, email, hashed_password)
                )
                db.commit()
                session["user_id"] = cursor.lastrowid
                session["name"] = name
                cursor.close()
                db.close()
                return redirect(url_for("paw_gram"))

        elif action == "login":
            #remember = request.form.get("remember")
            remember = request.form.get("remember") == "on"
            

            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))

            user = cursor.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                #session.permanent = True if remember else False
                session.clear()    
                session.permanent = remember
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                cursor.close()
                db.close()
                return redirect(url_for("paw_gram"))
            else:
                error = "Invalid email or password."

    cursor.close()
    db.close()
    return render_template("auth.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth"))




@app.route("/profile/<username>")
def profile(username):
    if "user_id" not in session:
        return redirect(url_for("auth"))

    cursor = db.cursor(dictionary=True)

    # get user info
    cursor.execute("SELECT * FROM users WHERE name=%s", (username,))
    user = cursor.fetchone()

    if not user:
        return "User not found", 404

    # get user's posts
    cursor.execute("""
    SELECT paw_posts.*, users.name,users.profile_pic
    FROM paw_posts
    JOIN users ON paw_posts.user_id = users.id
    WHERE paw_posts.user_id = %s
    ORDER BY paw_posts.created_at DESC
""", (user["id"],))
    posts = cursor.fetchall()


    return render_template(
        "profile.html",
        user=user,
        posts=posts
    )

#like post

@app.route("/like-post", methods=["POST"])
def like_post():
    if "user_id" not in session:
        return jsonify({"error": "login required"}), 401

    data = request.get_json()
    post_id = data["post_id"]
    user_id = session["user_id"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT id FROM paw_likes WHERE post_id=%s AND user_id=%s",
        (post_id, user_id)
    )
    liked = cursor.fetchone()

    if liked:
        cursor.execute(
            "DELETE FROM paw_likes WHERE post_id=%s AND user_id=%s",
            (post_id, user_id)
        )
        action = "unliked"
    else:
        cursor.execute(
            "INSERT INTO paw_likes (post_id, user_id) VALUES (%s,%s)",
            (post_id, user_id)
        )
        action = "liked"
    db.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM paw_likes WHERE post_id=%s",
        (post_id,)
    )
    count = cursor.fetchone()[0]

    return jsonify({"status": action, "likes": count})


#get likes
@app.route("/get-likes/<int:post_id>")
def get_likes(post_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM paw_likes WHERE post_id=%s",
        (post_id,)
    )
    count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT 1 FROM paw_likes WHERE post_id=%s AND user_id=%s",
        (post_id, session.get("user_id", 0))
    )
    liked = cursor.fetchone() is not None

    return jsonify({"likes": count, "liked": liked})


@app.route("/get-comments/<int:post_id>")
def get_comments(post_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            paw_comments.text,
            users.name,
            users.profile_pic
        FROM paw_comments
        JOIN users ON users.id = paw_comments.user_id
        WHERE paw_comments.post_id = %s
        ORDER BY paw_comments.created_at ASC
    """, (post_id,))

    comments = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify(comments)




#add comment
@app.route("/add-comment", methods=["POST"])
def add_comment():
    if "user_id" not in session:
        return jsonify({"error": "login required"}), 401

    data = request.get_json()
    post_id = data["post_id"]
    text = data["comment"]   # frontend still sends "comment"
    user_id = session["user_id"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT INTO paw_comments (post_id, user_id, text) VALUES (%s,%s,%s)",
        (post_id, user_id, text)
    )

    db.commit()
    cursor.close()
    db.close()

    return jsonify({"success": True})



@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("auth"))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user = cursor.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        bio = request.form["bio"]
        profile_pic = user["profile_pic"]

        file = request.files.get("profile_pic")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["PROFILE_PIC_FOLDER"], filename))
            profile_pic = filename

        cursor.execute("""
            UPDATE users
            SET name=%s, bio=%s, profile_pic=%s
            WHERE id=%s
        """, (name, bio, profile_pic, session["user_id"]))

        db.commit()
        session["name"] = name

        return redirect(url_for("profile", username=name))

    return render_template("edit_profile.html", user=user)


@app.route("/delete-post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session:
        return jsonify({"error": "login required"}), 401

    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor()

    # 🔒 only allow deleting own post
    cursor.execute(
        "SELECT image FROM paw_posts WHERE id=%s AND user_id=%s",
        (post_id, user_id)
    )
    post = cursor.fetchone()

    if not post:
        return jsonify({"error": "not allowed"}), 403

    # delete image file
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], post[0])
    if os.path.exists(image_path):
        os.remove(image_path)

    # delete likes + comments first (IMPORTANT)
    cursor.execute("DELETE FROM paw_likes WHERE post_id=%s", (post_id,))
    cursor.execute("DELETE FROM paw_comments WHERE post_id=%s", (post_id,))
    cursor.execute("DELETE FROM paw_posts WHERE id=%s", (post_id,))

    db.commit()
    return jsonify({"success": True})

#paw_feed page
@app.route("/paw-feed")
def paw_feed():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT paw_posts.id, paw_posts.image, paw_posts.caption,
               paw_posts.created_at,
               users.name, users.profile_pic
        FROM paw_posts
        JOIN users ON paw_posts.user_id = users.id
        ORDER BY paw_posts.created_at DESC
    """)

    posts = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("paw_feed.html", posts=posts)




#grooming page
@app.route('/grooming')
def grooming():
    return render_template('grooming.html')

#shelter map page
@app.route("/get-map-data")
def get_map_data():

    city=request.args.get("city")

    db=get_db()
    cursor=db.cursor(dictionary=True)

    if city:
        cursor.execute(
          "SELECT * FROM shelters WHERE city LIKE %s",
          ("%"+city+"%",)
        )
    else:
        cursor.execute("SELECT * FROM shelters")

    shelters=cursor.fetchall()

    return jsonify({"shelters":shelters})


# -------- GROOMING MAP DATA --------
@app.route("/get-grooming-data")
def get_grooming_data():

    place = request.args.get("place", "").strip().lower()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if place:
        query = """
            SELECT * FROM grooming_centers
            WHERE LOWER(city) LIKE %s
               OR LOWER(address) LIKE %s
        """
        search_term = f"%{place}%"
        cursor.execute(query, (search_term, search_term))
    else:
        cursor.execute("SELECT * FROM grooming_centers")

    grooming = cursor.fetchall()

    return jsonify({"grooming": grooming})


@app.route("/health-services")
def health_services():
    return render_template("health_services.html")

@app.route("/get-health-services")
def get_health_services():

    place = request.args.get("place", "").lower()

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # -------- VETS --------
    if place:
        cursor.execute("""
            SELECT *, 'vet' AS type FROM vet_services
            WHERE LOWER(city) LIKE %s
            OR LOWER(district) LIKE %s
        """, (f"%{place}%", f"%{place}%"))
    else:
        cursor.execute("SELECT *, 'vet' AS type FROM vet_services")

    vets = cursor.fetchall()

    # -------- PHARMACIES --------
    if place:
        cursor.execute("""
            SELECT *, 'pharmacy' AS type FROM pet_pharmacies
            WHERE LOWER(city) LIKE %s
            OR LOWER(district) LIKE %s
        """, (f"%{place}%", f"%{place}%"))
    else:
        cursor.execute("SELECT *, 'pharmacy' AS type FROM pet_pharmacies")

    pharmacies = cursor.fetchall()

    services = vets + pharmacies

    return jsonify({"services": services})



# -------- RUN SERVER --------
if __name__ == '__main__':
    app.run(debug=True)
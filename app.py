
import flask
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import secrets
from functools import wraps
from databaser import Databaser
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db = Databaser()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def root():
    videos = db.get_videos()
    return render_template('index.html', videos=videos, db=db)


@app.route('/search')
def search():
    query = request.args.get('q')
    videos = db.search_videos(query)
    return render_template('index.html', videos=videos, db=db)


@app.route('/<video_id>')
def video_page(video_id):
    video = db.get_video(video_id)

    if video is None:
        return 'Видео не найдено'

    user_id = session.get('user_id')
    if user_id:
        user = db.get_user(user_id)
    else:
        user = None

    comments = db.get_comments(video_id)

    return render_template('video_page.html', video=video, user=user, comments=comments)


@app.route('/<video_id>/like', methods=['POST'])
@login_required
def like_video(video_id):
    video_id = int(video_id)
    user_id = session['user_id']
    db.like_video(video_id, user_id)
    return 'ok'


@app.route('/<video_id>/dislike', methods=['POST'])
@login_required
def dislike_video(video_id):
    video_id = int(video_id)
    user_id = session['user_id']
    db.dislike_video(video_id, user_id)
    return 'ok'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        description = request.form['description']

        avatar = request.files['avatar'] if 'avatar' in request.files else None
        avatar_filename = None

        if len(password) < 7:
            flash('Пароль должен содержать не менее 7 символов.', 'error')
            return render_template('register.html')
        if not any(c.isupper() for c in password):
            flash('Пароль должен содержать хотя бы одну заглавную букву.', 'error')
            return render_template('register.html')
        if not any(c.isdigit() for c in password):
            flash('Пароль должен содержать хотя бы одну цифру.', 'error')
            return render_template('register.html')

        if db.get_user_by_username(username):
            flash('Имя пользователя уже занято.', 'error')
            return render_template('register.html')

        if avatar and avatar.filename != '':
            if allowed_file(avatar.filename):
                avatar_filename = secure_filename(avatar.filename)
                avatar.save(os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename))
            else:
                flash('Недопустимый формат аватара.', 'error')
                return render_template('register.html')

        user_id = db.add_user(name, username, password, description, avatar_filename)
        session['user_id'] = user_id
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('root'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = db.get_user_by_username(username)

        if user and db.verify_password(password, user['password']):
            session['user_id'] = user['id']
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('root'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('root'))


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        video_file = request.files['video']
        thumbnail = request.files['thumbnail']
        author_id = session['user_id']

        if not all([name, description, video_file, thumbnail]):
            flash('Пожалуйста, заполните все поля.', 'error')
            return render_template('upload.html')

        if video_file and allowed_file(video_file.filename) and thumbnail and allowed_file(thumbnail.filename):
            video_filename = secure_filename(video_file.filename)
            thumbnail_filename = secure_filename(thumbnail.filename)

            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], thumbnail_filename)

            video_file.save(video_path)
            thumbnail.save(thumbnail_path)

            db.add_video(name, description, video_filename, thumbnail_filename, author_id)
            flash('Видео успешно загружено!', 'success')
            return redirect(url_for('root'))
        else:
            flash('Недопустимый формат файла.', 'error')
            return render_template('upload.html')

    return render_template('upload.html')


@app.route('/profile/<username>')
def profile(username):
    user = db.get_user_by_username(username)

    if not user:
        return 'Пользователь не найден'

    videos = db.get_videos_by_user(user['id'])
    subscriber_count = db.get_subscriber_count(user['id'])

    is_subscribed = False
    if 'user_id' in session:
        is_subscribed = db.is_subscribed(session['user_id'], user['id'])

    return render_template('profile.html', user=user, videos=videos, subscriber_count=subscriber_count, is_subscribed=is_subscribed, db=db)


@app.route('/subscribe/<profile_id>', methods=['POST'])
@login_required
def subscribe(profile_id):
    user_id = session['user_id']
    profile_id = int(profile_id)

    db.subscribe_user(user_id, profile_id)
    return redirect(url_for('profile', username=db.get_user(profile_id)['username']))


@app.route('/unsubscribe/<profile_id>', methods=['POST'])
@login_required
def unsubscribe(profile_id):
    user_id = session['user_id']
    profile_id = int(profile_id)

    db.unsubscribe_user(user_id, profile_id)
    return redirect(url_for('profile', username=db.get_user(profile_id)['username']))


@app.route('/comment/<video_id>', methods=['POST'])
@login_required
def add_comment(video_id):
    video_id = int(video_id)
    user_id = session['user_id']
    text = request.form['comment']

    if text:
        db.add_comment(video_id, user_id, text)

    return redirect(url_for('video_page', video_id=video_id))


# API Endpoints (Basic Structure)
@app.route('/api/video/<video_id>')
def get_video_api(video_id):
    video = db.get_video(video_id)
    if video:
        return jsonify(video)
    return jsonify({'error': 'Video not found'}), 404

@app.route('/api/author/<username>')
def get_author_api(username):
    user = db.get_user_by_username(username)
    if user:
        return jsonify(user)
    return jsonify({'error': 'Author not found'}), 404

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)

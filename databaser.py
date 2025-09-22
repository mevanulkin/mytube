
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


class Databaser:

    def __init__(self, db_name='database.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                description TEXT,
                avatar TEXT
            )
        ''')

        self.cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            desc TEXT NOT NULL,
                            video_file TEXT NOT NULL,
                            thumbnail TEXT NOT NULL,
                            author_id INTEGER NOT NULL,
                            likes INTEGER DEFAULT 0,
                            dislikes INTEGER DEFAULT 0,
                            date_create DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (author_id) REFERENCES users (id)
                            )''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                user_id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                like_type INTEGER NOT NULL,
                PRIMARY KEY (user_id, video_id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (video_id) REFERENCES videos (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscribers (
                subscriber_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                PRIMARY KEY (subscriber_id, profile_id),
                FOREIGN KEY (subscriber_id) REFERENCES users (id),
                FOREIGN KEY (profile_id) REFERENCES users (id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        self.connection.commit()

    def add_user(self, name, username, password, description=None, avatar=None):
        hashed_password = generate_password_hash(password)
        self.cursor.execute('''
            INSERT INTO users (name, username, password, description, avatar)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, username, hashed_password, description, avatar))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        r = self.cursor.fetchone()
        if not r:
            return None
        return dict(r)

    def get_user_by_username(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        r = self.cursor.fetchone()
        if not r:
            return None
        return dict(r)

    def verify_password(self, password, hashed_password):
        return check_password_hash(hashed_password, password)

    def add_video(self, name, desc, video_file, thumbnail, author_id):
        self.cursor.execute('''
            INSERT INTO videos (name, desc, video_file, thumbnail, author_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, desc, video_file, thumbnail, author_id))
        self.connection.commit()

    def get_video(self, video_id):
        self.cursor.execute('SELECT videos.*, users.username AS author_username FROM videos JOIN users ON videos.author_id = users.id WHERE videos.id = ?', (video_id,))
        r = self.cursor.fetchone()

        if not r:
            return

        return dict(r)

    def get_videos_by_user(self, user_id):
        self.cursor.execute('SELECT * FROM videos WHERE author_id = ?', (user_id,))
        videos = self.cursor.fetchall()
        return list(map(dict, videos))

    def get_videos(self):
        self.cursor.execute('SELECT videos.*, users.username AS author_username FROM videos JOIN users ON videos.author_id = users.id')
        videos = self.cursor.fetchall()

        videos = list(map(dict, videos))
        videos.sort(key=lambda x: x['likes'] - x['dislikes'], reverse=True)

        return videos

    def like_video(self, video_id, user_id):
        self.cursor.execute('SELECT like_type FROM likes WHERE user_id = ? AND video_id = ?', (user_id, video_id))
        existing_like = self.cursor.fetchone()

        if existing_like:
            like_type = existing_like[0]
            if like_type == 1:
                self.cursor.execute('DELETE FROM likes WHERE user_id = ? AND video_id = ?', (user_id, video_id))
                self.cursor.execute('UPDATE videos SET likes = likes - 1 WHERE id = ?', (video_id,))
            else:
                self.cursor.execute('UPDATE likes SET like_type = 1 WHERE user_id = ? AND video_id = ?', (user_id, video_id))
                self.cursor.execute('UPDATE videos SET likes = likes + 1, dislikes = dislikes - 1 WHERE id = ?', (video_id,))
        else:
            self.cursor.execute('INSERT INTO likes (user_id, video_id, like_type) VALUES (?, ?, 1)', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET likes = likes + 1 WHERE id = ?', (video_id,))

        self.connection.commit()

    def dislike_video(self, video_id, user_id):
        self.cursor.execute('SELECT like_type FROM likes WHERE user_id = ? AND video_id = ?', (user_id, video_id))
        existing_like = self.cursor.fetchone()

        if existing_like:
            like_type = existing_like[0]
            if like_type == -1:
                self.cursor.execute('DELETE FROM likes WHERE user_id = ? AND video_id = ?', (user_id, video_id))
                self.cursor.execute('UPDATE videos SET dislikes = dislikes - 1 WHERE id = ?', (video_id,))
            else:
                self.cursor.execute('UPDATE likes SET like_type = -1 WHERE user_id = ? AND video_id = ?', (user_id, video_id))
                self.cursor.execute('UPDATE videos SET dislikes = dislikes + 1, likes = likes - 1 WHERE id = ?', (video_id,))
        else:
            self.cursor.execute('INSERT INTO likes (user_id, video_id, like_type) VALUES (?, ?, -1)', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes + 1 WHERE id = ?', (video_id,))

        self.connection.commit()

    def subscribe_user(self, subscriber_id, profile_id):
        self.cursor.execute('INSERT INTO subscribers (subscriber_id, profile_id) VALUES (?, ?)',
                            (subscriber_id, profile_id))
        self.connection.commit()

    def unsubscribe_user(self, subscriber_id, profile_id):
        self.cursor.execute('DELETE FROM subscribers WHERE subscriber_id = ? AND profile_id = ?',
                            (subscriber_id, profile_id))
        self.connection.commit()

    def is_subscribed(self, subscriber_id, profile_id):
        self.cursor.execute('SELECT 1 FROM subscribers WHERE subscriber_id = ? AND profile_id = ?',
                            (subscriber_id, profile_id))
        return self.cursor.fetchone() is not None

    def get_subscriber_count(self, profile_id):
        self.cursor.execute('SELECT COUNT(*) FROM subscribers WHERE profile_id = ?', (profile_id,))
        return self.cursor.fetchone()[0]

    def add_comment(self, video_id, user_id, text):
        self.cursor.execute('''
            INSERT INTO comments (video_id, user_id, text)
            VALUES (?, ?, ?)
        ''', (video_id, user_id, text))
        self.connection.commit()

    def get_comments(self, video_id):
        self.cursor.execute('''
            SELECT comments.*, users.username FROM comments
            JOIN users ON comments.user_id = users.id
            WHERE video_id = ?
            ORDER BY created_at DESC
        ''', (video_id,))
        comments = self.cursor.fetchall()
        return list(map(dict, comments))

    def search_videos(self, query):
        query = '%' + query + '%'
        self.cursor.execute('''
            SELECT videos.*, users.username AS author_username
            FROM videos
            JOIN users ON videos.author_id = users.id
            WHERE videos.name LIKE ? OR videos.desc LIKE ? OR users.username LIKE ?
        ''', (query, query, query))
        videos = self.cursor.fetchall()
        return list(map(dict, videos))

if __name__ == '__main__':
    db = Databaser()

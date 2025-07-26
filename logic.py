import sqlite3
import os
import cv2
import numpy as np
from datetime import datetime
from math import sqrt, ceil, floor
from config import DATABASE

class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT,
                    coins INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prizes (
                    prize_id INTEGER PRIMARY KEY,
                    image TEXT,
                    used INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS winners (
                    user_id INTEGER,
                    prize_id INTEGER,
                    win_time TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS missed (
                    user_id INTEGER,
                    prize_id INTEGER
                )
            ''')

    def add_user(self, user_id, user_name):
        with sqlite3.connect(self.database) as conn:
            conn.execute('INSERT OR IGNORE INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name))

    def add_prize(self, data):
        with sqlite3.connect(self.database) as conn:
            conn.executemany('INSERT INTO prizes (image) VALUES (?)', data)

    def add_winner(self, user_id, prize_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchone():
                return False
            win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('INSERT INTO winners VALUES (?, ?, ?)', (user_id, prize_id, win_time))
            cur.execute('UPDATE users SET coins = coins + 10 WHERE user_id = ?', (user_id,))
            return True

    def mark_prize_used(self, prize_id):
        with sqlite3.connect(self.database) as conn:
            conn.execute('UPDATE prizes SET used = 1 WHERE prize_id = ?', (prize_id,))

    def get_users(self):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('SELECT user_id FROM users')
            return [x[0] for x in cur.fetchall()]

    def get_prize_img(self, prize_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('SELECT image FROM prizes WHERE prize_id = ?', (prize_id,))
            return cur.fetchone()[0]

    def get_random_prize(self):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM prizes WHERE used = 0 ORDER BY RANDOM()')
            return cur.fetchone()

    def get_winners_count(self, prize_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id = ?', (prize_id,))
            return cur.fetchone()[0]

    def get_rating(self):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT users.user_name, COUNT(winners.prize_id)
                FROM winners
                INNER JOIN users ON winners.user_id = users.user_id
                GROUP BY winners.user_id
                ORDER BY COUNT(winners.prize_id) DESC
                LIMIT 10
            ''')
            return cur.fetchall()

    def get_winners_img(self, user_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT image FROM winners
                INNER JOIN prizes ON winners.prize_id = prizes.prize_id
                WHERE user_id = ?
            ''', (user_id,))
            return [x[0] for x in cur.fetchall()]

    def get_user_coins(self, user_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def spend_coins(self, user_id, amount):
        coins = self.get_user_coins(user_id)
        if coins >= amount:
            with sqlite3.connect(self.database) as conn:
                conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, user_id))
            return True
        return False

    def add_missed(self, user_id, prize_id):
        with sqlite3.connect(self.database) as conn:
            conn.execute("INSERT INTO missed (user_id, prize_id) VALUES (?, ?)", (user_id, prize_id))

    def get_missed(self, user_id):
        with sqlite3.connect(self.database) as conn:
            cur = conn.cursor()
            cur.execute("SELECT prize_id FROM missed WHERE user_id = ?", (user_id,))
            return [x[0] for x in cur.fetchall()]

    def clear_missed(self, user_id):
        with sqlite3.connect(self.database) as conn:
            conn.execute("DELETE FROM missed WHERE user_id = ?", (user_id,))

def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated = cv2.resize(blurred, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated = cv2.resize(pixelated, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    os.makedirs('hidden_img', exist_ok=True)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated)

def create_collage(image_paths):
    images = [cv2.imread(path) for path in image_paths if cv2.imread(path) is not None]
    if not images:
        return None
    num = len(images)
    cols = floor(sqrt(num))
    rows = ceil(num / cols)
    h, w = images[0].shape[:2]
    collage = np.zeros((rows * h, cols * w, 3), dtype=np.uint8)
    for i, img in enumerate(images):
        r, c = i // cols, i % cols
        collage[r*h:(r+1)*h, c*w:(c+1)*w] = img
    return collage

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    prizes = [(f,) for f in os.listdir('img')]
    manager.add_prize(prizes)

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
import os
from config import *

bot = TeleBot(API_TOKEN)

def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=prize_id))
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать!
Ты успешно зарегистрирован!
Каждую минуту тебе будут приходить новые картинки, и у тебя будет шанс их получить!
Только три первых пользователя получат картинку — успей нажать 'Получить!' первым!""")

@bot.message_handler(commands=['rating'])
def handle_rating(message):
    rating = manager.get_rating()
    if not rating:
        bot.send_message(message.chat.id, "Пока нет данных для рейтинга.")
        return
    header = '| ИМЯ ПОЛЬЗОВАТЕЛЯ | ПОЛУЧЕНО |\n' + '-' * 31
    lines = [f'| @{username:<16}| {count:^9}|' for username, count in rating]
    table = '\n'.join([header] + lines + ['-' * 31])
    bot.send_message(message.chat.id, f"<pre>{table}</pre>", parse_mode="HTML")

@bot.message_handler(commands=['my_score'])
def get_my_score(message):
    user_id = message.chat.id
    won_images = manager.get_winners_img(user_id)
    all_images = os.listdir('img')
    image_paths = [f'img/{x}' if x in won_images else f'hidden_img/{x}' for x in all_images]

    collage = create_collage(image_paths)
    if collage is None:
        bot.send_message(user_id, "У тебя пока нет картинок для коллажа.")
        return

    os.makedirs('temp', exist_ok=True)
    out_path = f"temp/collage_{user_id}.jpg"
    cv2.imwrite(out_path, collage)
    with open(out_path, 'rb') as photo:
        bot.send_photo(user_id, photo, caption="Вот твой коллаж достижений!")
    os.remove(out_path)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    prize_id = call.data
    user_id = call.message.chat.id
    if manager.get_winners_count(prize_id) < 3:
        success = manager.add_winner(user_id, prize_id)
        if success:
            img = manager.get_prize_img(prize_id)
            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравляем! Ты получил картинку! 🎉")
        else:
            bot.send_message(user_id, "Ты уже получал эту картинку!")
    else:
        bot.send_message(user_id, "Увы, три пользователя уже успели получить картинку. Попробуй в следующий раз!")

def send_message():
    prize = manager.get_random_prize()
    if prize:
        prize_id, img = prize[:2]
        manager.mark_prize_used(prize_id)
        hide_img(img)
        for user_id in manager.get_users():
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user_id, photo, reply_markup=gen_markup(prize_id))

def schedule_thread():
    schedule.every(1).minutes.do(send_message)
    while True:
        schedule.run_pending()
        time.sleep(1)

def polling_thread():
    bot.polling(none_stop=True)

if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    threading.Thread(target=polling_thread).start()
    threading.Thread(target=schedule_thread).start()

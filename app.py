import os
import json
import threading
from flask import Flask, render_template, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import telebot.apihelper

app = Flask(__name__)

# Telegram Bot Token එක
BOT_TOKEN = '8513660481:AAGi9Uvwqbw4vYc0ODbPzPy-NERq8jwtt6A'
bot = telebot.TeleBot(BOT_TOKEN)

# ⏳ Timeout සීමා වැඩි කිරීම
telebot.apihelper.CONNECT_TIMEOUT = 60
telebot.apihelper.READ_TIMEOUT = 300

# 🌐 Server URL එක (Render/Cloud Hosting ලබාදුන් පසු මෙය Update කරනු ලැබේ)
BASE_URL = "http://127.0.0.1:5000"

# 📢 Telegram Chat IDs
GROUP_CHAT_ID = -5588131565      # පෝස්ට් යන Telegram Group එක
STORAGE_CHANNEL_ID = -5226449370  # වීඩියෝ Upload කරන Private Storage Channel එක

# වීඩියෝ පිළිබඳ දත්ත සේව් කරන JSON File එක
VIDEO_DB_FILE = "video_db.json"

def load_video_db():
    if os.path.exists(VIDEO_DB_FILE):
        with open(VIDEO_DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_video_db(db):
    with open(VIDEO_DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

# --- CHANNEL EKEN AUTO DETECT KIRIMA ---
@bot.channel_post_handler(content_types=['video'])
def handle_channel_video(message):
    if message.chat.id == STORAGE_CHANNEL_ID:
        video_file_id = message.video.file_id
        thumb_file_id = message.video.thumbnail.file_id if message.video.thumbnail else None
        
        # වීඩියෝවේ Title එක Caption එකෙන් හෝ Default නමකින් ලබා ගැනීම
        title = message.caption if message.caption else f"Video_{message.message_id}"
        
        video_db = load_video_db()
        vid_id = f"vid_{message.message_id}"
        
        video_db[vid_id] = {
            "file_id": video_file_id,
            "thumb_id": thumb_file_id,
            "title": title
        }
        save_video_db(video_db)
        
        print(f"🎬 New Video Saved from Channel: {title}")
        
        # Group එකට Auto Post කිරීම
        bot_username = bot.get_me().username
        bot_deep_link = f"https://t.me/{bot_username}?start={vid_id}"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔓 Watch & Get Video", url=bot_deep_link))
        
        caption_text = f"🔥 **අලුත්ම වීඩියෝවක් එකතු විය!**\n\n🎬 **{title}**\n\n👇 වීඩියෝව ලබා ගැනීමට පහත Button එක ඔබන්න:"
        
        try:
            if thumb_file_id:
                bot.send_photo(
                    chat_id=GROUP_CHAT_ID,
                    photo=thumb_file_id,
                    caption=caption_text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=caption_text,
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
            print("✅ Auto-posted to group successfully!")
        except Exception as e:
            print(f"❌ Error auto-posting to group: {e}")

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = message.text.split()
    chat_id = message.chat.id
    
    video_db = load_video_db()
    
    if len(text) > 1:
        vid_id = text[1]
        if vid_id in video_db:
            unlock_url = f"{BASE_URL}/?vid={vid_id}&user={chat_id}"
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔓 Unlock Video Now", url=unlock_url))
            
            bot.send_message(
                chat_id, 
                f"🎬 **{video_db[vid_id]['title']}** ලබා ගැනීමට පහත Button එක ඔබා Ad එක බලන්න:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

    bot.send_message(chat_id, "👋 **සාදරයෙන් පිළිගනිමු!** Group එකේ ඇති Link එකක් හරහා වීඩියෝ ලබා ගන්න.")

# --- FLASK WEB SERVER LOGIC ---
@app.route('/')
def home():
    vid = request.args.get('vid')
    user_id = request.args.get('user')
    return render_template('index.html', vid=vid, user=user_id)

@app.route('/api/unlock', methods=['POST'])
def unlock_video():
    data = request.json
    vid = data.get('vid')
    user_id = data.get('user')

    video_db = load_video_db()

    if vid in video_db:
        video_data = video_db[vid]
        try:
            # Telegram Storage එකෙන් direct යැවීම
            bot.send_video(
                chat_id=user_id, 
                video=video_data['file_id'], 
                caption=f"🎉 **මෙන්න ඔබ Unlock කළ වීඩියෝව:** {video_data['title']}",
                parse_mode="Markdown",
                timeout=300
            )
            return jsonify({"status": "success", "message": "Video sent successfully!"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    else:
        return jsonify({"status": "error", "message": "Invalid Video ID!"})

def run_bot():
    try:
        bot.remove_webhook()
        bot.infinity_polling(skip_pending=True)
    except Exception as e:
        print(f"Bot polling error: {e}")

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(debug=True, port=5000, use_reloader=False)
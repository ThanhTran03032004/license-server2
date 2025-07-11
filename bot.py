from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, MessageHandler, filters, CallbackContext  # Chú ý import Application và filters
import re, time, json, os, subprocess

BOT_TOKEN = '7685475112:AAEgA7YO5v0HSfDapeI8hcCkM5ju3EHxkmI'
ADMIN_CHAT_ID = 5154548822  # Thay bằng chat_id thật của mày

DATA_FILE = 'activations.json'
pending_mac = {}  # {chat_id: mac}

# ====== JSON Handling ======
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ====== GIT PULL & PUSH tự động ======
def git_pull():
    try:
        subprocess.check_call(['git', 'pull', 'origin', 'main'])
    except subprocess.CalledProcessError as e:
        print("❌ Git pull failed:", e)

def git_push():
    try:
        subprocess.check_call(['git', 'add', DATA_FILE])
        subprocess.check_call(['git', 'commit', '-m', 'Update activation list'])
        subprocess.check_call(['git', 'push'])
    except subprocess.CalledProcessError as e:
        print("❌ Git push failed:", e)

# ====== Bot Logic ======
async def handle_message(update: Update, context: CallbackContext):
    global pending_mac
    text = update.message.text.strip()
    chat_id = update.message.chat_id

    # Chặn người không phải admin
    if chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("🚫 Không có quyền.")
        return

    # Nhận MAC từ client gửi lên
    if "MAC:" in text.upper():
        match = re.search(r'MAC:\s*`?([A-Fa-f0-9]{6,})`?', text)
        if match:
            mac = match.group(1).upper()
            pending_mac[chat_id] = mac
            await update.message.reply_text(
                f"📌 Nhận yêu cầu kích hoạt:\n"
                f"MAC: `{mac}`\n"
                f"Reply với: ACTIVE_1 | ACTIVE_7 | ACTIVE_14 | ACTIVE_30\n"
                f"Để xoá: DELETE",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ Không tìm thấy MAC.")
        return

    # Kích hoạt
    if text.startswith("ACTIVE_"):
        if chat_id not in pending_mac:
            await update.message.reply_text("❌ Không có MAC nào đang chờ kích hoạt.")
            return

        mac = pending_mac[chat_id]
        try:
            days = int(text.split("_")[1])
        except:
            await update.message.reply_text("❌ Cú pháp sai. Dùng ACTIVE_1, ACTIVE_7... hoặc ACTIVE_30.")
            return

        # Kéo dữ liệu từ remote repository trước khi thay đổi
        git_pull()  # Kéo các thay đổi mới nhất từ GitHub

        data = load_data()
        expire_time = int(time.time()) + days * 86400
        data[mac] = expire_time
        save_data(data)
        git_push()  # Đẩy thay đổi lên GitHub

        await update.message.reply_text(
            f"✅ Đã kích hoạt `{mac}` trong {days} ngày.",
            parse_mode=ParseMode.MARKDOWN)
        del pending_mac[chat_id]
        return

    # Xoá MAC nhưng không xóa hết mà giữ lại các dữ liệu khác
    if text.startswith("DELETE"):
        if chat_id not in pending_mac:
            await update.message.reply_text("❌ Không có MAC nào để xoá.")
            return

        mac = pending_mac[chat_id]
        
        # Kéo dữ liệu từ remote repository trước khi thay đổi
        git_pull()  # Kéo các thay đổi mới nhất từ GitHub

        data = load_data()

        # Kiểm tra xem MAC có tồn tại trong dữ liệu hay không
        if mac in data:
            del data[mac]  # Xóa MAC khỏi dữ liệu
            save_data(data)  # Lưu lại dữ liệu sau khi đã xoá
            git_push()  # Đẩy thay đổi lên GitHub
            await update.message.reply_text(f"🗑 Đã xoá `{mac}` khỏi danh sách kích hoạt.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠ MAC chưa được kích hoạt hoặc đã bị xoá.")
        
        del pending_mac[chat_id]  # Xoá MAC khỏi danh sách pending
        return

    # Default
    await update.message.reply_text("🤖 Dùng ACTIVE_1 / ACTIVE_7 / ACTIVE_14 / ACTIVE_30 hoặc DELETE để xử lý MAC.")

# ====== Main Bot ======
def main():
    application = Application.builder().token(BOT_TOKEN).build()  # Sử dụng Application mới cho v20.x
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Thêm handler cho message
    print("🤖 Bot đang chạy...")
    application.run_polling()  # Chạy bot

if __name__ == '__main__':
    main()

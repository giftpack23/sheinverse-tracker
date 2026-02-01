import time
import json
import threading
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import telebot

# --- CONFIGURATION ---
BOT_TOKEN = "8315975028:AAF8wszZMHe4X_fLLM9Q5Z4klFbOolkDlVs"
SHEIN_URL = "https://www.sheinindia.in/c/sverse-5939-37961"
USERS_FILE = "users.json"

# ⚠️ RAILWAY PAR CHALANE KE LIYE ZARURI:
# Apni Telegram Chat ID yahan daalein (Sirf Number).
# Example: 123456789
# Agar nahi daloge to Initial Count ka message nahi milega.
ADMIN_CHAT_ID = None 

# Bot Setup
bot = telebot.TeleBot(BOT_TOKEN)

# --- HELPER FUNCTIONS ---

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def broadcast_message(message_text):
    users = load_users()
    print(f"📢 Broadcasting to {len(users)} users...")
    for uid in users:
        try:
            bot.send_message(uid, message_text)
            time.sleep(0.5) 
        except Exception as e:
            print(f"Error sending to {uid}: {e}")

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    users = load_users()
    user_id = message.chat.id
    if user_id not in users:
        users.append(user_id)
        save_users(users)
        bot.reply_to(message, "✅ Welcome! Sverse Stock Updates Active.")
    else:
        bot.reply_to(message, "Already subscribed! 👍")

@bot.message_handler(commands=['stop'])
def unsubscribe(message):
    users = load_users()
    user_id = message.chat.id
    if user_id in users:
        users.remove(user_id)
        save_users(users)
        bot.reply_to(message, "❌ Unsubscribe ho gaye.")

# --- SCRAPER ---
def scrape_counts(driver):
    men_count = 0
    women_count = 0
    try:
        driver.get(SHEIN_URL)
        time.sleep(3)
        try:
            men_tab = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Men')]")))
            men_tab.click()
            time.sleep(2)
            products = driver.find_elements(By.CLASS_NAME, "S-product-item")
            men_count = len(products)
        except: pass
        try:
            women_tab = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Women')]")))
            women_tab.click()
            time.sleep(2)
            products = driver.find_elements(By.CLASS_NAME, "S-product-item")
            women_count = len(products)
        except: pass
    except Exception as e:
        print(f"Scraping Error: {e}")
    return men_count, women_count

# --- BACKGROUND LOOP ---
def stock_checker():
    print("🚀 Bot Setup ho raha hai...")
    
    # Chrome Options for Railway (Docker)
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # Selenium 4.x automatically manages driver
    driver = webdriver.Chrome(options=chrome_options)
    
    prev_men = 0
    prev_women = 0

    print("🔍 Initial Check kar rahe hoon...")
    time.sleep(10) 
    
    current_men, current_women = scrape_counts(driver)
    print(f"Initial -> Men: {current_men}, Women: {current_women}")
    
    prev_men = current_men
    prev_women = current_women

    if ADMIN_CHAT_ID:
        bot.send_message(ADMIN_CHAT_ID, f"🔥 **BOT STARTED**\n👨 Men: {current_men}\n👩 Women: {current_women}")

    print("⏱️ Loop shuru: Har 30 second mein check hoga.")
    while True:
        try:
            time.sleep(30)
            current_men, current_women = scrape_counts(driver)
            print(f"Check -> Men: {current_men}, Women: {current_women}")

            if current_men > prev_men:
                diff = current_men - prev_men
                msg = f"🚨 NEW STOCK (MEN)\n🛒 +{diff} Added\n👉 Total: {current_men}\n{SHEIN_URL}"
                broadcast_message(msg)
                prev_men = current_men
            elif current_men < prev_men:
                print("Men stock gya, ignore kiya.")
            
            if current_women > prev_women:
                diff = current_women - prev_women
                msg = f"🚨 NEW STOCK (WOMEN)\n🛒 +{diff} Added\n👉 Total: {current_women}\n{SHEIN_URL}"
                broadcast_message(msg)
                prev_women = current_women
            elif current_women < prev_women:
                print("Women stock gya, ignore kiya.")

        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    t = threading.Thread(target=stock_checker)
    t.daemon = True
    t.start()
    print("✅ Telegram Bot Polling shuru...")
    bot.polling(non_stop=True)

"""
Sheinverse Stock Tracker Bot
- Channel verification required
- Auto-checks stock every 15-20 seconds
- Instant alerts on stock changes with product images
- Hourly status updates when no changes
- Tracks Men & Women collections separately
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
import re

# ⚠️ CONFIGURED VALUES
BOT_TOKEN = "8315975028:AAF8wszZMHe4X_fLLM9Q5Z4klFbOolkDlVs"
CHANNEL_ID = -1003605508755
CHANNEL_LINK = "https://t.me/+97wLvWe17YU0NmI1"
ADMIN_USER_ID = 6160310914

# Sheinverse collection URL
SHEINVERSE_URL = "https://www.sheinindia.in/c/sverse-5939-37961"

# Database files
USERS_FILE = "subscribers.json"
STOCK_FILE = "stock_data.json"

# Check interval (seconds)
CHECK_INTERVAL = 17  # 15-20 seconds
HOURLY_UPDATE_INTERVAL = 3600  # 1 hour


def load_users():
    """Load subscribed users"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_users(users):
    """Save subscribed users"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def add_user(user_id):
    """Add user to subscribers"""
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)
        return True
    return False


def remove_user(user_id):
    """Remove user from subscribers"""
    users = load_users()
    if user_id in users:
        users.remove(user_id)
        save_users(users)
        return True
    return False


def load_stock_data():
    """Load previous stock data"""
    if os.path.exists(STOCK_FILE):
        with open(STOCK_FILE, 'r') as f:
            return json.load(f)
    return {
        "women": 0,
        "men": 0,
        "total": 0,
        "last_update": None,
        "last_hourly": None,
        "products": []
    }


def save_stock_data(data):
    """Save current stock data"""
    with open(STOCK_FILE, 'w') as f:
        json.dump(data, f, indent=2)


async def scrape_sheinverse():
    """
    Scrape Sheinverse page for stock counts
    Returns: dict with women_count, men_count, total, and new_products
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(SHEINVERSE_URL, headers=headers, timeout=30) as response:
                html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Parse product data from page
        # Note: This is a placeholder - actual parsing depends on Shein's HTML structure
        # You may need to adjust selectors based on actual page structure
        
        women_count = 0
        men_count = 0
        products = []
        
        # Try to find product elements
        # These selectors are examples - need to be adjusted for actual Shein HTML
        product_items = soup.select('.product-card, .goods-item, [class*="product"]')
        
        for item in product_items[:50]:  # Limit to first 50 for analysis
            try:
                # Detect if men's or women's product
                text = item.get_text().lower()
                
                # Extract product details
                title_elem = item.select_one('.product-title, .goods-title, h3, h4')
                price_elem = item.select_one('.price, .product-price, [class*="price"]')
                link_elem = item.select_one('a[href*="/product"], a[href*="/goods"]')
                img_elem = item.select_one('img')
                
                if 'men' in text or 'man' in text:
                    men_count += 1
                    category = 'men'
                else:
                    women_count += 1
                    category = 'women'
                
                # Extract product info
                if title_elem and link_elem:
                    product = {
                        'title': title_elem.get_text(strip=True)[:100],
                        'price': price_elem.get_text(strip=True) if price_elem else 'N/A',
                        'link': 'https://www.sheinindia.in' + link_elem.get('href', ''),
                        'image': img_elem.get('src', '') if img_elem else '',
                        'category': category
                    }
                    products.append(product)
            except:
                continue
        
        # If no products found with category detection, estimate 50/50
        if women_count == 0 and men_count == 0:
            total_items = len(product_items)
            women_count = total_items // 2
            men_count = total_items - women_count
        
        return {
            'women': women_count,
            'men': men_count,
            'total': women_count + men_count,
            'products': products[:8],  # Keep top 8 products
            'success': True
        }
    
    except Exception as e:
        print(f"Scraping error: {e}")
        return {
            'women': 0,
            'men': 0,
            'total': 0,
            'products': [],
            'success': False,
            'error': str(e)
        }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - channel verification required"""
    user = update.effective_user
    user_id = user.id
    
    # Check if already verified
    users = load_users()
    if user_id in users:
        stock_data = load_stock_data()
        
        status_text = f"""
✅ You're subscribed!

📦 Current Sheinverse Stock:

👗 Women: {stock_data.get('women', 0)}
👔 Men: {stock_data.get('men', 0)}
📈 Total: {stock_data.get('total', 0)}

🔔 You'll receive:
• Instant alerts on stock changes
• Hourly status updates
• New product links with images

Commands:
/status - Check current stock
/stop - Unsubscribe
"""
        await update.message.reply_text(status_text)
        return
    
    # Welcome message
    welcome_text = f"""
🙏 Welcome to Sheinverse Stock Tracker!

Get real-time stock updates from Sheinverse collection!

📊 Features:
• Live stock tracking (Men & Women)
• Instant alerts on new arrivals
• Product images & direct links
• Hourly status updates

To continue, join our channel 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify channel membership"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        
        if member.status in ['member', 'creator', 'administrator']:
            # Add user to subscribers
            add_user(user_id)
            
            # Get current stock
            stock_data = load_stock_data()
            
            success_text = f"""
✅ Verified Successfully!

Welcome {user_name}! 🎉

📦 Current Sheinverse Stock:

👗 Women: {stock_data.get('women', 0)}
👔 Men: {stock_data.get('men', 0)}
📈 Total: {stock_data.get('total', 0)}

🔔 You'll now receive:
• Real-time stock alerts
• New product notifications
• Hourly status updates

Bot is tracking 24/7! 🚀
"""
            await query.edit_message_text(success_text)
            
            # Notify admin
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=f"📊 New subscriber: {user_name} ({user_id})\nTotal: {len(load_users())}"
                )
            except:
                pass
        else:
            not_joined_text = """
❌ You haven't joined the channel yet!

Please join the channel first, then verify. 👇
"""
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ Verify", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(not_joined_text, reply_markup=reply_markup)
    
    except Exception as e:
        error_text = """
⚠️ Verification error!

Please ensure:
1. You've joined the channel
2. Bot is admin in the channel

Try "Verify" again.
"""
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current stock status"""
    user_id = update.effective_user.id
    users = load_users()
    
    if user_id not in users:
        await update.message.reply_text("❌ You're not subscribed! Use /start to subscribe.")
        return
    
    stock_data = load_stock_data()
    
    status_text = f"""
📦 Sheinverse Stock Status

👗 Women: {stock_data.get('women', 0)}
👔 Men: {stock_data.get('men', 0)}
📈 Total: {stock_data.get('total', 0)}

🕐 Last Update: {stock_data.get('last_update', 'Never')}

🔄 Checking every 15-20 seconds...
"""
    await update.message.reply_text(status_text)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from alerts"""
    user_id = update.effective_user.id
    
    if remove_user(user_id):
        await update.message.reply_text(
            "✅ Unsubscribed successfully!\n\n"
            "Use /start to subscribe again."
        )
    else:
        await update.message.reply_text("❌ You weren't subscribed!")


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin stats command"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    users = load_users()
    stock_data = load_stock_data()
    
    stats_text = f"""
👑 Admin Stats

📊 Subscribers: {len(users)}

📦 Current Stock:
👗 Women: {stock_data.get('women', 0)}
👔 Men: {stock_data.get('men', 0)}
📈 Total: {stock_data.get('total', 0)}

🕐 Last Update: {stock_data.get('last_update', 'Never')}
🔄 Checking every {CHECK_INTERVAL}s
"""
    await update.message.reply_text(stats_text)


async def broadcast_stock_change(context: ContextTypes.DEFAULT_TYPE, old_data, new_data):
    """Broadcast stock change to all subscribers"""
    users = load_users()
    
    women_change = new_data['women'] - old_data['women']
    men_change = new_data['men'] - old_data['men']
    total_change = new_data['total'] - old_data['total']
    
    # Format change indicators
    women_indicator = "↗️" if women_change > 0 else "↘️" if women_change < 0 else "➖"
    men_indicator = "↗️" if men_change > 0 else "↘️" if men_change < 0 else "➖"
    total_indicator = "↗️" if total_change > 0 else "↘️" if total_change < 0 else "➖"
    
    alert_text = f"""
🚨 STOCK CHANGED!

👗 Women: {old_data['women']} → {new_data['women']} ({women_change:+d}) {women_indicator}
👔 Men: {old_data['men']} → {new_data['men']} ({men_change:+d}) {men_indicator}

📈 Total: {old_data['total']} → {new_data['total']} ({total_change:+d}) {total_indicator}

⏰ Updated: Just now
"""
    
    # Send to all users
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=alert_text
            )
            
            # Send new product images (if available and stock increased)
            if total_change > 0 and new_data.get('products'):
                products_to_show = new_data['products'][:4]  # Show 2-4 products
                
                if products_to_show:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="🆕 New Products Added:"
                    )
                    
                    for idx, product in enumerate(products_to_show, 1):
                        try:
                            caption = f"{idx}️⃣ {product['title']}\n💰 {product['price']}\n🔗 {product['link']}"
                            
                            if product.get('image'):
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=product['image'],
                                    caption=caption
                                )
                            else:
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=caption
                                )
                            
                            await asyncio.sleep(0.5)  # Small delay between products
                        except:
                            continue
            
            await asyncio.sleep(0.05)  # Small delay between users
        except:
            continue


async def broadcast_hourly_status(context: ContextTypes.DEFAULT_TYPE, stock_data):
    """Broadcast hourly status update"""
    users = load_users()
    
    status_text = f"""
ℹ️ Hourly Status Check

👗 Women: {stock_data['women']} (No change)
👔 Men: {stock_data['men']} (No change)

📈 Total: {stock_data['total']}

🕐 Last checked: Just now
"""
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=status_text
            )
            await asyncio.sleep(0.05)
        except:
            continue


async def stock_monitor_loop(context: ContextTypes.DEFAULT_TYPE):
    """Main loop to monitor stock changes"""
    print("🔄 Stock monitoring started...")
    
    last_hourly_update = datetime.now()
    
    while True:
        try:
            # Scrape current stock
            current_data = await scrape_sheinverse()
            
            if current_data['success']:
                # Load previous data
                previous_data = load_stock_data()
                
                # Check if stock changed
                if (current_data['women'] != previous_data.get('women', 0) or
                    current_data['men'] != previous_data.get('men', 0)):
                    
                    print(f"📊 Stock changed! Women: {current_data['women']}, Men: {current_data['men']}")
                    
                    # Broadcast change
                    await broadcast_stock_change(context, previous_data, current_data)
                    
                    # Update last hourly time
                    last_hourly_update = datetime.now()
                
                # Check if 1 hour passed without changes
                elif (datetime.now() - last_hourly_update).seconds >= HOURLY_UPDATE_INTERVAL:
                    print("🕐 Hourly update - no changes")
                    await broadcast_hourly_status(context, current_data)
                    last_hourly_update = datetime.now()
                
                # Save current data
                current_data['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                current_data['last_hourly'] = last_hourly_update.strftime("%Y-%m-%d %H:%M:%S")
                save_stock_data(current_data)
            
            else:
                print(f"❌ Scraping failed: {current_data.get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ Monitor loop error: {e}")
        
        # Wait before next check
        await asyncio.sleep(CHECK_INTERVAL)


async def post_init(application: Application):
    """Start monitoring after bot initializes"""
    # Start stock monitoring loop
    asyncio.create_task(stock_monitor_loop(application))


def main():
    """Start the bot"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 Sheinverse Stock Tracker Starting...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot Token: Configured")
    print(f"✅ Channel ID: {CHANNEL_ID}")
    print(f"✅ Check Interval: {CHECK_INTERVAL}s")
    print(f"✅ Tracking: {SHEINVERSE_URL}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify$"))
    
    print("✅ Bot Successfully Started! 🎉")
    print("📊 Stock Monitoring: Active")
    print("🔔 Alert System: Active")
    print("📸 Product Images: Active")
    print("\n⚡ Bot is running...")
    print("🛑 Press Ctrl+C to stop\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Run bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

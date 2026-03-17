import os, json, random, datetime, asyncio, time, shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ══════════════════════════════
# CẤU HÌNH
# ══════════════════════════════
TOKEN      = os.environ.get("TOKEN", "")
ADMIN_ID   = 7510588294
SHOP_NAME  = "Vantu Shop"
ADMIN_USER = "chipxgai"

# ══════════════════════════════
# DATABASE
# ══════════════════════════════
DB_FILE = os.environ.get("DB_PATH", "/sdcard/vantu_db.json" if os.path.exists("/sdcard") else "db.json")

SPAM_CACHE = {}

def check_spam(uid):
    uid = str(uid)
    now_ts = time.time()
    SPAM_CACHE[uid] = [t for t in SPAM_CACHE.get(uid, []) if now_ts - t < 10]
    if len(SPAM_CACHE[uid]) >= 5:
        return True
    SPAM_CACHE[uid].append(now_ts)
    return False

def backup_db():
    try:
        if os.path.exists(DB_FILE):
            d = os.path.dirname(DB_FILE) or "."
            bp = os.path.join(d, f"backup_{datetime.datetime.now().strftime('%Y%m%d')}.json")
            shutil.copy2(DB_FILE, bp)
            print(f"✅ Backup: {bp}")
    except Exception as e:
        print(f"Backup error: {e}")

def init_db():
    try:
        d = os.path.dirname(DB_FILE)
        if d: os.makedirs(d, exist_ok=True)
    except: pass

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "users": {}, "orders": [], "cards": [],
        "products": default_products(),
        "vouchers": {}, "settings": default_settings()
    }

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"DB save error: {e}")

def get_user(db, uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": "", "balance": 0, "total_spent": 0,
            "total_deposit": 0, "orders": [], "cards": [],
            "ref_count": 0, "ref_earned": 0, "ref_by": None,
            "joined": now(), "banned": False,
            "spin_today": 0, "dice_today": 0, "last_game_date": "",
            "points": 0, "buy_today": {}, "last_buy_date": "",
            "birthday": "", "ref_code": "",
            "deposit_history": [], "withdraw_history": []
        }
    return db["users"][uid]

def now():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

def today_str():
    return datetime.datetime.now().strftime("%d/%m/%Y")

def get_vip_level(total_spent):
    if total_spent >= 2000000: return ("💎 Kim Cương", 10)
    if total_spent >= 1000000: return ("🥇 Vàng", 7)
    if total_spent >= 500000:  return ("🥈 Bạc", 5)
    if total_spent >= 100000:  return ("🥉 Đồng", 3)
    return ("👤 Thành Viên", 0)

def get_flash_price(p, s):
    if s.get("flash_sale") and s.get("flash_end"):
        try:
            end = datetime.datetime.strptime(s["flash_end"], "%d/%m/%Y %H:%M")
            if datetime.datetime.now() < end:
                pct = s.get("flash_discount", 10)
                return max(0, int(p["price"] * (1 - pct/100))), True
        except: pass
    return p["price"], False

def default_settings():
    return {
        "spin_cost": 5000, "dice_cost": 3000,
        "ref_percent": 10, "withdraw_min": 50000,
        "maintenance": False,
        "welcome_msg": "Xin chào {name}! Chào mừng đến với {shop}!",
        "spin_daily_limit": 10, "dice_daily_limit": 10,
        "low_stock_alert": 3,
        "flash_sale": False, "flash_discount": 10, "flash_end": ""
    }

def default_products():
    return {
        "🎥 Netflix": [
            {"name": "Netflix Premium 4K 1 tháng", "price": 65000, "stock": 10,
             "desc": "4K Ultra HD · Nhiều màn hình", "keys": [], "buy_limit": 0, "ratings": []}
        ],
        "▶️ YouTube Premium": [
            {"name": "YouTube Premium 1 tháng",  "price": 30000,  "stock": 15,
             "desc": "Không quảng cáo · Phát nền", "keys": [], "buy_limit": 0, "ratings": []},
            {"name": "YouTube Premium 6 tháng",  "price": 140000, "stock": 8,
             "desc": "Không quảng cáo · Phát nền", "keys": [], "buy_limit": 0, "ratings": []},
            {"name": "YouTube Premium 12 tháng", "price": 260000, "stock": 5,
             "desc": "Không quảng cáo · Phát nền", "keys": [], "buy_limit": 0, "ratings": []},
        ],
        "🎬 CapCut Pro": [
            {"name": "CapCut Pro 35 Ngày BHF", "price": 26000, "stock": 9,
             "desc": "Full tính năng Pro", "keys": [], "buy_limit": 0, "ratings": []},
            {"name": "CapCut Pro 6 Tháng",     "price": 110000, "stock": 13,
             "desc": "Full tính năng Pro", "keys": [], "buy_limit": 0, "ratings": []},
        ],
        "🤖 ChatGPT Plus": [
            {"name": "ChatGPT Plus Riêng Tư 1 tháng",       "price": 30000, "stock": 12,
             "desc": "Model mạnh nhất", "keys": [], "buy_limit": 0, "ratings": []},
            {"name": "ChatGPT Plus Team Chính Chủ 1 tháng", "price": 50000, "stock": 8,
             "desc": "Chính chủ 100%", "keys": [], "buy_limit": 0, "ratings": []},
        ],
    }

# ══════════════════════════════
# KEYBOARDS
# ══════════════════════════════
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Cửa Hàng MMO",      callback_data="shop"),
         InlineKeyboardButton("📋 Đã Mua",            callback_data="orders")],
        [InlineKeyboardButton("🎡 Vòng Quay",         callback_data="spin"),
         InlineKeyboardButton("🎲 Xúc Xắc",           callback_data="dice"),
         InlineKeyboardButton("🎁 Kiếm Tiền",         callback_data="earn")],
        [InlineKeyboardButton("💳 Quản Lý (Nạp/Rút)", callback_data="wallet"),
         InlineKeyboardButton("📖 HD & CS",            callback_data="guide")],
        [InlineKeyboardButton("💬 Hỗ Trợ & Liên Hệ", callback_data="support"),
         InlineKeyboardButton("❌ Báo Lỗi",            callback_data="report")],
        [InlineKeyboardButton("🔍 Tìm Kiếm SP",       callback_data="search"),
         InlineKeyboardButton("👤 Thống Kê",           callback_data="profile")],
        [InlineKeyboardButton("🎯 Tài Xỉu",           callback_data="taixiu"),
         InlineKeyboardButton("🔢 Đoán Số",            callback_data="guess"),
         InlineKeyboardButton("💎 VIP",                callback_data="vip")],
        [InlineKeyboardButton("👥 Nhóm Cộng Đồng", url=f"https://t.me/{ADMIN_USER}")],
    ])

def kb_shop(products, s):
    rows = []
    flash, _ = s.get("flash_sale", False), s.get("flash_discount", 0)
    flash_txt = f" 🔥-{s.get('flash_discount',0)}%" if s.get("flash_sale") else ""
    for cat, items in products.items():
        total = sum(p["stock"] for p in items)
        label = f"{cat} ({total}){flash_txt}" if total > 0 else f"❌ {cat} - HẾT HÀNG"
        rows.append([InlineKeyboardButton(label, callback_data=f"cat_{cat}")])
    rows.append([InlineKeyboardButton("🏠 Quay lại Main Menu", callback_data="main")])
    return InlineKeyboardMarkup(rows)

def kb_cat(cat, items, s):
    rows = []
    for i, p in enumerate(items):
        flash_price, is_flash = get_flash_price(p, s)
        if p["stock"] > 0:
            price_txt = f"{flash_price//1000}K🔥" if is_flash else f"{p['price']//1000}K"
            label = f"{p['name']} | {price_txt} | Còn {p['stock']}"
        else:
            label = f"❌ {p['name']} | Hết hàng"
        rows.append([InlineKeyboardButton(label, callback_data=f"buy_{cat}_{i}")])
    rows.append([InlineKeyboardButton("🏠 Quay lại Danh Mục", callback_data="shop")])
    return InlineKeyboardMarkup(rows)

def kb_back(target="main", label="🏠 Quay lại"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=target)]])

def kb_wallet():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 Nạp Chuyển Khoản", callback_data="napck")],
        [InlineKeyboardButton("💸 Rút Tiền",          callback_data="withdraw")],
        [InlineKeyboardButton("📊 Lịch Sử Nạp",      callback_data="deposit_history")],
        [InlineKeyboardButton("📊 Lịch Sử Rút",      callback_data="withdraw_history")],
        [InlineKeyboardButton("🏠 Quay lại",          callback_data="main")],
    ])

# ══════════════════════════════
# HANDLERS
# ══════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    s = db.get("settings", default_settings())
    if s.get("maintenance") and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🔧 Hệ thống đang bảo trì. Vui lòng thử lại sau!")
        return
    user = update.effective_user
    u = get_user(db, user.id)
    u["name"] = user.first_name or user.username or "Khách"
    uid = str(user.id)
    if ctx.args and ctx.args[0].startswith("ref_"):
        ref_id = ctx.args[0].replace("ref_", "")
        if ref_id != uid and not u["ref_by"]:
            u["ref_by"] = ref_id
            ref_u = get_user(db, ref_id)
            ref_u["ref_count"] += 1
            try:
                await ctx.bot.send_message(int(ref_id),
                    f"🎉 *{u['name']}* vừa dùng link giới thiệu của bạn!\n💰 Bạn nhận 10% hoa hồng từ mọi đơn!",
                    parse_mode="Markdown")
            except: pass
    # Kiểm tra sinh nhật
    if u.get("birthday") and u["birthday"] == today_str()[:5]:
        await update.message.reply_text(
            f"🎂 Chúc mừng sinh nhật *{u['name']}*! 🎉\nShop tặng bạn voucher BDAY giảm 20k!",
            parse_mode="Markdown")
        db.setdefault("vouchers", {})["BDAY" + uid[-3:]] = {"amount": 20000, "limit": 1, "used": 0}
    save_db(db)
    flash_txt = f"\n🔥 *FLASH SALE -{s.get('flash_discount',0)}%* đang diễn ra!" if s.get("flash_sale") else ""
    welcome = s.get("welcome_msg", "").format(name=u["name"], shop=SHOP_NAME)
    vip_name, _ = get_vip_level(u.get("total_spent", 0))
    text = (
        f"👑 *HỆ THỐNG DỊCH VỤ MMO CAO CẤP* 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*{SHOP_NAME}*{flash_txt}\n\n"
        f"💥 Uy tín - Nhanh gọn - Chuyên nghiệp\n"
        f"⚡ Giao hàng tự động 24/7\n\n"
        f"{welcome}\n"
        f"🏅 Hạng: *{vip_name}* | ⭐ Điểm: *{u.get('points',0)}*\n\n"
        f"✅ *Lựa chọn dịch vụ bên dưới:*"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb_main())


async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    db = load_db()
    user = q.from_user
    u = get_user(db, user.id)
    uid = str(user.id)
    s = db.get("settings", default_settings())

    if u.get("banned") and uid != str(ADMIN_ID):
        await q.answer("❌ Tài khoản bị khóa!", show_alert=True)
        return

    # ── MAIN ──
    if data == "main":
        vip_name, _ = get_vip_level(u.get("total_spent", 0))
        flash_txt = f"\n🔥 *FLASH SALE -{s.get('flash_discount',0)}%* đang diễn ra!" if s.get("flash_sale") else ""
        text = (
            f"👑 *{SHOP_NAME}*{flash_txt}\n\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"🏅 Hạng: *{vip_name}* | ⭐ Điểm: *{u.get('points',0)}*\n\n"
            f"✅ Chọn dịch vụ bên dưới:"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_main())

    # ── CỬA HÀNG ──
    elif data == "shop":
        flash_txt = f"\n🔥 FLASH SALE -{s.get('flash_discount',0)}% toàn bộ!" if s.get("flash_sale") else ""
        await q.edit_message_text(
            f"🛒 *CỬA HÀNG DỊCH VỤ*{flash_txt}\n\nChọn danh mục:",
            parse_mode="Markdown", reply_markup=kb_shop(db["products"], s))

    # ── DANH MỤC ──
    elif data.startswith("cat_"):
        cat = data[4:]
        if cat not in db["products"]:
            await q.edit_message_text("❌ Không tìm thấy!", reply_markup=kb_back("shop"))
            return
        await q.edit_message_text(
            f"📦 *DANH MỤC: {cat}*\n\nChọn sản phẩm:",
            parse_mode="Markdown", reply_markup=kb_cat(cat, db["products"][cat], s))

    # ── CHI TIẾT SẢN PHẨM ──
    elif data.startswith("buy_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], int(parts[2])
        p = db["products"][cat][idx]
        if p["stock"] <= 0:
            await q.answer("❌ Sản phẩm đã hết hàng!", show_alert=True)
            return
        flash_price, is_flash = get_flash_price(p, s)
        vip_name, vip_disc = get_vip_level(u.get("total_spent", 0))
        final_show = int(flash_price * (1 - vip_disc/100)) if vip_disc else flash_price
        ratings = p.get("ratings", [])
        avg_rate = f"{sum(ratings)/len(ratings):.1f}⭐ ({len(ratings)})" if ratings else "Chưa có đánh giá"
        price_line = f"~~{p['price']:,}đ~~ *{flash_price:,}đ* 🔥" if is_flash else f"*{p['price']:,}đ*"
        vip_line = f"\n{vip_name} giảm thêm *{vip_disc}%* → *{final_show:,}đ*" if vip_disc else ""
        key_type = "🔑 Giao key tự động" if p.get("keys") else "📩 Giao thủ công"
        text = (
            f"🛍 *{p['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 {p.get('desc','')}\n"
            f"💰 Giá: {price_line}{vip_line}\n"
            f"📦 Tồn kho: *{p['stock']}*\n"
            f"⭐ {avg_rate}\n"
            f"🚀 {key_type}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💳 Số dư của bạn: *{u['balance']:,}đ*\n"
            f"🎫 Bạn có mã giảm giá? Nhập sau khi xác nhận."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Xác Nhận Mua", callback_data=f"confirm_{cat}_{idx}")],
            [InlineKeyboardButton("🏷 Dùng Mã Giảm Giá", callback_data=f"voucher_{cat}_{idx}")],
            [InlineKeyboardButton("⭐ Xem Đánh Giá", callback_data=f"rating_{cat}_{idx}")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data=f"cat_{cat}")],
        ])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)

    # ── NHẬP MÃ GIẢM GIÁ ──
    elif data.startswith("voucher_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], parts[2]
        ctx.user_data["voucher_for"] = f"{cat}_{idx}"
        ctx.user_data["waiting_voucher"] = True
        await q.edit_message_text(
            "🎫 *NHẬP MÃ GIẢM GIÁ*\n\nGửi mã giảm giá của bạn:",
            parse_mode="Markdown", reply_markup=kb_back(f"buy_{cat}_{idx}", "🔙 Quay lại"))

    # ── XÁC NHẬN MUA ──
    elif data.startswith("confirm_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], int(parts[2])
        p = db["products"][cat][idx]
        if p["stock"] <= 0:
            await q.answer("❌ Hết hàng rồi!", show_alert=True)
            return
        # Kiểm tra giới hạn mua/ngày
        buy_limit = p.get("buy_limit", 0)
        if buy_limit > 0:
            today = today_str()
            if u.get("last_buy_date") != today:
                u["buy_today"] = {}
                u["last_buy_date"] = today
            prod_key = f"{cat}_{idx}"
            bought = u.get("buy_today", {}).get(prod_key, 0)
            if bought >= buy_limit:
                await q.answer(f"❌ Đã mua đủ {buy_limit} lần hôm nay!", show_alert=True)
                return
            u.setdefault("buy_today", {})[prod_key] = bought + 1
        # Tính giá
        discount = ctx.user_data.get(f"discount_{cat}_{idx}", 0)
        flash_price, _ = get_flash_price(p, s)
        _, vip_disc = get_vip_level(u.get("total_spent", 0))
        base = int(flash_price * (1 - vip_disc/100)) if vip_disc else flash_price
        final_price = max(0, base - discount)
        if u["balance"] < final_price:
            shortage = final_price - u["balance"]
            await q.edit_message_text(
                f"❌ *Số dư không đủ!*\n\n💳 Số dư: *{u['balance']:,}đ*\n💰 Giá: *{final_price:,}đ*\n📉 Thiếu: *{shortage:,}đ*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Nạp Tiền", callback_data="wallet")],
                    [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
                ]))
            return
        # Trừ tiền
        u["balance"] -= final_price
        u["total_spent"] += final_price
        p["stock"] -= 1
        # Lấy key tự động
        auto_key = None
        if p.get("keys"):
            auto_key = p["keys"].pop(0)
            p["stock"] = len(p["keys"])
        # Hoa hồng ref
        if u["ref_by"]:
            commission = int(final_price * s.get("ref_percent", 10) / 100)
            if commission > 0:
                ref_u = get_user(db, u["ref_by"])
                ref_u["balance"] += commission
                ref_u["ref_earned"] += commission
                try:
                    await ctx.bot.send_message(int(u["ref_by"]),
                        f"💰 Nhận *{commission:,}đ* hoa hồng từ {u['name']}!",
                        parse_mode="Markdown")
                except: pass
        # Tích điểm
        points_earned = final_price // 10000
        u["points"] = u.get("points", 0) + points_earned
        # Tạo đơn
        order_id = f"VT{len(db['orders'])+1:04d}"
        order = {
            "id": order_id, "user": uid, "username": u["name"],
            "product": p["name"], "price": final_price,
            "original_price": p["price"], "discount": discount,
            "time": now(), "status": "Hoàn thành", "cat": cat,
            "key": auto_key or ""
        }
        db["orders"].append(order)
        u["orders"].append(order_id)
        ctx.user_data.pop(f"discount_{cat}_{idx}", None)
        save_db(db)
        # Cảnh báo sắp hết hàng
        low = s.get("low_stock_alert", 3)
        if 0 < p["stock"] <= low:
            try:
                await ctx.bot.send_message(ADMIN_ID,
                    f"⚠️ *SẮP HẾT HÀNG!*\n📦 {p['name']}\nCòn *{p['stock']}* cái!",
                    parse_mode="Markdown")
            except: pass
        # Thông báo admin
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"🛒 *ĐƠN HÀNG MỚI #{order_id}*\n👤 {u['name']} ({uid})\n📦 {p['name']}\n💰 {final_price:,}đ\n🔑 Key: {auto_key or 'Giao thủ công'}\n🕐 {now()}",
                parse_mode="Markdown")
        except: pass
        key_text = f"\n🔑 *Key của bạn:*\n`{auto_key}`" if auto_key else f"\n📩 Nhắn @{ADMIN_USER} kèm *{order_id}* để nhận hàng!"
        await q.edit_message_text(
            f"✅ *MUA HÀNG THÀNH CÔNG!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *{p['name']}*\n"
            f"💰 Giá: *{final_price:,}đ*\n"
            f"📋 Mã đơn: *{order_id}*\n"
            f"🕐 {now()}\n"
            f"💳 Số dư còn: *{u['balance']:,}đ*\n"
            f"⭐ Điểm nhận: *+{points_earned}* (Tổng: {u['points']})\n"
            f"━━━━━━━━━━━━━━━━━━━━"
            f"{key_text}\n"
            f"⏰ Hỗ trợ 24/7",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Đánh giá 5★", callback_data=f"rate_5_{order_id}"),
                 InlineKeyboardButton("⭐ Đánh giá 4★", callback_data=f"rate_4_{order_id}")],
                [InlineKeyboardButton("🏠 Menu", callback_data="main")],
            ]))

    # ── LỊCH SỬ ĐƠN ──
    elif data == "orders":
        orders = u.get("orders", [])
        if not orders:
            await q.edit_message_text(
                "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n📭 Chưa có đơn hàng nào!",
                parse_mode="Markdown", reply_markup=kb_back())
            return
        rows = []
        for oid in reversed(orders[-15:]):
            o = next((x for x in db["orders"] if x["id"] == oid), None)
            if o:
                icon = "↩️" if o.get("refunded") else "✅"
                label = f"{icon} {o['time'][:10]} | {o['price']//1000}K | {o['product'][:18]}"
                rows.append([InlineKeyboardButton(label, callback_data=f"od_{oid}")])
        rows.append([InlineKeyboardButton("🏠 Quay lại", callback_data="main")])
        await q.edit_message_text(
            "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n👇 Chọn đơn để xem chi tiết:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("od_"):
        oid = data[3:]
        o = next((x for x in db["orders"] if x["id"] == oid), None)
        if not o:
            await q.answer("Không tìm thấy đơn!", show_alert=True)
            return
        disc_txt = f"\n🎫 Giảm: *{o.get('discount',0):,}đ*" if o.get("discount") else ""
        key_txt = f"\n🔑 Key: `{o['key']}`" if o.get("key") else ""
        await q.edit_message_text(
            f"📋 *CHI TIẾT ĐƠN #{o['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {o['product']}\n"
            f"💰 Giá: *{o['price']:,}đ*{disc_txt}\n"
            f"🕐 {o['time']}\n"
            f"✅ {o['status']}{key_txt}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📩 Liên hệ @{ADMIN_USER} nếu chưa nhận được hàng.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Báo Lỗi", callback_data=f"rep_{oid}")],
                [InlineKeyboardButton("🔙 Quay lại", callback_data="orders")],
            ]))

    # ── VÍ TIỀN ──
    elif data == "wallet":
        await q.edit_message_text(
            f"💳 *QUẢN LÝ TÀI KHOẢN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Số dư: *{u['balance']:,}đ*\n"
            f"📊 Tổng nạp: *{u.get('total_deposit',0):,}đ*\n"
            f"🛍 Tổng chi: *{u['total_spent']:,}đ*",
            parse_mode="Markdown", reply_markup=kb_wallet())

    # ── LỊCH SỬ NẠP/RÚT ──
    elif data == "deposit_history":
        hist = u.get("deposit_history", [])
        if not hist:
            await q.edit_message_text(
                "📊 *LỊCH SỬ NẠP TIỀN*\n\n📭 Chưa có lịch sử!",
                parse_mode="Markdown", reply_markup=kb_back("wallet"))
            return
        text = "📊 *LỊCH SỬ NẠP TIỀN*\n━━━━━━━━━━━━━━━━━━━━\n"
        for c in reversed(hist[-15:]):
            text += f"✅ {c['time']} | +{c['amount']:,}đ\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back("wallet"))

    elif data == "withdraw_history":
        hist = u.get("withdraw_history", [])
        if not hist:
            await q.edit_message_text(
                "📊 *LỊCH SỬ RÚT TIỀN*\n\n📭 Chưa có lịch sử!",
                parse_mode="Markdown", reply_markup=kb_back("wallet"))
            return
        text = "📊 *LỊCH SỬ RÚT TIỀN*\n━━━━━━━━━━━━━━━━━━━━\n"
        for w in reversed(hist[-15:]):
            icon = "✅" if w.get("status") == "done" else "⏳"
            text += f"{icon} {w['time']} | -{w['amount']:,}đ\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back("wallet"))

    # ── NẠP CHUYỂN KHOẢN ──
    elif data == "napck":
        await q.edit_message_text(
            f"🏦 *NẠP TIỀN CHUYỂN KHOẢN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📲 Liên hệ Admin: @{ADMIN_USER}\n\n"
            f"Nội dung chuyển khoản:\n`NAP {uid}`\n\n"
            f"Admin sẽ cộng tiền trong vòng 5 phút!",
            parse_mode="Markdown", reply_markup=kb_back("wallet"))

    # ── RÚT TIỀN ──
    elif data == "withdraw":
        min_wd = s.get("withdraw_min", 50000)
        if u["balance"] < min_wd:
            await q.answer(f"❌ Cần ít nhất {min_wd:,}đ để rút!", show_alert=True)
            return
        ctx.user_data["waiting_withdraw"] = True
        await q.edit_message_text(
            f"💸 *RÚT TIỀN*\n\n💳 Số dư: *{u['balance']:,}đ*\n📉 Tối thiểu: *{min_wd:,}đ*\n\nGửi số tiền muốn rút:",
            parse_mode="Markdown", reply_markup=kb_back("wallet"))

    # ── VÒNG QUAY ──
    elif data == "spin":
        cost = s.get("spin_cost", 5000)
        daily_limit = s.get("spin_daily_limit", 10)
        today = today_str()
        if u.get("last_game_date") != today:
            u["spin_today"] = 0
            u["dice_today"] = 0
            u["last_game_date"] = today
        if u.get("spin_today", 0) >= daily_limit:
            await q.answer(f"❌ Hết lượt quay hôm nay! Giới hạn {daily_limit} lần/ngày.", show_alert=True)
            return
        if u["balance"] < cost:
            await q.answer(f"❌ Cần {cost:,}đ để quay!", show_alert=True)
            return
        u["spin_today"] = u.get("spin_today", 0) + 1
        prizes = [
            ("🎰 JACKPOT 200K!", 200000, 1),
            ("💎 Trúng 100K!",   100000, 2),
            ("🥇 Trúng 50K!",    50000,  5),
            ("🎉 Trúng 20K!",    20000,  10),
            ("⭐ Trúng 10K!",    10000,  15),
            ("✨ Hoàn lại 5K",   5000,   17),
            ("😢 Không trúng",   0,      50),
        ]
        roll = random.randint(1, 100)
        cum = 0
        result_txt, prize = "😢 Không trúng", 0
        for txt, amt, chance in prizes:
            cum += chance
            if roll <= cum:
                result_txt, prize = txt, amt
                break
        u["balance"] = u["balance"] - cost + prize
        luot_con = daily_limit - u.get("spin_today", 0)
        save_db(db)
        await q.edit_message_text(
            f"🎡 *VÒNG QUAY MAY MẮN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎰 Kết quả: *{result_txt}*\n"
            f"{'💰 Nhận: *'+f'{prize:,}đ*' if prize > 0 else f'💸 Mất: *{cost:,}đ*'}\n\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"🔄 Lượt còn hôm nay: *{luot_con}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎡 Quay Tiếp ({cost//1000}K)", callback_data="spin")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    # ── XÚC XẮC ──
    elif data == "dice":
        cost = s.get("dice_cost", 3000)
        daily_limit = s.get("dice_daily_limit", 10)
        today = today_str()
        if u.get("last_game_date") != today:
            u["spin_today"] = 0
            u["dice_today"] = 0
            u["last_game_date"] = today
        if u.get("dice_today", 0) >= daily_limit:
            await q.answer(f"❌ Hết lượt chơi hôm nay!", show_alert=True)
            return
        if u["balance"] < cost:
            await q.answer(f"❌ Cần {cost:,}đ để chơi!", show_alert=True)
            return
        u["dice_today"] = u.get("dice_today", 0) + 1
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2
        if total >= 10:
            prize = cost * 3
            result = f"🎉 *THẮNG!* Tổng {total} → Nhận *{prize:,}đ*"
        elif total >= 7:
            prize = cost
            result = f"😊 *Hoà!* Tổng {total} → Nhận lại *{prize:,}đ*"
        else:
            prize = 0
            result = f"😢 *Thua!* Tổng {total} → Mất *{cost:,}đ*"
        u["balance"] = u["balance"] - cost + prize
        luot_con = daily_limit - u.get("dice_today", 0)
        save_db(db)
        await q.edit_message_text(
            f"🎲 *XÚC XẮC*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎲 {d1}  +  🎲 {d2}  =  *{total}*\n\n"
            f"{result}\n\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"🔄 Lượt còn hôm nay: *{luot_con}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎲 Chơi Tiếp ({cost//1000}K)", callback_data="dice")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    # ── TÀI XỈU ──
    elif data == "taixiu":
        cost = s.get("dice_cost", 3000)
        await q.edit_message_text(
            f"🎯 *TÀI XỈU*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Cược: *{cost:,}đ* | Thắng 2x\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n\n"
            f"Tổng 3 xúc xắc:\n"
            f"• *Tài* (11-18) → Thắng 2x\n"
            f"• *Xỉu* (3-10) → Thắng 2x\n\n"
            f"Chọn:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 TÀI", callback_data="taichon_tai"),
                 InlineKeyboardButton("🔵 XỈU", callback_data="taichon_xiu")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    elif data.startswith("taichon_"):
        choice = data.split("_")[1]
        cost = s.get("dice_cost", 3000)
        if u["balance"] < cost:
            await q.answer(f"❌ Không đủ tiền! Cần {cost:,}đ", show_alert=True)
            return
        d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
        total = d1 + d2 + d3
        result_type = "tai" if total >= 11 else "xiu"
        win = choice == result_type
        prize = cost * 2 if win else 0
        u["balance"] = u["balance"] - cost + prize
        save_db(db)
        result_txt = "🔴 TÀI" if result_type == "tai" else "🔵 XỈU"
        await q.edit_message_text(
            f"🎯 *TÀI XỈU*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎲 {d1}+{d2}+{d3} = *{total}* → {result_txt}\n\n"
            f"{'🎉 *THẮNG!* Nhận *'+f'{prize:,}đ*' if win else '😢 *Thua!* Mất *'+f'{cost:,}đ*'}\n"
            f"💳 Số dư: *{u['balance']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 TÀI", callback_data="taichon_tai"),
                 InlineKeyboardButton("🔵 XỈU", callback_data="taichon_xiu")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    # ── ĐOÁN SỐ ──
    elif data == "guess":
        cost = s.get("dice_cost", 3000)
        if u["balance"] < cost:
            await q.answer(f"❌ Cần {cost:,}đ để chơi!", show_alert=True)
            return
        num = random.randint(1, 10)
        ctx.user_data["guess_number"] = num
        ctx.user_data["guess_cost"] = cost
        ctx.user_data["waiting_guess"] = True
        await q.edit_message_text(
            f"🔢 *ĐOÁN SỐ*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Cược: *{cost:,}đ*\n"
            f"🏆 Thắng: *{cost*8:,}đ* (8x)\n\n"
            f"Mình đang nghĩ 1 số từ 1-10\nBạn đoán xem là số mấy?\n\nGõ số vào chat:",
            parse_mode="Markdown", reply_markup=kb_back())

    # ── KIẾM TIỀN ──
    elif data == "earn":
        ref_link = f"https://t.me/{ctx.bot.username}?start=ref_{uid}"
        ref_code = u.get("ref_code") or f"REF{uid[-4:]}"
        pct = s.get("ref_percent", 10)
        await q.edit_message_text(
            f"🎁 *CHƯƠNG TRÌNH ĐỐI TÁC*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Giới thiệu bạn bè nhận *{pct}% hoa hồng*!\n\n"
            f"🔗 *Link của bạn:*\n`{ref_link}`\n\n"
            f"📊 Đã mời: *{u['ref_count']} người*\n"
            f"💰 Đã kiếm: *{u['ref_earned']:,}đ*\n"
            f"💳 Số dư: *{u['balance']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 Top Giới Thiệu", callback_data="top_ref")],
                [InlineKeyboardButton("🔗 Đặt Mã Ref Riêng", callback_data="set_refcode")],
                [InlineKeyboardButton("💸 Rút Tiền",         callback_data="withdraw")],
                [InlineKeyboardButton("🏠 Quay lại",         callback_data="main")],
            ]))

    # ── TOP ──
    elif data in ("top_deposit", "top_ref"):
        if data == "top_deposit":
            users = [(u2["name"], u2.get("total_deposit",0)) for u2 in db["users"].values() if u2.get("total_deposit",0)>0]
            title = "🏆 TOP NẠP TIỀN"
            suffix = "đ"
        else:
            users = [(u2["name"], u2.get("ref_count",0)) for u2 in db["users"].values() if u2.get("ref_count",0)>0]
            title = "🏆 TOP GIỚI THIỆU"
            suffix = " người"
        users.sort(key=lambda x: x[1], reverse=True)
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        text = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, val) in enumerate(users[:10]):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            text += f"{medal} {name}: *{val:,}{suffix}*\n"
        if not users:
            text += "Chưa có dữ liệu!"
        await q.edit_message_text(text, parse_mode="Markdown",
            reply_markup=kb_back("earn" if data=="top_ref" else "main"))

    # ── THỐNG KÊ CÁ NHÂN ──
    elif data == "profile":
        vip_name, vip_disc = get_vip_level(u.get("total_spent", 0))
        await q.edit_message_text(
            f"📊 *THỐNG KÊ CÁ NHÂN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Tên: *{u['name']}*\n"
            f"🆔 ID: `{uid}`\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"🏅 VIP: *{vip_name}* (Giảm {vip_disc}%)\n"
            f"⭐ Điểm: *{u.get('points',0)}*\n"
            f"📅 Tham gia: *{u['joined']}*\n\n"
            f"🛍 Tổng chi: *{u['total_spent']:,}đ* ({len(u['orders'])} đơn)\n"
            f"💵 Tổng nạp: *{u.get('total_deposit',0):,}đ*\n\n"
            f"👥 Đã giới thiệu: *{u['ref_count']} người*\n"
            f"💰 Hoa hồng: *{u['ref_earned']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Xem VIP",        callback_data="vip")],
                [InlineKeyboardButton("🎁 Đổi Điểm",       callback_data="redeem")],
                [InlineKeyboardButton("🎂 Cài Sinh Nhật",  callback_data="set_birthday")],
                [InlineKeyboardButton("🏆 Top Nạp",        callback_data="top_deposit")],
                [InlineKeyboardButton("🏠 Quay lại",       callback_data="main")],
            ]))

    # ── VIP ──
    elif data == "vip":
        vip_name, vip_disc = get_vip_level(u.get("total_spent", 0))
        points = u.get("points", 0)
        levels = [
            ("👤 Thành Viên", 0, "0đ"),
            ("🥉 Đồng", 3, "100,000đ"),
            ("🥈 Bạc", 5, "500,000đ"),
            ("🥇 Vàng", 7, "1,000,000đ"),
            ("💎 Kim Cương", 10, "2,000,000đ"),
        ]
        level_txt = ""
        for lname, ldisc, lreq in levels:
            mark = "▶️" if lname == vip_name else "  "
            level_txt += f"{mark} {lname} — Giảm {ldisc}% (Chi {lreq})\n"
        await q.edit_message_text(
            f"💎 *HỆ THỐNG VIP*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Hạng hiện tại: *{vip_name}*\n"
            f"Giảm giá VIP: *{vip_disc}%*\n"
            f"⭐ Điểm: *{points}*\n"
            f"🛍 Tổng chi: *{u.get('total_spent',0):,}đ*\n\n"
            f"*Các hạng VIP:*\n{level_txt}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Đổi Điểm", callback_data="redeem")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    # ── ĐỔI ĐIỂM ──
    elif data == "redeem":
        points = u.get("points", 0)
        await q.edit_message_text(
            f"🎁 *ĐỔI ĐIỂM*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⭐ Điểm hiện có: *{points} điểm*\n\n"
            f"• 10 điểm = 10,000đ\n"
            f"• 50 điểm = 55,000đ (+5K bonus)\n"
            f"• 100 điểm = 120,000đ (+20K bonus)\n\n"
            f"Chọn mức đổi:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("10đ → 10K", callback_data="redeem_10"),
                 InlineKeyboardButton("50đ → 55K", callback_data="redeem_50"),
                 InlineKeyboardButton("100đ → 120K", callback_data="redeem_100")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

    elif data.startswith("redeem_"):
        amt = int(data.split("_")[1])
        rewards = {10: 10000, 50: 55000, 100: 120000}
        reward = rewards.get(amt, 0)
        if u.get("points", 0) < amt:
            await q.answer(f"❌ Không đủ điểm! Cần {amt} điểm.", show_alert=True)
            return
        u["points"] = u.get("points", 0) - amt
        u["balance"] += reward
        save_db(db)
        await q.edit_message_text(
            f"✅ Đổi *{amt} điểm* thành công!\n💰 Nhận: *{reward:,}đ*\n💳 Số dư: *{u['balance']:,}đ*",
            parse_mode="Markdown", reply_markup=kb_back())

    # ── ĐÁNH GIÁ ──
    elif data.startswith("rating_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], int(parts[2])
        p = db["products"][cat][idx]
        ratings = p.get("ratings", [])
        if not ratings:
            text = f"⭐ *{p['name']}*\n\nChưa có đánh giá nào!"
        else:
            avg = sum(ratings)/len(ratings)
            text = f"⭐ *{p['name']}*\n━━━━━━━━━━━━━━━━━━━━\n⭐ Điểm TB: *{avg:.1f}/5* ({len(ratings)} đánh giá)"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back(f"buy_{cat}_{idx}"))

    elif data.startswith("rate_"):
        parts = data.split("_")
        stars, oid = int(parts[1]), parts[2]
        o = next((x for x in db["orders"] if x["id"] == oid), None)
        if o and not o.get("rated"):
            for c, items in db["products"].items():
                for i, item in enumerate(items):
                    if item["name"] == o["product"]:
                        db["products"][c][i].setdefault("ratings", []).append(stars)
                        break
            o["rated"] = True
            save_db(db)
            await q.edit_message_text(f"✅ Cảm ơn bạn đã đánh giá *{stars}⭐*!", parse_mode="Markdown", reply_markup=kb_back())
        else:
            await q.answer("Bạn đã đánh giá rồi!", show_alert=True)

    # ── TÌM KIẾM ──
    elif data == "search":
        ctx.user_data["waiting_search"] = True
        await q.edit_message_text(
            "🔍 *TÌM KIẾM SẢN PHẨM*\n\nGõ tên sản phẩm cần tìm:",
            parse_mode="Markdown", reply_markup=kb_back())

    # ── SINH NHẬT ──
    elif data == "set_birthday":
        ctx.user_data["waiting_birthday"] = True
        await q.edit_message_text(
            "🎂 *CÀI SINH NHẬT*\n\nGửi ngày sinh theo định dạng:\n`DD/MM`\n\nVí dụ: `15/03`",
            parse_mode="Markdown", reply_markup=kb_back("profile"))

    # ── MÃ GIỚI THIỆU ──
    elif data == "set_refcode":
        ctx.user_data["waiting_refcode"] = True
        await q.edit_message_text(
            "🔗 *CÀI MÃ GIỚI THIỆU*\n\nTạo mã ngắn gọn của bạn:\n_(4-10 ký tự, không dấu, không khoảng trắng)_",
            parse_mode="Markdown", reply_markup=kb_back("earn"))

    # ── HỖ TRỢ ──
    elif data == "support":
        ctx.user_data["live_chat"] = True
        await q.edit_message_text(
            f"💬 *LIVE CHAT VỚI ADMIN*\n\n📩 Gửi tin nhắn bên dưới!\n📞 Hoặc liên hệ: @{ADMIN_USER}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Đóng Chat", callback_data="close_chat")],
                [InlineKeyboardButton("🏠 Quay lại",  callback_data="main")],
            ]))

    elif data == "close_chat":
        ctx.user_data["live_chat"] = False
        await q.edit_message_text("✅ Đã đóng chat.", reply_markup=kb_back())

    # ── BÁO LỖI ──
    elif data == "report":
        await q.edit_message_text(
            f"🔧 *BÁO LỖI*\n\n1️⃣ Chọn *Đã Mua*\n2️⃣ Chọn đơn hàng\n3️⃣ Bấm *Báo Lỗi Đơn Này*\n\nHoặc nhắn @{ADMIN_USER}",
            parse_mode="Markdown", reply_markup=kb_back())

    elif data.startswith("rep_"):
        oid = data[4:]
        ctx.user_data["report_order"] = oid
        ctx.user_data["waiting_report"] = True
        await q.edit_message_text(
            f"⚠️ *BÁO LỖI ĐƠN #{oid}*\n\nMô tả ngắn gọn vấn đề:",
            parse_mode="Markdown", reply_markup=kb_back("orders"))

    # ── HƯỚNG DẪN ──
    elif data == "guide":
        await q.edit_message_text(
            f"📖 *HƯỚNG DẪN & CHÍNH SÁCH*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛒 *Cách mua hàng:*\n"
            f"1. Chọn Cửa Hàng MMO\n"
            f"2. Chọn sản phẩm → Xác nhận\n"
            f"3. Nhận key tự động hoặc nhắn @{ADMIN_USER}\n\n"
            f"💳 *Nạp tiền:*\n"
            f"• Chuyển khoản: Nhắn @{ADMIN_USER}\n\n"
            f"💎 *VIP:* Mua nhiều lên hạng, giảm giá thêm\n"
            f"⭐ *Điểm:* 10k chi = 1 điểm, đổi tiền mặt\n"
            f"🔄 *Bảo hành:* 30 ngày\n"
            f"❓ *Hỗ trợ:* @{ADMIN_USER} - 24/7",
            parse_mode="Markdown", reply_markup=kb_back())

    save_db(db)


# ══════════════════════════════
# XỬ LÝ TIN NHẮN
# ══════════════════════════════
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    user = update.effective_user
    u = get_user(db, user.id)
    uid = str(user.id)
    text = update.message.text or ""

    # Spam check
    if check_spam(user.id) and user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bạn gửi quá nhanh! Vui lòng chờ vài giây.")
        return

    # ── LIVE CHAT ──
    if ctx.user_data.get("live_chat"):
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"💬 *LIVE CHAT*\n👤 {u['name']} ({uid}):\n{text}",
                parse_mode="Markdown")
            await update.message.reply_text("✅ Đã gửi! Đang chờ Admin phản hồi...")
        except:
            await update.message.reply_text("❌ Lỗi gửi tin!")
        return

    # ── BÁO LỖI ──
    if ctx.user_data.get("waiting_report"):
        oid = ctx.user_data.get("report_order", "")
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"⚠️ *BÁO LỖI ĐƠN #{oid}*\n👤 {u['name']} ({uid}):\n{text}",
                parse_mode="Markdown")
        except: pass
        ctx.user_data["waiting_report"] = False
        await update.message.reply_text(
            "✅ Đã gửi báo lỗi! Admin xử lý sớm nhất.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main")]]))
        return

    # ── TÌM KIẾM ──
    if ctx.user_data.get("waiting_search"):
        ctx.user_data["waiting_search"] = False
        keyword = text.strip().lower()
        results = []
        for cat, items in db["products"].items():
            for i, p in enumerate(items):
                if keyword in p["name"].lower() or keyword in p.get("desc","").lower():
                    results.append((cat, i, p))
        if not results:
            await update.message.reply_text(
                f"🔍 Không tìm thấy sản phẩm nào với '*{text}*'",
                parse_mode="Markdown", reply_markup=kb_back())
            return
        rows = []
        for cat, i, p in results[:10]:
            label = f"{'✅' if p['stock']>0 else '❌'} {p['name']} | {p['price']//1000}K"
            rows.append([InlineKeyboardButton(label, callback_data=f"buy_{cat}_{i}")])
        rows.append([InlineKeyboardButton("🏠 Quay lại", callback_data="main")])
        await update.message.reply_text(
            f"🔍 Tìm thấy *{len(results)}* sản phẩm:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))
        return

    # ── SINH NHẬT ──
    if ctx.user_data.get("waiting_birthday"):
        ctx.user_data["waiting_birthday"] = False
        bday = text.strip()
        try:
            datetime.datetime.strptime(bday, "%d/%m")
            u["birthday"] = bday
            save_db(db)
            await update.message.reply_text(
                f"🎂 Đã lưu sinh nhật *{bday}*!\nBot sẽ tặng voucher vào ngày sinh nhật của bạn!",
                parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ Sai định dạng! Gửi dạng DD/MM, ví dụ: 15/03")
        return

    # ── MÃ GIỚI THIỆU ──
    if ctx.user_data.get("waiting_refcode"):
        ctx.user_data["waiting_refcode"] = False
        code = text.strip().upper()
        if 4 <= len(code) <= 10 and code.isalnum():
            # Kiểm tra trùng
            used = any(u2.get("ref_code") == code for u2 in db["users"].values())
            if used:
                await update.message.reply_text("❌ Mã này đã được dùng! Chọn mã khác.")
            else:
                u["ref_code"] = code
                save_db(db)
                await update.message.reply_text(
                    f"✅ Mã giới thiệu của bạn: *{code}*",
                    parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Mã phải 4-10 ký tự, chỉ chữ và số!")
        return

    # ── ĐOÁN SỐ ──
    if ctx.user_data.get("waiting_guess"):
        ctx.user_data["waiting_guess"] = False
        num = ctx.user_data.get("guess_number", 0)
        cost = ctx.user_data.get("guess_cost", 3000)
        try:
            guess = int(text.strip())
            if u["balance"] < cost:
                await update.message.reply_text(f"❌ Không đủ tiền!")
                return
            if guess == num:
                prize = cost * 8
                u["balance"] = u["balance"] - cost + prize
                save_db(db)
                await update.message.reply_text(
                    f"🎉 *ĐÚNG RỒI!* Số là *{num}*\n💰 Nhận: *{prize:,}đ*\n💳 Số dư: *{u['balance']:,}đ*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔢 Chơi tiếp", callback_data="guess"), InlineKeyboardButton("🏠 Menu", callback_data="main")]]))
            else:
                u["balance"] -= cost
                save_db(db)
                await update.message.reply_text(
                    f"😢 *Sai rồi!* Số là *{num}*, bạn đoán *{guess}*\n💸 Mất: *{cost:,}đ*\n💳 Số dư: *{u['balance']:,}đ*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔢 Chơi tiếp", callback_data="guess"), InlineKeyboardButton("🏠 Menu", callback_data="main")]]))
        except:
            await update.message.reply_text("❌ Gõ số từ 1-10!")
        return

    # ── MÃ GIẢM GIÁ ──
    if ctx.user_data.get("waiting_voucher"):
        voucher_key = text.strip().upper()
        target = ctx.user_data.get("voucher_for", "")
        vouchers = db.get("vouchers", {})
        if voucher_key in vouchers:
            v = vouchers[voucher_key]
            if v.get("used", 0) >= v.get("limit", 999):
                await update.message.reply_text("❌ Mã giảm giá đã hết lượt!")
            else:
                discount = v["amount"]
                ctx.user_data[f"discount_{target}"] = discount
                v["used"] = v.get("used", 0) + 1
                save_db(db)
                await update.message.reply_text(
                    f"✅ Áp dụng mã *{voucher_key}*!\n💰 Giảm: *{discount:,}đ*",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Xác Nhận Mua", callback_data=f"confirm_{target}")
                    ]]))
        else:
            await update.message.reply_text("❌ Mã không hợp lệ hoặc đã hết hạn!")
        ctx.user_data["waiting_voucher"] = False
        return

    # ── RÚT TIỀN ──
    if ctx.user_data.get("waiting_withdraw"):
        try:
            amount = int(text.strip())
            min_wd = db.get("settings",{}).get("withdraw_min", 50000)
            if amount < min_wd:
                await update.message.reply_text(f"❌ Tối thiểu {min_wd:,}đ!")
                return
            if amount > u["balance"]:
                await update.message.reply_text(f"❌ Số dư không đủ! Có: {u['balance']:,}đ")
                return
            ctx.user_data["waiting_withdraw"] = False
            u.setdefault("withdraw_history", []).append({"amount": amount, "time": now(), "status": "pending"})
            save_db(db)
            try:
                await ctx.bot.send_message(ADMIN_ID,
                    f"💸 *YÊU CẦU RÚT TIỀN*\n👤 {u['name']} ({uid})\n💰 {amount:,}đ\n🕐 {now()}",
                    parse_mode="Markdown")
            except: pass
            await update.message.reply_text(
                f"✅ Yêu cầu rút *{amount:,}đ* đã gửi!\nAdmin xử lý trong 24h.",
                parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Nhập số tiền hợp lệ!")
        return

    # ── ADMIN REPLY LIVE CHAT ──
    if user.id == ADMIN_ID and update.message.reply_to_message:
        rep = update.message.reply_to_message.text or ""
        if "LIVE CHAT" in rep or "BÁO LỖI" in rep:
            for line in rep.split("\n"):
                if "(" in line and ")" in line:
                    try:
                        target_id = line.split("(")[1].split(")")[0]
                        await ctx.bot.send_message(int(target_id),
                            f"📩 *Admin ({now()}):*\n{text}", parse_mode="Markdown")
                        await update.message.reply_text("✅ Đã gửi!")
                        return
                    except: pass

    save_db(db)
    await update.message.reply_text(
        "❓ Dùng /start để mở menu!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Mở Menu", callback_data="main")]]))


# ══════════════════════════════
# ADMIN COMMANDS
# ══════════════════════════════
async def addmoney(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        tid, amt = ctx.args[0], int(ctx.args[1])
        db = load_db()
        u = get_user(db, tid)
        u["balance"] += amt
        u["total_deposit"] = u.get("total_deposit", 0) + amt
        u.setdefault("deposit_history", []).append({"amount": amt, "time": now(), "type": "admin"})
        save_db(db)
        await update.message.reply_text(f"✅ Cộng *{amt:,}đ* cho {tid}", parse_mode="Markdown")
        try:
            await ctx.bot.send_message(int(tid),
                f"💰 Tài khoản được cộng *{amt:,}đ*!\n💳 Số dư: *{u['balance']:,}đ*",
                parse_mode="Markdown")
        except: pass
    except:
        await update.message.reply_text("❌ /addmoney <user_id> <số_tiền>")

async def removemoney(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        tid, amt = ctx.args[0], int(ctx.args[1])
        db = load_db()
        u = get_user(db, tid)
        u["balance"] = max(0, u["balance"] - amt)
        save_db(db)
        await update.message.reply_text(f"✅ Trừ *{amt:,}đ* của {tid}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /removemoney <user_id> <số_tiền>")

async def addproduct(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat = ctx.args[0]
        price = int(ctx.args[-2])
        stock = int(ctx.args[-1])
        name = " ".join(ctx.args[1:-2])
        db = load_db()
        if cat not in db["products"]:
            db["products"][cat] = []
        db["products"][cat].append({"name": name, "price": price, "stock": stock, "desc": "", "keys": [], "buy_limit": 0, "ratings": []})
        save_db(db)
        await update.message.reply_text(f"✅ Đã thêm: *{name}* | {price:,}đ | Stock: {stock}", parse_mode="Markdown")
        # Thông báo tất cả users
        for uid2 in list(db["users"].keys()):
            try:
                await ctx.bot.send_message(int(uid2),
                    f"🆕 *SẢN PHẨM MỚI!*\n📦 {name}\n💰 {price:,}đ\n🛒 Mua ngay: /start",
                    parse_mode="Markdown")
                await asyncio.sleep(0.05)
            except: pass
    except:
        await update.message.reply_text("❌ /addproduct <cat> <tên> <giá> <stock>")

async def deleteproduct(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx = ctx.args[0], int(ctx.args[1])
        db = load_db()
        p = db["products"][cat][idx]
        db["products"][cat].pop(idx)
        save_db(db)
        await update.message.reply_text(f"✅ Đã xóa *{p['name']}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /deleteproduct <cat> <index>")

async def addstock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx, qty = ctx.args[0], int(ctx.args[1]), int(ctx.args[2])
        db = load_db()
        db["products"][cat][idx]["stock"] += qty
        save_db(db)
        p = db["products"][cat][idx]
        await update.message.reply_text(f"✅ Thêm {qty} stock cho *{p['name']}*\nTổng: {p['stock']}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /addstock <cat> <index> <qty>")

async def setprice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx, price = ctx.args[0], int(ctx.args[1]), int(ctx.args[2])
        db = load_db()
        db["products"][cat][idx]["price"] = price
        save_db(db)
        p = db["products"][cat][idx]
        await update.message.reply_text(f"✅ Đổi giá *{p['name']}* → *{price:,}đ*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setprice <cat> <index> <giá>")

async def addkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx = ctx.args[0], int(ctx.args[1])
        keys_raw = " ".join(ctx.args[2:])
        new_keys = [k.strip() for k in keys_raw.split("|") if k.strip()]
        db = load_db()
        p = db["products"][cat][idx]
        p.setdefault("keys", []).extend(new_keys)
        p["stock"] = len(p["keys"])
        save_db(db)
        await update.message.reply_text(
            f"✅ Thêm *{len(new_keys)}* key vào *{p['name']}*\nTổng key: *{len(p['keys'])}*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /addkey <cat> <index> <key1|key2|key3>")

async def listkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx = ctx.args[0], int(ctx.args[1])
        db = load_db()
        p = db["products"][cat][idx]
        keys = p.get("keys", [])
        if not keys:
            await update.message.reply_text(f"📭 *{p['name']}* chưa có key!", parse_mode="Markdown")
            return
        text = f"🔑 *KEY: {p['name']}*\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, k in enumerate(keys):
            text += f"{i+1}. `{k}`\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /listkeys <cat> <index>")

async def addvoucher(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        code = ctx.args[0].upper()
        amount = int(ctx.args[1])
        limit = int(ctx.args[2]) if len(ctx.args) > 2 else 999
        db = load_db()
        db["vouchers"][code] = {"amount": amount, "limit": limit, "used": 0}
        save_db(db)
        await update.message.reply_text(
            f"✅ Tạo voucher *{code}*\n💰 Giảm: {amount:,}đ\n🔢 Giới hạn: {limit} lần",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /addvoucher <code> <giảm> <limit>")

async def setvoucher(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        code = ctx.args[0].upper()
        amount = int(ctx.args[1])
        limit = int(ctx.args[2]) if len(ctx.args) > 2 else 999
        db = load_db()
        if code not in db.get("vouchers", {}):
            await update.message.reply_text(f"❌ Mã *{code}* không tồn tại!", parse_mode="Markdown")
            return
        db["vouchers"][code]["amount"] = amount
        db["vouchers"][code]["limit"] = limit
        save_db(db)
        await update.message.reply_text(f"✅ Đã cập nhật voucher *{code}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setvoucher <code> <giảm> <limit>")

async def refund(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        oid = ctx.args[0].upper()
        db = load_db()
        o = next((x for x in db["orders"] if x["id"] == oid), None)
        if not o:
            await update.message.reply_text(f"❌ Không tìm thấy đơn *{oid}*!", parse_mode="Markdown")
            return
        if o.get("refunded"):
            await update.message.reply_text(f"❌ Đơn *{oid}* đã hoàn tiền rồi!", parse_mode="Markdown")
            return
        u = get_user(db, o["user"])
        u["balance"] += o["price"]
        o["refunded"] = True
        o["status"] = "Đã hoàn tiền"
        save_db(db)
        await update.message.reply_text(
            f"✅ Hoàn tiền đơn *{oid}*\n👤 {o['username']}\n💰 {o['price']:,}đ",
            parse_mode="Markdown")
        try:
            await ctx.bot.send_message(int(o["user"]),
                f"💰 *HOÀN TIỀN ĐƠN #{oid}*\nĐã hoàn *{o['price']:,}đ*!\n💳 Số dư: *{u['balance']:,}đ*",
                parse_mode="Markdown")
        except: pass
    except:
        await update.message.reply_text("❌ /refund <order_id>")

async def listusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    users = db.get("users", {})
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    text = f"👥 *DANH SÁCH USERS* ({len(users)} người)\n━━━━━━━━━━━━━━━━━━━━\n"
    for uid2, u2 in list(users.items())[-20:]:
        status = "🔒" if u2.get("banned") else "✅"
        vip_name, _ = get_vip_level(u2.get("total_spent", 0))
        text += f"{status} *{u2['name']}* (`{uid2}`)\n   💳 {u2['balance']:,}đ | {vip_name}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        tid = ctx.args[0]
        db = load_db()
        u = get_user(db, tid)
        u["banned"] = not u.get("banned", False)
        save_db(db)
        status = "🔒 Khóa" if u["banned"] else "🔓 Mở khóa"
        await update.message.reply_text(f"✅ {status} tài khoản {tid}")
    except:
        await update.message.reply_text("❌ /ban <user_id>")

async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(ctx.args)
    if not msg:
        await update.message.reply_text("❌ /broadcast <tin nhắn>")
        return
    db = load_db()
    ok = 0
    for uid2 in db["users"]:
        try:
            await ctx.bot.send_message(int(uid2),
                f"📢 *THÔNG BÁO TỪ {SHOP_NAME}:*\n\n{msg}", parse_mode="Markdown")
            ok += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"✅ Gửi tới {ok} người dùng!")

async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    today = today_str()
    orders_today = [o for o in db["orders"] if o["time"].startswith(today[:5])]
    revenue_today = sum(o["price"] for o in orders_today)
    revenue_all = sum(o["price"] for o in db["orders"])
    vip_counts = {}
    for u2 in db["users"].values():
        vname, _ = get_vip_level(u2.get("total_spent", 0))
        vip_counts[vname] = vip_counts.get(vname, 0) + 1
    vip_txt = " | ".join([f"{k}: {v}" for k, v in vip_counts.items()])
    await update.message.reply_text(
        f"📊 *THỐNG KÊ HỆ THỐNG*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Tổng users: *{len(db['users'])}*\n"
        f"📋 Tổng đơn: *{len(db['orders'])}*\n"
        f"💰 Doanh thu: *{revenue_all:,}đ*\n"
        f"📅 Hôm nay: *{len(orders_today)} đơn* — *{revenue_today:,}đ*\n\n"
        f"*VIP:* {vip_txt}",
        parse_mode="Markdown")

async def listproducts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    text = "📦 *DANH SÁCH SẢN PHẨM*\n━━━━━━━━━━━━━━━━━━━━\n"
    for cat, items in db["products"].items():
        text += f"\n*{cat}*\n"
        for i, p in enumerate(items):
            keys_count = len(p.get("keys", []))
            text += f"  [{i}] {p['name']} | {p['price']//1000}K | Stock: {p['stock']} | Keys: {keys_count}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def flashsale(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        db = load_db()
        s = db.get("settings", default_settings())
        if ctx.args[0].lower() == "off":
            s["flash_sale"] = False
            db["settings"] = s
            save_db(db)
            await update.message.reply_text("✅ Đã tắt Flash Sale!")
            return
        pct = int(ctx.args[0])
        hours = float(ctx.args[1]) if len(ctx.args) > 1 else 1
        end_time = datetime.datetime.now() + datetime.timedelta(hours=hours)
        s["flash_sale"] = True
        s["flash_discount"] = pct
        s["flash_end"] = end_time.strftime("%d/%m/%Y %H:%M")
        db["settings"] = s
        save_db(db)
        await update.message.reply_text(
            f"🔥 *FLASH SALE BẬT!*\n💥 Giảm: *{pct}%*\n⏰ Kết thúc: *{s['flash_end']}*",
            parse_mode="Markdown")
        ok = 0
        for uid2 in list(db["users"].keys()):
            try:
                await ctx.bot.send_message(int(uid2),
                    f"⚡ *FLASH SALE -{pct}%!*\n🛒 Toàn bộ sản phẩm giảm *{pct}%*!\n⏰ Chỉ *{hours}h* — Mua ngay: /start",
                    parse_mode="Markdown")
                ok += 1
                await asyncio.sleep(0.05)
            except: pass
        await update.message.reply_text(f"📢 Đã thông báo *{ok}* người!", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /flashsale <phần_trăm> <giờ>\nTắt: /flashsale off")

async def setbuylimit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat, idx, limit = ctx.args[0], int(ctx.args[1]), int(ctx.args[2])
        db = load_db()
        db["products"][cat][idx]["buy_limit"] = limit
        save_db(db)
        p = db["products"][cat][idx]
        await update.message.reply_text(
            f"✅ *{p['name']}*\nGiới hạn: *{limit} lần/ngày*" if limit > 0 else f"✅ Bỏ giới hạn mua cho *{p['name']}*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setbuylimit <cat> <idx> <limit>")

async def maintenance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    s = db.get("settings", default_settings())
    s["maintenance"] = not s.get("maintenance", False)
    db["settings"] = s
    save_db(db)
    status = "🔧 BẬT" if s["maintenance"] else "✅ TẮT"
    await update.message.reply_text(f"Bảo trì: {status}")

async def setshop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if not ctx.args:
        await update.message.reply_text("❌ /setshop <tên shop mới>")
        return
    global SHOP_NAME
    SHOP_NAME = " ".join(ctx.args)
    await update.message.reply_text(f"✅ Đổi tên shop: *{SHOP_NAME}*", parse_mode="Markdown")

async def setspin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cost = int(ctx.args[0])
        db = load_db()
        s = db.get("settings", default_settings())
        s["spin_cost"] = cost
        db["settings"] = s
        save_db(db)
        await update.message.reply_text(f"✅ Giá vòng quay: *{cost:,}đ/lần*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setspin <giá>")

async def setdice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cost = int(ctx.args[0])
        db = load_db()
        s = db.get("settings", default_settings())
        s["dice_cost"] = cost
        db["settings"] = s
        save_db(db)
        await update.message.reply_text(f"✅ Giá xúc xắc/tài xỉu/đoán số: *{cost:,}đ/lần*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setdice <giá>")

async def backup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    backup_db()
    await update.message.reply_text("✅ Đã backup database!")

async def adminhelp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "🛠 *LỆNH ADMIN*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/addmoney <id> <tiền>\n"
        "/removemoney <id> <tiền>\n"
        "/addproduct <cat> <tên> <giá> <stock>\n"
        "/deleteproduct <cat> <idx>\n"
        "/setprice <cat> <idx> <giá>\n"
        "/addstock <cat> <idx> <qty>\n"
        "/addkey <cat> <idx> <key1|key2>\n"
        "/listkeys <cat> <idx>\n"
        "/addvoucher <code> <giảm> <limit>\n"
        "/setvoucher <code> <giảm> <limit>\n"
        "/setbuylimit <cat> <idx> <n>\n"
        "/refund <order_id>\n"
        "/ban <id>\n"
        "/listusers\n"
        "/listproducts\n"
        "/broadcast <tin nhắn>\n"
        "/flashsale <pct> <giờ> | off\n"
        "/stats\n"
        "/maintenance\n"
        "/setshop <tên>\n"
        "/setspin <giá>\n"
        "/setdice <giá>\n"
        "/backup\n"
        "/adminhelp",
        parse_mode="Markdown")


# ══════════════════════════════
# HELPER REDIRECT
# ══════════════════════════════
async def button_redirect(update: Update, ctx: ContextTypes.DEFAULT_TYPE, action: str):
    db = load_db()
    u = get_user(db, update.effective_user.id)
    uid = str(update.effective_user.id)
    if action == "orders":
        orders = u.get("orders", [])
        if not orders:
            await update.message.reply_text("📋 Chưa có đơn hàng nào!", reply_markup=kb_back())
            return
        rows = []
        for oid in reversed(orders[-15:]):
            o = next((x for x in db["orders"] if x["id"] == oid), None)
            if o:
                label = f"✅ {o['time'][:10]} | {o['price']//1000}K | {o['product'][:18]}"
                rows.append([InlineKeyboardButton(label, callback_data=f"od_{oid}")])
        rows.append([InlineKeyboardButton("🏠 Quay lại", callback_data="main")])
        await update.message.reply_text("📋 *LỊCH SỬ ĐƠN HÀNG*", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(rows))
    elif action == "profile":
        vip_name, vip_disc = get_vip_level(u.get("total_spent", 0))
        await update.message.reply_text(
            f"📊 *THỐNG KÊ CÁ NHÂN*\n👤 {u['name']}\n💳 {u['balance']:,}đ\n🏅 {vip_name}\n⭐ {u.get('points',0)} điểm",
            parse_mode="Markdown", reply_markup=kb_back())
    elif action == "earn":
        ref_link = f"https://t.me/{ctx.bot.username}?start=ref_{uid}"
        await update.message.reply_text(
            f"🎁 *GIỚI THIỆU*\n🔗 `{ref_link}`\n👥 Đã mời: {u['ref_count']}\n💰 Đã kiếm: {u['ref_earned']:,}đ",
            parse_mode="Markdown", reply_markup=kb_back())


async def post_init(app):
    user_commands = [
        BotCommand("start",    "🏠 Menu chính"),
        BotCommand("lichsu",   "📋 Lịch sử đơn hàng"),
        BotCommand("mystats",  "📊 Thống kê cá nhân"),
        BotCommand("myref",    "🎁 Giới thiệu bạn bè"),
    ]
    admin_commands = user_commands + [
        BotCommand("addmoney",     "💰 Cộng tiền"),
        BotCommand("removemoney",  "💸 Trừ tiền"),
        BotCommand("addproduct",   "➕ Thêm sản phẩm"),
        BotCommand("deleteproduct","🗑 Xóa sản phẩm"),
        BotCommand("setprice",     "🏷 Đổi giá"),
        BotCommand("addstock",     "📦 Thêm stock"),
        BotCommand("addkey",       "🔑 Thêm key tự động"),
        BotCommand("listkeys",     "🔑 Xem key"),
        BotCommand("addvoucher",   "🎫 Tạo voucher"),
        BotCommand("setvoucher",   "✏️ Sửa voucher"),
        BotCommand("setbuylimit",  "🛡 Giới hạn mua"),
        BotCommand("refund",       "↩️ Hoàn tiền"),
        BotCommand("ban",          "🔒 Khóa tài khoản"),
        BotCommand("listusers",    "👥 Danh sách users"),
        BotCommand("listproducts", "📋 Danh sách sản phẩm"),
        BotCommand("broadcast",    "📢 Gửi thông báo"),
        BotCommand("flashsale",    "🔥 Flash Sale"),
        BotCommand("stats",        "📊 Thống kê"),
        BotCommand("maintenance",  "🔧 Bảo trì"),
        BotCommand("setshop",      "🏪 Đổi tên shop"),
        BotCommand("setspin",      "🎡 Cài vòng quay"),
        BotCommand("setdice",      "🎲 Cài xúc xắc"),
        BotCommand("backup",       "💾 Backup data"),
        BotCommand("adminhelp",    "🛠 Trợ giúp admin"),
    ]
    await app.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))


# ══════════════════════════════
# MAIN
# ══════════════════════════════
def main():
    init_db()
    backup_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("lichsu",       lambda u,c: button_redirect(u,c,"orders")))
    app.add_handler(CommandHandler("mystats",      lambda u,c: button_redirect(u,c,"profile")))
    app.add_handler(CommandHandler("myref",        lambda u,c: button_redirect(u,c,"earn")))
    app.add_handler(CommandHandler("addmoney",     addmoney))
    app.add_handler(CommandHandler("removemoney",  removemoney))
    app.add_handler(CommandHandler("addproduct",   addproduct))
    app.add_handler(CommandHandler("deleteproduct",deleteproduct))
    app.add_handler(CommandHandler("addstock",     addstock))
    app.add_handler(CommandHandler("setprice",     setprice))
    app.add_handler(CommandHandler("addkey",       addkey))
    app.add_handler(CommandHandler("listkeys",     listkeys))
    app.add_handler(CommandHandler("addvoucher",   addvoucher))
    app.add_handler(CommandHandler("setvoucher",   setvoucher))
    app.add_handler(CommandHandler("setbuylimit",  setbuylimit))
    app.add_handler(CommandHandler("refund",       refund))
    app.add_handler(CommandHandler("ban",          ban))
    app.add_handler(CommandHandler("listusers",    listusers))
    app.add_handler(CommandHandler("listproducts", listproducts))
    app.add_handler(CommandHandler("broadcast",    broadcast))
    app.add_handler(CommandHandler("flashsale",    flashsale))
    app.add_handler(CommandHandler("stats",        stats))
    app.add_handler(CommandHandler("maintenance",  maintenance))
    app.add_handler(CommandHandler("setshop",      setshop))
    app.add_handler(CommandHandler("setspin",      setspin))
    app.add_handler(CommandHandler("setdice",      setdice))
    app.add_handler(CommandHandler("backup",       backup))
    app.add_handler(CommandHandler("adminhelp",    adminhelp))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"🤖 {SHOP_NAME} Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()

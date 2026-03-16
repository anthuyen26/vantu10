import os, json, random, datetime, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ══════════════════════════════
# CẤU HÌNH
# ══════════════════════════════
TOKEN      = os.environ.get("TOKEN", "")
ADMIN_ID   = 7510588294
SHOP_NAME  = "Vantu Shop"
ADMIN_USER = "chipxgai"

# ══════════════════════════════
# DATABASE (JSON file)
# ══════════════════════════════
DB_FILE = "/data/db.json" if os.path.exists("/data") else "db.json"

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True) if "/" in DB_FILE else None

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
            "spin_today": 0, "dice_today": 0, "last_game_date": ""
        }
    return db["users"][uid]

def now():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

def default_settings():
    return {
        "spin_cost": 20000,
        "spin_win_after": 3,
        "spin_win_prize": 20000,
        "dice_cost": 3000,
        "ref_percent": 10,
        "withdraw_min": 50000,
        "maintenance": False,
        "welcome_msg": "Xin chào {name}! Chào mừng đến với {shop}!",
        "spin_daily_limit": 5,
        "dice_daily_limit": 5,
        "low_stock_alert": 3
    }

def default_products():
    return {
        "🎥 Netflix": [
            {"name": "Netflix Premium 4K 1 tháng", "price": 65000, "stock": 10, "desc": "4K Ultra HD · Nhiều màn hình"}
        ],
        "▶️ YouTube Premium": [
            {"name": "YouTube Premium 1 tháng",  "price": 30000,  "stock": 15, "desc": "Không quảng cáo · Phát nền"},
            {"name": "YouTube Premium 6 tháng",  "price": 140000, "stock": 8,  "desc": "Không quảng cáo · Phát nền"},
            {"name": "YouTube Premium 12 tháng", "price": 260000, "stock": 5,  "desc": "Không quảng cáo · Phát nền"},
            {"name": "YouTube Premium 18 tháng", "price": 360000, "stock": 3,  "desc": "Không quảng cáo · Phát nền"},
        ],
        "🎬 CapCut Pro": [
            {"name": "CapCut Pro 35 Ngày BHF", "price": 26000,  "stock": 9,  "desc": "Full tính năng Pro"},
            {"name": "CapCut Pro 6 Tháng",     "price": 110000, "stock": 13, "desc": "Full tính năng Pro"},
        ],
        "🤖 ChatGPT Plus": [
            {"name": "ChatGPT Plus Riêng Tư 1 tháng",       "price": 30000, "stock": 12, "desc": "Model mạnh nhất"},
            {"name": "ChatGPT Plus Team Chính Chủ 1 tháng", "price": 50000, "stock": 8,  "desc": "Chính chủ 100%"},
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
        [InlineKeyboardButton("👤 Thống Kê Cá Nhân",  callback_data="profile")],
        [InlineKeyboardButton("👥 Nhóm Cộng Đồng", url=f"https://t.me/{ADMIN_USER}")],
    ])

def kb_shop(products):
    rows = []
    for cat, items in products.items():
        total = sum(p["stock"] for p in items)
        if total > 0:
            label = f"{cat} ({total})"
        else:
            label = f"❌ {cat} - TẠM HẾT HÀNG"
        rows.append([InlineKeyboardButton(label, callback_data=f"cat_{cat}")])
    rows.append([InlineKeyboardButton("🏠 Quay lại Main Menu", callback_data="main")])
    return InlineKeyboardMarkup(rows)

def kb_cat(cat, items):
    rows = []
    for i, p in enumerate(items):
        if p["stock"] > 0:
            label = f"{p['name']} | {p['price']//1000}K | Còn {p['stock']}"
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
        [InlineKeyboardButton("🏠 Quay lại",          callback_data="main")],
    ])

# ══════════════════════════════
# TOP NẠP
# ══════════════════════════════
def get_top_deposit(db, limit=10):
    users = []
    for uid, u in db["users"].items():
        if u.get("total_deposit", 0) > 0:
            users.append((u["name"], u["total_deposit"]))
    users.sort(key=lambda x: x[1], reverse=True)
    return users[:limit]

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

    # Xử lý ref
    if ctx.args and ctx.args[0].startswith("ref_"):
        ref_id = ctx.args[0].replace("ref_", "")
        if ref_id != uid and not u["ref_by"]:
            u["ref_by"] = ref_id
            ref_u = get_user(db, ref_id)
            ref_u["ref_count"] += 1
            save_db(db)
            try:
                await ctx.bot.send_message(ref_id,
                    f"🎉 *{u['name']}* vừa dùng link giới thiệu của bạn!\n"
                    f"💰 Bạn sẽ nhận 10% hoa hồng từ mọi đơn hàng của họ!",
                    parse_mode="Markdown")
            except: pass

    save_db(db)
    welcome = s.get("welcome_msg","").format(name=u["name"], shop=SHOP_NAME)
    text = f"""
👑 *HỆ THỐNG DỊCH VỤ MMO CAO CẤP* 👑
━━━━━━━━━━━━━━━━━━━━━━━━
*{SHOP_NAME}*

💥 Uy tín - Nhanh gọn - Chuyên nghiệp
⚡ Hệ thống giao hàng tự động 24/7

{welcome}

✅ *Lựa chọn dịch vụ bên dưới để bắt đầu:*
"""
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
        text = f"👑 *{SHOP_NAME}*\n\n✅ Chọn dịch vụ bên dưới:"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_main())

    # ── CỬA HÀNG ──
    elif data == "shop":
        await q.edit_message_text(
            "🛒 *CỬA HÀNG DỊCH VỤ*\n\nChọn danh mục sản phẩm bạn quan tâm:",
            parse_mode="Markdown", reply_markup=kb_shop(db["products"])
        )

    # ── DANH MỤC ──
    elif data.startswith("cat_"):
        cat = data[4:]
        if cat not in db["products"]:
            await q.edit_message_text("❌ Không tìm thấy!", reply_markup=kb_back("shop"))
            return
        await q.edit_message_text(
            f"📦 *DANH MỤC: {cat}*\n\nChọn sản phẩm:",
            parse_mode="Markdown", reply_markup=kb_cat(cat, db["products"][cat])
        )

    # ── CHI TIẾT SẢN PHẨM ──
    elif data.startswith("buy_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], int(parts[2])
        p = db["products"][cat][idx]
        if p["stock"] <= 0:
            await q.answer("❌ Sản phẩm đã hết hàng!", show_alert=True)
            return
        text = f"""
🛍 *{p['name']}*
━━━━━━━━━━━━━━━━━━━━
📝 {p.get('desc','')}
💰 Giá: *{p['price']:,}đ*
📦 Tồn kho: *{p['stock']}*
━━━━━━━━━━━━━━━━━━━━
💳 Số dư của bạn: *{u['balance']:,}đ*

🎫 Bạn có mã giảm giá? Nhập sau khi xác nhận.
"""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Xác Nhận Mua", callback_data=f"confirm_{cat}_{idx}")],
            [InlineKeyboardButton("🏷 Dùng Mã Giảm Giá", callback_data=f"voucher_{cat}_{idx}")],
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
            parse_mode="Markdown", reply_markup=kb_back(f"buy_{cat}_{idx}", "🔙 Quay lại")
        )

    # ── XÁC NHẬN MUA (có thể có voucher) ──
    elif data.startswith("confirm_"):
        parts = data.split("_", 2)
        cat, idx = parts[1], int(parts[2])
        p = db["products"][cat][idx]
        if p["stock"] <= 0:
            await q.answer("❌ Hết hàng rồi!", show_alert=True)
            return

        # Kiểm tra voucher đã áp dụng
        discount = ctx.user_data.get(f"discount_{cat}_{idx}", 0)
        final_price = max(0, p["price"] - discount)

        if u["balance"] < final_price:
            shortage = final_price - u["balance"]
            await q.edit_message_text(
                f"❌ *Số dư không đủ!*\n\n"
                f"💳 Số dư: *{u['balance']:,}đ*\n"
                f"💰 Giá: *{final_price:,}đ*\n"
                f"📉 Thiếu: *{shortage:,}đ*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Nạp Tiền", callback_data="wallet")],
                    [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
                ])
            )
            return

        # Trừ tiền
        u["balance"] -= final_price
        u["total_spent"] += final_price
        p["stock"] -= 1

        # Hoa hồng ref
        if u["ref_by"]:
            commission = int(final_price * s.get("ref_percent", 10) / 100)
            if commission > 0:
                ref_u = get_user(db, u["ref_by"])
                ref_u["balance"] += commission
                ref_u["ref_earned"] += commission
                try:
                    await ctx.bot.send_message(u["ref_by"],
                        f"💰 Nhận *{commission:,}đ* hoa hồng từ {u['name']}!",
                        parse_mode="Markdown")
                except: pass

        # Tạo đơn
        order_id = f"VT{len(db['orders'])+1:04d}"
        order = {
            "id": order_id, "user": uid, "username": u["name"],
            "product": p["name"], "price": final_price,
            "original_price": p["price"], "discount": discount,
            "time": now(), "status": "Hoàn thành", "cat": cat
        }
        db["orders"].append(order)
        u["orders"].append(order_id)

        # Xóa voucher đã dùng
        ctx.user_data.pop(f"discount_{cat}_{idx}", None)
        save_db(db)

        # Thông báo admin
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"🛒 *ĐƠN HÀNG MỚI #{order_id}*\n"
                f"👤 {u['name']} (ID: {uid})\n"
                f"📦 {p['name']}\n"
                f"💰 {final_price:,}đ{' (Giảm '+str(discount//1000)+'K)' if discount else ''}\n"
                f"🕐 {now()}",
                parse_mode="Markdown")
        except: pass

        await q.edit_message_text(
            f"✅ *MUA HÀNG THÀNH CÔNG!*\n\n"
            f"📦 *{p['name']}*\n"
            f"💰 Đã thanh toán: *{final_price:,}đ*\n"
            f"📋 Mã đơn: *{order_id}*\n"
            f"💳 Số dư còn: *{u['balance']:,}đ*\n\n"
            f"📩 Nhắn @{ADMIN_USER} kèm mã đơn để nhận tài khoản!\n"
            f"⏰ Hỗ trợ 24/7",
            parse_mode="Markdown", reply_markup=kb_main()
        )

    # ── LỊCH SỬ ĐƠN ──
    elif data == "orders":
        orders = u.get("orders", [])
        if not orders:
            await q.edit_message_text(
                "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n📭 Chưa có đơn hàng nào!",
                parse_mode="Markdown", reply_markup=kb_back()
            )
            return
        rows = []
        for oid in reversed(orders[-15:]):
            o = next((x for x in db["orders"] if x["id"] == oid), None)
            if o:
                icon = "✅" if o["status"] == "Hoàn thành" else "⏳"
                label = f"{icon} {o['time'][:5]} | {o['product'][:22]}"
                rows.append([InlineKeyboardButton(label, callback_data=f"od_{oid}")])
        rows.append([InlineKeyboardButton("🏠 Quay lại", callback_data="main")])
        await q.edit_message_text(
            "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n👇 Chọn đơn để xem chi tiết:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows)
        )

    elif data.startswith("od_"):
        oid = data[3:]
        o = next((x for x in db["orders"] if x["id"] == oid), None)
        if not o:
            await q.answer("Không tìm thấy đơn!", show_alert=True)
            return
        disc_txt = f"\n🎫 Giảm giá: *{o.get('discount',0):,}đ*" if o.get('discount') else ""
        await q.edit_message_text(
            f"📋 *CHI TIẾT ĐƠN #{o['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {o['product']}\n"
            f"💰 Giá: *{o['price']:,}đ*{disc_txt}\n"
            f"🕐 {o['time']}\n"
            f"✅ {o['status']}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📩 Liên hệ @{ADMIN_USER} kèm mã đơn nếu chưa nhận được hàng.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Báo Lỗi Đơn Này", callback_data=f"rep_{oid}")],
                [InlineKeyboardButton("🔙 Quay lại", callback_data="orders")],
            ])
        )

    # ── VÍ TIỀN ──
    elif data == "wallet":
        await q.edit_message_text(
            f"💳 *QUẢN LÝ TÀI KHOẢN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Số dư: *{u['balance']:,}đ*\n"
            f"📊 Tổng nạp: *{u.get('total_deposit',0):,}đ*\n"
            f"🛍 Tổng chi: *{u['total_spent']:,}đ*",
            parse_mode="Markdown", reply_markup=kb_wallet()
        )

    # ── NẠP THẺ CÀO ──
    elif data == "napthe":
        await q.edit_message_text(
            "💵 *NẠP THẺ CÀO*\n\n"
            "Hỗ trợ: Viettel, Vinaphone, Mobifone, Zing\n\n"
            "Gửi thông tin theo định dạng:\n"
            "`LOAITHE MENHGIA SERI MATHE`\n\n"
            "Ví dụ:\n"
            "`VIETTEL 50000 12345678901234 123456789012`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📱 Viettel",    callback_data="the_VIETTEL")],
                [InlineKeyboardButton("📱 Vinaphone",  callback_data="the_VINAPHONE")],
                [InlineKeyboardButton("📱 Mobifone",   callback_data="the_MOBIFONE")],
                [InlineKeyboardButton("📱 Zing",       callback_data="the_ZING")],
                [InlineKeyboardButton("🏠 Quay lại",   callback_data="wallet")],
            ])
        )

    elif data.startswith("the_"):
        nha_mang = data[4:]
        ctx.user_data["nap_the_type"] = nha_mang
        ctx.user_data["waiting_the"] = True
        await q.edit_message_text(
            f"📱 *NẠP THẺ {nha_mang}*\n\n"
            f"Gửi thông tin theo định dạng:\n"
            f"`MENHGIA SERI MATHE`\n\n"
            f"Ví dụ: `50000 12345678901234 123456789012`",
            parse_mode="Markdown",
            reply_markup=kb_back("napthe", "🔙 Quay lại")
        )

    # ── NẠP CHUYỂN KHOẢN ──
    elif data == "napck":
        await q.edit_message_text(
            f"🏦 *NẠP TIỀN CHUYỂN KHOẢN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📲 Liên hệ Admin: @{ADMIN_USER}\n\n"
            f"Nội dung chuyển khoản:\n"
            f"`NAP {uid}`\n\n"
            f"Admin sẽ cộng tiền trong vòng 5 phút!",
            parse_mode="Markdown", reply_markup=kb_back("wallet")
        )

    # ── LỊCH SỬ NẠP ──
    elif data == "deposit_history":
        cards = u.get("cards", [])
        if not cards:
            await q.edit_message_text(
                "📊 *LỊCH SỬ NẠP TIỀN*\n\n📭 Chưa có lịch sử nạp!",
                parse_mode="Markdown", reply_markup=kb_back("wallet")
            )
            return
        text = "📊 *LỊCH SỬ NẠP TIỀN*\n━━━━━━━━━━━━━━━━━━━━\n"
        for c in reversed(cards[-10:]):
            icon = "✅" if c["status"] == "success" else "❌"
            text += f"{icon} {c['time'][:10]} | {c['type']} | {c['amount']:,}đ\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back("wallet"))

    # ── RÚT TIỀN ──
    elif data == "withdraw":
        min_wd = s.get("withdraw_min", 50000)
        if u["balance"] < min_wd:
            await q.answer(f"❌ Cần ít nhất {min_wd:,}đ để rút!", show_alert=True)
            return
        ctx.user_data["waiting_withdraw"] = True
        await q.edit_message_text(
            f"💸 *RÚT TIỀN*\n\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"📉 Tối thiểu: *{min_wd:,}đ*\n\n"
            f"Gửi số tiền muốn rút:",
            parse_mode="Markdown", reply_markup=kb_back("wallet")
        )

    # ── VÒNG QUAY ──
    elif data == "spin":
        cost = s.get("spin_cost", 20000)
        win_after = s.get("spin_win_after", 3)
        win_prize = s.get("spin_win_prize", 20000)
        daily_limit = s.get("spin_daily_limit", 5)
        today = datetime.datetime.now().strftime("%d/%m/%Y")
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
        spin_count = u.get("spin_count", 0) + 1
        u["spin_count"] = spin_count
        if spin_count >= win_after:
            result_txt = f"🎉 Trúng {win_prize//1000}K!"
            prize = win_prize
            u["spin_count"] = 0
        else:
            prizes = [
                ("🎰 JACKPOT 200K!", 200000, 1),
                ("💎 Trúng 100K!",   100000, 2),
                ("🥇 Trúng 50K!",    50000,  3),
                ("😢 Không trúng",   0,      94),
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
        save_db(db)
        spins_left = win_after - u.get("spin_count", 0)
        await q.edit_message_text(
            f"🎡 *VÒNG QUAY MAY MẮN*\n\n"
            f"🎰 Kết quả: *{result_txt}*\n"
            f"{'💰 Nhận: '+f'{prize:,}đ' if prize > 0 else f'💸 Mất: {cost:,}đ'}\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n\n"
            f"🔄 Lần quay tiếp theo đảm bảo trúng sau *{spins_left}* lần!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎡 Quay Tiếp ({cost//1000}K)", callback_data="spin")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ])
        )

    # ── XÚC XẮC ──
    elif data == "dice":
        cost = s.get("dice_cost", 3000)
        daily_limit = s.get("dice_daily_limit", 5)
        today = datetime.datetime.now().strftime("%d/%m/%Y")
        if u.get("last_game_date") != today:
            u["spin_today"] = 0
            u["dice_today"] = 0
            u["last_game_date"] = today
        if u.get("dice_today", 0) >= daily_limit:
            await q.answer(f"❌ Hết lượt chơi hôm nay! Giới hạn {daily_limit} lần/ngày.", show_alert=True)
            return
        if u["balance"] < cost:
            await q.answer(f"❌ Cần {cost:,}đ để chơi!", show_alert=True)
            return
        u["dice_today"] = u.get("dice_today", 0) + 1
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        d3 = random.randint(1, 6)
        if d1 == d2 == d3:
            prize = cost * 5
            result = f"🎉 *BA GIỐNG NHAU! THẮNG LỚN!* Nhận *{prize:,}đ*"
        else:
            prize = 0
            result = "😢 Thua rồi! Cần 3 số giống nhau để thắng."
        u["balance"] = u["balance"] - cost + prize
        save_db(db)
        await q.edit_message_text(
            f"🎲 *XÚC XẮC*\n\n"
            f"🎲 {d1}  •  🎲 {d2}  •  🎲 {d3}\n\n"
            f"{result}\n"
            f"💳 Số dư: *{u['balance']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🎲 Chơi Tiếp ({cost//1000}K)", callback_data="dice")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ])
        )

    # ── KIẾM TIỀN ──
    elif data == "earn":
        ref_link = f"https://t.me/{ctx.bot.username}?start=ref_{uid}"
        pct = s.get("ref_percent", 10)
        await q.edit_message_text(
            f"🎁 *CHƯƠNG TRÌNH ĐỐI TÁC*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Giới thiệu bạn bè nhận *{pct}% hoa hồng* mọi giao dịch!\n\n"
            f"🔗 *Link của bạn:*\n`{ref_link}`\n\n"
            f"📊 Đã mời: *{u['ref_count']} người*\n"
            f"💰 Đã kiếm: *{u['ref_earned']:,}đ*\n"
            f"💳 Số dư: *{u['balance']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 Top Giới Thiệu", callback_data="top_ref")],
                [InlineKeyboardButton("💸 Rút Tiền",       callback_data="withdraw")],
                [InlineKeyboardButton("🏠 Quay lại",       callback_data="main")],
            ])
        )

    # ── TOP NẠP / TOP GIỚI THIỆU ──
    elif data in ("top_deposit", "top_ref"):
        db2 = load_db()
        if data == "top_deposit":
            users = [(u2["name"], u2.get("total_deposit",0)) for u2 in db2["users"].values() if u2.get("total_deposit",0)>0]
            title = "🏆 TOP NẠP TIỀN"
        else:
            users = [(u2["name"], u2.get("ref_count",0)) for u2 in db2["users"].values() if u2.get("ref_count",0)>0]
            title = "🏆 TOP GIỚI THIỆU"
        users.sort(key=lambda x: x[1], reverse=True)
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        text = f"{title}\n━━━━━━━━━━━━━━━━━━━━\n"
        for i, (name, val) in enumerate(users[:10]):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            suffix = "đ" if data == "top_deposit" else " người"
            text += f"{medal} {name}: *{val:,}{suffix}*\n"
        if not users:
            text += "Chưa có dữ liệu!"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back("earn" if data=="top_ref" else "main"))

    # ── THỐNG KÊ CÁ NHÂN ──
    elif data == "profile":
        await q.edit_message_text(
            f"📊 *THỐNG KÊ CÁ NHÂN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Tên: *{u['name']}*\n"
            f"🆔 ID: `{uid}`\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"📅 Tham gia: *{u['joined']}*\n\n"
            f"🛍 Tổng chi tiêu: *{u['total_spent']:,}đ* ({len(u['orders'])} đơn)\n"
            f"💵 Tổng nạp: *{u.get('total_deposit',0):,}đ*\n\n"
            f"👥 Đã giới thiệu: *{u['ref_count']} người*\n"
            f"💰 Hoa hồng: *{u['ref_earned']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 Top Nạp",  callback_data="top_deposit")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ])
        )

    # ── HỖ TRỢ ──
    elif data == "support":
        ctx.user_data["live_chat"] = True
        await q.edit_message_text(
            f"💬 *LIVE CHAT VỚI ADMIN*\n\n"
            f"📩 Gửi tin nhắn bên dưới, admin sẽ phản hồi sớm nhất!\n"
            f"📞 Hoặc liên hệ trực tiếp: @{ADMIN_USER}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Đóng Chat", callback_data="close_chat")],
                [InlineKeyboardButton("🏠 Quay lại",  callback_data="main")],
            ])
        )

    elif data == "close_chat":
        ctx.user_data["live_chat"] = False
        await q.edit_message_text("✅ Đã đóng chat.", reply_markup=kb_back())

    # ── BÁO LỖI ──
    elif data == "report":
        await q.edit_message_text(
            "🔧 *HƯỚNG DẪN BÁO LỖI*\n\n"
            "1️⃣ Chọn *Đã Mua*\n"
            "2️⃣ Chọn đơn hàng gặp lỗi\n"
            "3️⃣ Bấm *Báo Lỗi Đơn Này*\n\n"
            f"Hoặc nhắn thẳng @{ADMIN_USER}",
            parse_mode="Markdown", reply_markup=kb_back()
        )

    elif data.startswith("rep_"):
        oid = data[4:]
        ctx.user_data["report_order"] = oid
        ctx.user_data["waiting_report"] = True
        await q.edit_message_text(
            f"⚠️ *BÁO LỖI ĐƠN #{oid}*\n\nMô tả ngắn gọn vấn đề:",
            parse_mode="Markdown", reply_markup=kb_back("orders")
        )

    # ── HƯỚNG DẪN ──
    elif data == "guide":
        await q.edit_message_text(
            f"📖 *HƯỚNG DẪN & CHÍNH SÁCH*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛒 *Cách mua hàng:*\n"
            f"1. Chọn Cửa Hàng MMO\n"
            f"2. Chọn sản phẩm → Xác nhận\n"
            f"3. Nhắn @{ADMIN_USER} + mã đơn nhận acc\n\n"
            f"💳 *Nạp tiền:*\n"
            f"• Thẻ cào: Viettel/Mobi/Vina/Zing\n"
            f"• Chuyển khoản: Nhắn @{ADMIN_USER}\n\n"
            f"🔄 *Bảo hành:* 30 ngày\n"
            f"❓ *Hỗ trợ:* @{ADMIN_USER} - 24/7",
            parse_mode="Markdown", reply_markup=kb_back()
        )

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

    # ── MÃ GIẢM GIÁ ──
    if ctx.user_data.get("waiting_voucher"):
        voucher_key = text.strip().upper()
        target = ctx.user_data.get("voucher_for", "")
        vouchers = db.get("vouchers", {})
        if voucher_key in vouchers:
            v = vouchers[voucher_key]
            if v.get("used", 0) >= v.get("limit", 999):
                await update.message.reply_text("❌ Mã giảm giá đã hết lượt dùng!")
            else:
                parts = target.split("_")
                cat_idx = "_".join(parts)
                discount = v["amount"]
                ctx.user_data[f"discount_{cat_idx}"] = discount
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

    # ── NẠP THẺ ──
    if ctx.user_data.get("waiting_the"):
        nha_mang = ctx.user_data.get("nap_the_type", "")
        parts = text.strip().split()
        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Sai định dạng! Gửi:\n`MENHGIA SERI MATHE`\nVí dụ: `50000 12345678901234 123456789012`",
                parse_mode="Markdown")
            return
        try:
            menh_gia = int(parts[0])
            seri = parts[1]
            ma_the = parts[2]
        except:
            await update.message.reply_text("❌ Mệnh giá phải là số!")
            return

        ctx.user_data["waiting_the"] = False
        await update.message.reply_text("⏳ Đang xử lý thẻ...")

        # Ghi nhận thẻ chờ xử lý
        card_entry = {
            "type": nha_mang, "amount": menh_gia,
            "seri": seri, "code": ma_the,
            "user": uid, "time": now(), "status": "pending"
        }
        db["cards"].append(card_entry)
        u.setdefault("cards", []).append({"type": nha_mang, "amount": menh_gia, "time": now(), "status": "pending"})
        save_db(db)

        # Thông báo admin xử lý thủ công nếu chưa có API
        try:
            await ctx.bot.send_message(ADMIN_ID,
                f"💵 *NẠP THẺ MỚI*\n"
                f"👤 {u['name']} ({uid})\n"
                f"📱 {nha_mang} - {menh_gia:,}đ\n"
                f"🔢 Seri: `{seri}`\n"
                f"🔑 Mã thẻ: `{ma_the}`\n"
                f"⏰ {now()}\n\n"
                f"Dùng /addmoney {uid} {menh_gia} để cộng tiền!",
                parse_mode="Markdown")
        except: pass

        await update.message.reply_text(
            f"✅ *Đã nhận thẻ {nha_mang} {menh_gia:,}đ!*\n\n"
            f"⏳ Admin đang xử lý...\n"
            f"💰 Tiền sẽ vào trong vài phút!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main")]]))
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
                        await ctx.bot.send_message(
                            int(target_id),
                            f"📦 *Admin ({now()}):*\n{text}",
                            parse_mode="Markdown")
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
    # /addproduct <danh_muc> <tên> <giá> <stock>
    try:
        cat = ctx.args[0]
        price = int(ctx.args[-2])
        stock = int(ctx.args[-1])
        name = " ".join(ctx.args[1:-2])
        db = load_db()
        if cat not in db["products"]:
            db["products"][cat] = []
        db["products"][cat].append({"name": name, "price": price, "stock": stock, "desc": ""})
        save_db(db)
        await update.message.reply_text(f"✅ Đã thêm sản phẩm:\n📦 {name}\n💰 {price:,}đ | Stock: {stock}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /addproduct <danh_muc> <tên sản phẩm> <giá> <stock>")

async def addstock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    # /addstock <danh_muc> <index> <số_lượng>
    try:
        cat = ctx.args[0]
        idx = int(ctx.args[1])
        qty = int(ctx.args[2])
        db = load_db()
        db["products"][cat][idx]["stock"] += qty
        save_db(db)
        p = db["products"][cat][idx]
        await update.message.reply_text(f"✅ Thêm {qty} stock cho *{p['name']}*\nTổng còn: {p['stock']}", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /addstock <danh_muc> <index> <số_lượng>")

async def addvoucher(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    # /addvoucher <code> <giảm_tiền> <giới_hạn_lần_dùng>
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
        await update.message.reply_text("❌ /addvoucher <code> <số_tiền_giảm> <giới_hạn>")

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
    for uid in db["users"]:
        try:
            await ctx.bot.send_message(int(uid),
                f"📢 *THÔNG BÁO TỪ {SHOP_NAME}:*\n\n{msg}",
                parse_mode="Markdown")
            ok += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"✅ Gửi tới {ok} người dùng!")

async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    total_users = len(db["users"])
    total_orders = len(db["orders"])
    revenue = sum(o["price"] for o in db["orders"])
    active = sum(1 for u in db["users"].values() if u.get("orders"))
    await update.message.reply_text(
        f"📊 *THỐNG KÊ HỆ THỐNG*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Tổng users: *{total_users}*\n"
        f"🛒 Đã mua: *{active}*\n"
        f"📋 Tổng đơn: *{total_orders}*\n"
        f"💰 Doanh thu: *{revenue:,}đ*",
        parse_mode="Markdown")

async def listproducts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    text = "📦 *DANH SÁCH SẢN PHẨM*\n━━━━━━━━━━━━━━━━━━━━\n"
    for cat, items in db["products"].items():
        text += f"\n*{cat}*\n"
        for i, p in enumerate(items):
            text += f"  [{i}] {p['name']} | {p['price']//1000}K | Stock: {p['stock']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

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
    await update.message.reply_text(f"✅ Đã đổi tên shop thành: *{SHOP_NAME}*", parse_mode="Markdown")

async def setprice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    # /setprice <danh_muc> <index> <giá_mới>
    try:
        cat = ctx.args[0]
        idx = int(ctx.args[1])
        price = int(ctx.args[2])
        db = load_db()
        db["products"][cat][idx]["price"] = price
        save_db(db)
        p = db["products"][cat][idx]
        await update.message.reply_text(
            f"✅ Đã đổi giá *{p['name']}* thành *{price:,}đ*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setprice <danh_muc> <index> <giá_mới>\nDùng /listproducts để xem index")

async def setspin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    # /setspin <giá_quay> <quay_bao_nhiêu_lần_thì_trúng> <phần_thưởng>
    try:
        cost = int(ctx.args[0])
        win_after = int(ctx.args[1])
        prize = int(ctx.args[2])
        db = load_db()
        s = db.get("settings", default_settings())
        s["spin_cost"] = cost
        s["spin_win_after"] = win_after
        s["spin_win_prize"] = prize
        db["settings"] = s
        save_db(db)
        await update.message.reply_text(
            f"✅ Cài vòng quay:\n💰 Giá: *{cost:,}đ/lần*\n🔄 Trúng sau: *{win_after} lần*\n🎁 Phần thưởng: *{prize:,}đ*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setspin <giá_quay> <số_lần_trúng> <phần_thưởng>")

async def setdice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    # /setdice <giá_chơi>
    try:
        cost = int(ctx.args[0])
        db = load_db()
        s = db.get("settings", default_settings())
        s["dice_cost"] = cost
        db["settings"] = s
        save_db(db)
        await update.message.reply_text(f"✅ Giá xúc xắc: *{cost:,}đ/lần*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setdice <giá_chơi>")

async def adminhelp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "🛠 *LỆNH ADMIN*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/addmoney <id> <tiền> — Cộng tiền\n"
        "/removemoney <id> <tiền> — Trừ tiền\n"
        "/addproduct <cat> <tên> <giá> <stock> — Thêm sản phẩm\n"
        "/addstock <cat> <idx> <qty> — Thêm stock\n"
        "/addvoucher <code> <giảm> <limit> — Tạo voucher\n"
        "/setprice <cat> <idx> <giá> — Đổi giá sản phẩm\n"
        "/setshop <tên> — Đổi tên shop\n"
        "/setspin <giá> <lần_trúng> <thưởng> — Cài vòng quay\n"
        "/setdice <giá> — Cài giá xúc xắc\n"
        "/ban <id> — Khóa/mở tài khoản\n"
        "/broadcast <tin nhắn> — Gửi thông báo\n"
        "/stats — Thống kê\n"
        "/listproducts — Danh sách sản phẩm\n"
        "/maintenance — Bật/tắt bảo trì\n",
        parse_mode="Markdown")


# ══════════════════════════════
# HELPER: redirect command -> button
# ══════════════════════════════
async def button_redirect(update: Update, ctx: ContextTypes.DEFAULT_TYPE, action: str):
    db = load_db()
    u = get_user(db, update.effective_user.id)
    uid = str(update.effective_user.id)
    s = db.get("settings", default_settings())
    if action == "orders":
        orders = u.get("orders", [])
        if not orders:
            await update.message.reply_text(
                "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n📭 Chưa có đơn hàng nào!",
                parse_mode="Markdown", reply_markup=kb_back())
            return
        rows = []
        for oid in reversed(orders[-15:]):
            o = next((x for x in db["orders"] if x["id"] == oid), None)
            if o:
                icon = "✅" if o["status"] == "Hoàn thành" else "⏳"
                label = f"{icon} {o['time'][:5]} | {o['product'][:22]}"
                rows.append([InlineKeyboardButton(label, callback_data=f"od_{oid}")])
        rows.append([InlineKeyboardButton("🏠 Quay lại", callback_data="main")])
        await update.message.reply_text(
            "📋 *LỊCH SỬ ĐƠN HÀNG*\n\n👇 Chọn đơn để xem chi tiết:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))
    elif action == "profile":
        await update.message.reply_text(
            f"📊 *THỐNG KÊ CÁ NHÂN*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Tên: *{u['name']}*\n"
            f"🆔 ID: `{uid}`\n"
            f"💳 Số dư: *{u['balance']:,}đ*\n"
            f"📅 Tham gia: *{u['joined']}*\n\n"
            f"🛍 Tổng chi tiêu: *{u['total_spent']:,}đ* ({len(u['orders'])} đơn)\n"
            f"💵 Tổng nạp: *{u.get('total_deposit',0):,}đ*\n\n"
            f"👥 Đã giới thiệu: *{u['ref_count']} người*\n"
            f"💰 Hoa hồng: *{u['ref_earned']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 Top Nạp",  callback_data="top_deposit")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))
    elif action == "earn":
        ref_link = f"https://t.me/{ctx.bot.username}?start=ref_{uid}"
        pct = s.get("ref_percent", 10)
        await update.message.reply_text(
            f"🎁 *CHƯƠNG TRÌNH ĐỐI TÁC*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Giới thiệu bạn bè nhận *{pct}% hoa hồng*!\n\n"
            f"🔗 *Link của bạn:*\n`{ref_link}`\n\n"
            f"📊 Đã mời: *{u['ref_count']} người*\n"
            f"💰 Đã kiếm: *{u['ref_earned']:,}đ*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Rút Tiền", callback_data="withdraw")],
                [InlineKeyboardButton("🏠 Quay lại", callback_data="main")],
            ]))

# ══════════════════════════════
# ADMIN COMMANDS MỚI
# ══════════════════════════════
async def deleteproduct(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        cat = ctx.args[0]
        idx = int(ctx.args[1])
        db = load_db()
        p = db["products"][cat][idx]
        db["products"][cat].pop(idx)
        save_db(db)
        await update.message.reply_text(f"✅ Đã xóa sản phẩm *{p['name']}*", parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /deleteproduct <danh_muc> <index>\nDùng /listproducts để xem index")

async def setvoucher(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        code = ctx.args[0].upper()
        amount = int(ctx.args[1])
        limit = int(ctx.args[2]) if len(ctx.args) > 2 else 999
        db = load_db()
        if code not in db.get("vouchers", {}):
            await update.message.reply_text(f"❌ Mã *{code}* không tồn tại! Dùng /addvoucher để tạo mới.", parse_mode="Markdown")
            return
        db["vouchers"][code]["amount"] = amount
        db["vouchers"][code]["limit"] = limit
        save_db(db)
        await update.message.reply_text(
            f"✅ Đã cập nhật voucher *{code}*\n💰 Giảm: {amount:,}đ\n🔢 Giới hạn: {limit} lần",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ /setvoucher <code> <số_tiền_giảm> <giới_hạn>")

async def refund(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        order_id = ctx.args[0].upper()
        db = load_db()
        order = next((o for o in db["orders"] if o["id"] == order_id), None)
        if not order:
            await update.message.reply_text(f"❌ Không tìm thấy đơn *{order_id}*!", parse_mode="Markdown")
            return
        if order.get("refunded"):
            await update.message.reply_text(f"❌ Đơn *{order_id}* đã được hoàn tiền rồi!", parse_mode="Markdown")
            return
        u = get_user(db, order["user"])
        u["balance"] += order["price"]
        order["refunded"] = True
        order["status"] = "Đã hoàn tiền"
        save_db(db)
        await update.message.reply_text(
            f"✅ Hoàn tiền đơn *{order_id}*\n👤 User: {order['username']}\n💰 Hoàn: {order['price']:,}đ",
            parse_mode="Markdown")
        try:
            await ctx.bot.send_message(int(order["user"]),
                f"💰 *HOÀN TIỀN ĐƠN #{order_id}*\n\n"
                f"Đơn hàng của bạn đã được hoàn tiền *{order['price']:,}đ*!\n"
                f"💳 Số dư hiện tại: *{u['balance']:,}đ*",
                parse_mode="Markdown")
        except: pass
    except:
        await update.message.reply_text("❌ /refund <order_id>\nVí dụ: /refund VT0001")

async def listusers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    db = load_db()
    users = db.get("users", {})
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    text = f"👥 *DANH SÁCH USERS* ({len(users)} người)\n━━━━━━━━━━━━━━━━━━━━\n"
    for uid, u in list(users.items())[-20:]:
        status = "🔒" if u.get("banned") else "✅"
        text += f"{status} *{u['name']}* (ID: `{uid}`)\n"
        text += f"   💳 {u['balance']:,}đ | 📦 {len(u.get('orders',[]))} đơn\n"
    if len(users) > 20:
        text += f"\n_(Hiển thị 20/{len(users)} users mới nhất)_"
    await update.message.reply_text(text, parse_mode="Markdown")

async def post_init(app):
    from telegram import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
    user_commands = [
        BotCommand("start",    "🏠 Menu chính"),
        BotCommand("lichsu",   "📋 Lịch sử đơn hàng"),
        BotCommand("mystats",  "📊 Thống kê cá nhân"),
        BotCommand("myref",    "🎁 Giới thiệu bạn bè"),
    ]
    admin_commands = user_commands + [
        BotCommand("addmoney",      "💰 Cộng tiền user"),
        BotCommand("removemoney",   "💸 Trừ tiền user"),
        BotCommand("addproduct",    "➕ Thêm sản phẩm"),
        BotCommand("deleteproduct", "🗑 Xóa sản phẩm"),
        BotCommand("addstock",      "📦 Thêm stock"),
        BotCommand("setprice",      "🏷 Đổi giá sản phẩm"),
        BotCommand("addvoucher",    "🎫 Tạo voucher"),
        BotCommand("setvoucher",    "✏️ Sửa voucher"),
        BotCommand("refund",        "↩️ Hoàn tiền đơn hàng"),
        BotCommand("ban",           "🔒 Khóa/mở tài khoản"),
        BotCommand("listusers",     "👥 Danh sách users"),
        BotCommand("listproducts",  "📋 Danh sách sản phẩm"),
        BotCommand("broadcast",     "📢 Gửi thông báo"),
        BotCommand("stats",         "📊 Thống kê hệ thống"),
        BotCommand("maintenance",   "🔧 Bật/tắt bảo trì"),
        BotCommand("setshop",       "🏪 Đổi tên shop"),
        BotCommand("setspin",       "🎡 Cài vòng quay"),
        BotCommand("setdice",       "🎲 Cài xúc xắc"),
        BotCommand("adminhelp",     "🛠 Trợ giúp admin"),
    ]
    await app.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_ID))

# ══════════════════════════════
# MAIN
# ══════════════════════════════
def main():
    init_db()
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    # User commands
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("lichsu",  lambda u,c: button_redirect(u,c,"orders")))
    app.add_handler(CommandHandler("mystats", lambda u,c: button_redirect(u,c,"profile")))
    app.add_handler(CommandHandler("myref",   lambda u,c: button_redirect(u,c,"earn")))
    # Admin commands
    app.add_handler(CommandHandler("addmoney",       addmoney))
    app.add_handler(CommandHandler("removemoney",    removemoney))
    app.add_handler(CommandHandler("addproduct",     addproduct))
    app.add_handler(CommandHandler("addstock",       addstock))
    app.add_handler(CommandHandler("addvoucher",     addvoucher))
    app.add_handler(CommandHandler("setvoucher",     setvoucher))
    app.add_handler(CommandHandler("deleteproduct",  deleteproduct))
    app.add_handler(CommandHandler("refund",         refund))
    app.add_handler(CommandHandler("listusers",      listusers))
    app.add_handler(CommandHandler("ban",            ban))
    app.add_handler(CommandHandler("broadcast",      broadcast))
    app.add_handler(CommandHandler("stats",          stats))
    app.add_handler(CommandHandler("listproducts",   listproducts))
    app.add_handler(CommandHandler("maintenance",    maintenance))
    app.add_handler(CommandHandler("adminhelp",      adminhelp))
    app.add_handler(CommandHandler("setshop",        setshop))
    app.add_handler(CommandHandler("setprice",       setprice))
    app.add_handler(CommandHandler("setspin",        setspin))
    app.add_handler(CommandHandler("setdice",        setdice))
    # Handlers
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print(f"🤖 {SHOP_NAME} Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()

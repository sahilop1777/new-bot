import json, qrcode, random, string
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8554584004:AAHpWmiz14A3ZCaf8rM6-DP6n34DOnZ7iFc"
ADMIN_IDS = [6416481890, 5043245237]
UPI_ID = "paytm.s1vdd6n@pty"

# 🔒 FORCE JOIN BOTH CHANNELS
FORCE_CHANNELS = ["@voucher_zone", "@voucher_zone"]

SHEIN_PRICES = {"500":8,"1000":110,"2000":200,"4000":330}
BB_PRICES = {"1":15,"5":13,"10":13,"20":13}

user_state = {}
pending_payments = {}

# ---------------- FILE HELPERS ----------------

def load_json(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_data(): return load_json("data.json", {"shein":{}, "bigbasket":{}, "free":[]})
def save_data(d): save_json("data.json", d)

def load_orders(): return load_json("orders.json", {})
def save_orders(d): save_json("orders.json", d)

def load_users(): return load_json("users.json", [])
def save_users(d): save_json("users.json", d)

def load_points(): return load_json("points.json", {})
def save_points(d): save_json("points.json", d)

def load_refs(): return load_json("referrals.json", {})
def save_refs(d): save_json("referrals.json", d)

def load_rewarded(): return load_json("rewarded.json", [])
def save_rewarded(d): save_json("rewarded.json", d)

def load_lottery(): return load_json("lottery.json", {})
def save_lottery(d): save_json("lottery.json", d)

# ---------------- UTIL ----------------

def generate_lottery_token():
    return "GL-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ---------------- MAIN MENU ----------------

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
        [["🛍 Shein", "⭐ My Points"],
         ["🎁 Refer & Earn", "📦 My Orders"],
         ["🎉 Free Code", "🆘 Support"],
         ["🎟 Free Giveaway "]],
        resize_keyboard=True
    )

    if update.message:
        await update.message.reply_text("Welcome! Choose option:", reply_markup=kb)
    else:
        await update.callback_query.message.reply_text("Welcome! Choose option:", reply_markup=kb)

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    args = context.args

    users = load_users()
    if uid not in users:
        users.append(uid)
        save_users(users)

    refs = load_refs()

    # ---------- REFERRAL CAPTURE ----------
    if args:
        try:
            ref = int(args[0])

            if ref != uid and str(uid) not in refs:
                refs[str(uid)] = ref
                save_refs(refs)

                try:
                    await context.bot.send_message(
                        ref,
                        "👀 Someone opened your referral link!\n\n"
                        "They must join both channels & verify to get +2 points."
                    )
                except:
                    pass
        except:
            pass

    # ---------- FORCE JOIN CHECK (2 CHANNELS) ----------
    try:
        for ch in FORCE_CHANNELS:
            m = await context.bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                raise Exception()

        await show_main_menu(update, context)

    except:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel 1", url="https://t.me/voucher_zone")],
            [InlineKeyboardButton("Verify", callback_data="verify")]
        ])
        await update.message.reply_text("Join both channels & verify:", reply_markup=kb)

# ---------------- VERIFY ----------------

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.callback_query.from_user.id

    try:
        for ch in FORCE_CHANNELS:
            m = await context.bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                await update.callback_query.answer("Join both channels first!", show_alert=True)
                return

        refs = load_refs()
        points = load_points()
        rewarded = load_rewarded()

        if str(uid) in refs and str(uid) not in rewarded:
            referrer = refs[str(uid)]
            points[str(referrer)] = points.get(str(referrer), 0) + 2
            save_points(points)

            rewarded.append(str(uid))
            save_rewarded(rewarded)

            try:
                await context.bot.send_message(
                    referrer,
                    "🎉 Referral Successful!\n⭐ +2 points added!"
                )
            except:
                pass

        await update.callback_query.message.delete()
        await show_main_menu(update, context)

    except:
        await update.callback_query.answer("Verification failed", show_alert=True)

# ---------------- GOLDEN LOTTERY ----------------

async def golden_lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = (
        "🎟 Golden Lottery Rules\n\n"
        "• Entry Fee: ₹3\n"
        "• Prize Pool: Shein 500 Code\n"
        "• Each user gets a unique token ID\n"
        "• 10-20 Winners announced later\n\n"
        "Click below to participate 👇"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Get Lottery", callback_data="lottery_pay")]
    ])

    await update.message.reply_text(rules, reply_markup=kb)


async def lottery_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi = f"upi://pay?pa={UPI_ID}&pn=GoldenLottery&am=3"
    img = qrcode.make(upi)
    path = f"lottery_{update.effective_user.id}.png"
    img.save(path)

    user_state[update.effective_user.id] = "LOTTERY_SCREENSHOT"

    await update.callback_query.message.reply_photo(
        photo=open(path, "rb"),
        caption="Pay ₹3 for Golden Lottery\n\n📸 Send payment screenshot after payment."
    )

# ---------------- SCREENSHOT ----------------

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.effective_user:
        return  # SAFETY CHECK

    uid = update.effective_user.id
    state = user_state.get(uid)

    if state not in ["WAITING_SCREENSHOT", "LOTTERY_SCREENSHOT"]:
        return

    photo = update.message.photo[-1].file_id
    username = update.effective_user.username or "NoUsername"

    # 🎟 LOTTERY PAYMENT
    if state == "LOTTERY_SCREENSHOT":
        pending_payments[uid] = {
            "service": "lottery",
            "approved": False,
            "username": username
        }

        msg = (
            "🎟 Golden Lottery Payment\n"
            f"User: {uid}\n"
            f"Username: @{username}"
        )

    # 🛍 SHEIN / BIGBASKET PAYMENT
    else:
        service = context.user_data.get("service")
        qty = context.user_data.get("qty", 1)
        amt = context.user_data.get("shein_amt")

        # Create full service name like "Shein 500"
        service_name = f"{service.capitalize()} {amt}"

        pending_payments[uid] = {
            "service": service,
            "service_name": service_name,
            "qty": qty,
            "amt": amt,
            "approved": False
        }

        msg = (
            "🧾 New Payment\n"
            f"User: {uid}\n"
            f"Username: @{username}\n\n"
            f"Service: {service_name}\n"
            f"Qty: {qty}"
        )

    # ✅ Admin Buttons
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{uid}")],
        [InlineKeyboardButton("Reject", callback_data=f"reject_{uid}")]
    ])

    # ✅ Send to all admins
    for admin in ADMIN_IDS:
        await context.bot.send_photo(
            chat_id=admin,
            photo=photo,
            caption=msg,
            reply_markup=kb
        )

    # ✅ Confirm to user
    await update.message.reply_text("⏳ Please wait, admin is verifying...")

# ---------------- REFER & EARN ----------------

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"

    text = (
        "🎁 Refer & Earn\n\n"
        "Share this link:\n"
        f"{link}\n\n"
        "You get 2 points per referral!"
    )

    # If triggered by normal message
    if update.message:
        await update.message.reply_text(text)

    # If triggered by inline button
    elif update.callback_query:
        await update.callback_query.message.reply_text(text)

# ---------------- MY POINTS ----------------

async def my_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    points = load_points()
    p = points.get(str(update.effective_user.id), 0)
    await update.message.reply_text(f"⭐ Your Points: {p}")

# ---------------- FREE CODE ----------------

async def free_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Code - 12 Points", callback_data="free_1")],
        [InlineKeyboardButton("2 Codes - 24 Points", callback_data="free_2")],
        [InlineKeyboardButton("3 Codes - 36 Points", callback_data="free_3")],
        [InlineKeyboardButton("5 Codes - 46 Points", callback_data="free_5")]
    ])
    # Always reply safely
    if update.message:
        await update.message.reply_text(
            "🎉 Redeem Free Codes:",
            reply_markup=kb
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "🎉 Redeem Free Codes:",
            reply_markup=kb
        )

async def free_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.callback_query.answer()
    except:
        return

    qty = int(update.callback_query.data.split("_")[1])
    cost = {1:12, 2:24, 3:36, 5:48}[qty]

    points = load_points()
    uid = str(update.effective_user.id)

    if points.get(uid, 0) < cost:
        await update.callback_query.message.reply_text(
            "❌ Not enough points"
        )
        return

    data = load_data()
    free = data["free"]

    if len(free) < qty:
        await update.callback_query.answer("❌ No free codes left try again tomorrow ", show_alert=True)
        return

    codes = [free.pop(0) for _ in range(qty)]
    points[uid] -= cost

    save_data(data)
    save_points(points)

    await update.callback_query.message.reply_text("🎉 Your Free Codes:\n" + "\n".join(codes))

# ---------- ADMIN PANEL ----------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ Bulk Add", callback_data="admin_bulk")],
        [InlineKeyboardButton("📦 Check Stock", callback_data="admin_stock")]
    ])

    await update.message.reply_text("👑 Admin Panel", reply_markup=kb)

# ---------- ADMIN BUTTONS ----------

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in ADMIN_IDS:
        return

    data = update.callback_query.data

    if data == "admin_broadcast":
        user_state[uid] = "BROADCAST"
        await update.callback_query.message.reply_text("Send broadcast message:")

    elif data == "admin_bulk":
        user_state[uid] = "BULK"
        await update.callback_query.message.reply_text(
            "Send bulk coupons like:\n"
            "/bulk shein 500\n"
            "CODE1\nCODE2\nCODE3"
        )

    elif data == "admin_stock":
        d = load_data()
        orders = load_orders()

        shein = d["shein"]
        bb = d["bigbasket"]
        free = d.get("free", [])

        total_bb = sum(len(v) for v in bb.values())
        total_free_orders = sum(
            1 for u in orders for o in orders[u] if "Free Code" in o
        )

        msg = (
            "📦 LIVE STOCK STATUS\n\n"
            "Shein Coupons\n"
            f"₹500  → {len(shein['500'])}\n"
            f"₹1000 → {len(shein['1000'])}\n"
            f"₹2000 → {len(shein['2000'])}\n"
            f"₹4000 → {len(shein['4000'])}\n\n"
            "BigBasket Coupons\n"
            f"1 Pack  → {len(bb['1'])}\n"
            f"5 Pack  → {len(bb['5'])}\n"
            f"10 Pack → {len(bb['10'])}\n"
            f"20 Pack → {len(bb['20'])}\n\n"
            "Free Codes\n"
            f"Stock → {len(free)}\n"
            f"Redeemed → {total_free_orders}"
        )

        await update.callback_query.message.reply_text(msg)

# ---------- ADMIN TEXT ----------

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return

    uid = update.effective_user.id

    if uid not in ADMIN_IDS:
        return

    state = user_state.get(uid)

    print("ADMIN MESSAGE:", update.message.text)
    print("STATE:", state)

    # ---------- BROADCAST ----------
    if state == "BROADCAST":
        users = load_users()

        print("📢 Broadcast started")
        print("Users loaded:", users)

        sent = 0
        failed = 0

        for u in users:
            try:
                user_id = int(u)

                await context.bot.send_message(
                    chat_id=user_id,
                    text=update.message.text,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )

                sent += 1
                print(f"✅ Sent to {user_id}")

            except Exception as e:
                failed += 1
                print(f"❌ Failed to send to {u} | {e}")

        await update.message.reply_text(
            f"✅ Broadcast Finished\n\n"
            f"Sent: {sent}\n"
            f"Failed: {failed}"
        )

        user_state.pop(uid, None)


# ---------- ADD COUPON ----------

async def add_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        _, service, key, code = update.message.text.split(" ", 3)
        data = load_data()
        data[service][key].append(code)
        save_data(data)
        await update.message.reply_text("Coupon Added ✅")
    except:
        await update.message.reply_text("Use:\n/add shein 500 CODE\n/add bigbasket 1 CODE")


# ---------- BULK ADD (FIXED) ----------

async def bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        lines = update.message.text.split("\n")
        cmd = lines[0].split()

        service = cmd[1].lower()   # shein / bigbasket / free
        key = cmd[2].lower()      # 500 / 1 / any
        codes = lines[1:]

        data = load_data()

        # ✅ FREE CODES
        if service == "free":
            data["free"].extend(codes)
            save_data(data)
            await update.message.reply_text(f"✅ {len(codes)} FREE codes added!")
            return

        # ✅ NORMAL COUPONS
        if service not in data:
            await update.message.reply_text("❌ Invalid service")
            return

        if key not in data[service]:
            data[service][key] = []

        data[service][key].extend(codes)
        save_data(data)

        await update.message.reply_text(f"✅ {len(codes)} coupons added!")

    except Exception as e:
        await update.message.reply_text(
            "❌ Wrong format!\n\n"
            "Use:\n"
            "/bulk shein 500\nCODE1\nCODE2\nCODE3\n\n"
            "/bulk shein 1000\nCODE1\nCODE2\nCODE3\n\n"
            "For free codes:\n"
            "/bulk free any\nFREE1\nFREE2"
        )
        print("Bulk error:", e)

# ---------- SHEIN ----------

async def shein(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    for key in ["500", "1000", "2000", "4000"]:
        if key not in data["shein"]:
            data["shein"][key] = []

    save_data(data)
    s = data["shein"]

    # Prices
    price_500 = 8
    price_1000 = 110
    price_2000 = 200
    price_4000 = 320

    buttons = [
        [InlineKeyboardButton(f"₹500 | ₹{price_500} | Stock: {len(s['500'])}", callback_data="shein_500")],
        [InlineKeyboardButton(f"₹1000 | ₹{price_1000} | Stock: {len(s['1000'])}", callback_data="shein_1000")],
        [InlineKeyboardButton(f"₹2000 | ₹{price_2000} | Stock: {len(s['2000'])}", callback_data="shein_2000")],
        [InlineKeyboardButton(f"₹4000 | ₹{price_4000} | Stock: {len(s['4000'])}", callback_data="shein_4000")]
    ]

    if update.message:
        await update.message.reply_text(
            "Select Shein Amount:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "Select Shein Amount:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
# ---------- BIGBASKET ----------

async def bigbasket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()["bigbasket"]
    buttons = [
        [InlineKeyboardButton("1 - ₹15 per coupon", callback_data="bb_1")],
        [InlineKeyboardButton("5 - ₹13 per coupon", callback_data="bb_5")],
        [InlineKeyboardButton("10 - ₹13 per coupon", callback_data="bb_10")],
        [InlineKeyboardButton("20 - ₹13 per coupon", callback_data="bb_20")]
    ]
    await update.message.reply_text(
        f"📦 Available Stock: {sum(len(v) for v in data.values())}\n\n🛍️ Select how many Bigbasket codes you want to buy:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
# ---------------- QUANTITY MENU ----------------

async def shein_quantity_menu(update, context):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 code", callback_data="sq_1"),
            InlineKeyboardButton("5 codes", callback_data="sq_5")
        ],
        [
            InlineKeyboardButton("10 codes", callback_data="sq_10"),
            InlineKeyboardButton("Other amount", callback_data="sq_other")
        ],
        [InlineKeyboardButton("⬅ Back", callback_data="sq_back")]
    ])

    await update.callback_query.message.reply_text("Select quantity:", reply_markup=kb)

# ---------- QR ----------

async def generate_qr(update, context, price, qty, service):
    total = price * qty
    amt = context.user_data.get("shein_amt", "")

    # Voucher name
    if service == "shein":
        voucher_name = f"Shein {amt} Coupon (Selected)"
    elif service == "bigbasket":
        voucher_name = "BigBasket Coupon (Selected)"
    else:
        voucher_name = "Coupon (Selected)"

    upi = f"upi://pay?pa={UPI_ID}&pn=Coupon&am={total}"

    img = qrcode.make(upi)
    path = f"qr_{update.effective_user.id}.png"
    img.save(path)

    context.user_data["qty"] = qty
    context.user_data["service"] = service
    user_state[update.effective_user.id] = "WAITING_SCREENSHOT"

    caption = (
        f"{voucher_name}\n\n"
        f"Pay ₹{total}\n"
        f"Qty: {qty}\n"
        f"UPI: {UPI_ID}\n\n"
        "📸 Send payment screenshot here 👇"
    )

    if update.callback_query:
        await update.callback_query.message.reply_photo(
            photo=open(path, "rb"),
            caption=caption
        )
    else:
        await update.message.reply_photo(
            photo=open(path, "rb"),
            caption=caption
        )

# ---------- BUTTON HANDLER ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    stock_data = load_data()

    if data.startswith("shein_"):
        amt = data.split("_")[1]

        # Check Shein stock
        available = len(stock_data["shein"].get(amt, []))

        if available == 0:
            await update.callback_query.answer(
                "❌ Stock finished! Please try later.",
                show_alert=True
            )
            return

        context.user_data["shein_amt"] = amt
        context.user_data["service"] = "shein"

        await shein_quantity_menu(update, context)

# ---------------- QUANTITY HANDLER ----------------

async def shein_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "sq_back":
        await shein(update, context)
        return

    if data == "sq_other":
        user_state[update.effective_user.id] = "SHEIN_CUSTOM_QTY"
        await update.callback_query.message.reply_text("Enter custom quantity:")
        return

    qty = int(data.replace("sq_", ""))
    amt = context.user_data.get("shein_amt")
    price = SHEIN_PRICES[amt]

    await generate_qr(update, context, price, qty, "shein")

# ---------------- CUSTOM QTY TEXT ----------------

async def user_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if user_state.get(uid) == "SHEIN_CUSTOM_QTY":
        text = update.message.text.strip()

        # Check if it's a number
        if not text.isdigit():
            await update.message.reply_text("❌ Please enter a number between 1 to 50.")
            return

        qty = int(text)

        # Limit 1–50
        if qty < 1 or qty > 50:
            await update.message.reply_text("❌ Quantity must be between 1 to 50.")
            return

        amt = context.user_data.get("shein_amt")
        price = SHEIN_PRICES[amt]

        user_state.pop(uid)

        await generate_qr(update, context, price, qty, "shein")

# ---------------- ADMIN ACTION ----------------

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action, uid = update.callback_query.data.split("_")
    uid = int(uid)

    if uid not in pending_payments:
        await update.callback_query.answer("Payment not found", show_alert=True)
        return

    if pending_payments[uid].get("approved"):
        await update.callback_query.answer("Already approved ✅", show_alert=True)
        return

    orders = load_orders()
    data = load_data()

    service = pending_payments[uid]["service"]
    qty = pending_payments[uid].get("qty", 1)
    amt = pending_payments[uid].get("amt")  # 500 / 1000 / 2000 / 4000
    username = pending_payments[uid].get("username", "Unknown")

    # ---------------- APPROVE ----------------
    if action == "approve":

        # 🎟 GOLDEN LOTTERY
        if service == "lottery":
            lottery_db = load_lottery()
            token = generate_lottery_token()

            lottery_db[token] = {
                "user_id": uid,
                "username": username
            }
            save_lottery(lottery_db)

            orders.setdefault(str(uid), [])
            orders[str(uid)].append(f"🎟 Golden Lottery Ticket : {token}")
            save_orders(orders)

            pending_payments[uid]["approved"] = True

            await context.bot.send_message(
                uid,
                f"🎉 Golden Lottery Entry Successful!\n\n"
                f"🎫 Your Ticket ID:\n`{token}`",
                parse_mode="Markdown"
            )

            await update.callback_query.message.reply_text("Lottery Approved ✅")
            return

        # 🛍 SHEIN COUPONS
        if service == "shein":
            stock = data["shein"].get(amt, [])

            if len(stock) < qty:
                await context.bot.send_message(uid, "❌ Not enough stock for this amount")
                await update.callback_query.message.reply_text("Out of stock ❌")
                return

            codes = [stock.pop(0) for _ in range(qty)]
            save_data(data)

            orders.setdefault(str(uid), [])
            for code in codes:
                orders[str(uid)].append(f"🛍 Shein ₹{amt} : {code}")

        # 🧺 BIGBASKET COUPONS
        elif service == "bigbasket":
            stock = data["bigbasket"]
            codes = []

            for k in stock:
                while stock[k] and len(codes) < qty:
                    codes.append(stock[k].pop(0))

            if not codes:
                await context.bot.send_message(uid, "❌ Out of stock")
                await update.callback_query.message.reply_text("Out of stock ❌")
                return

            save_data(data)

            orders.setdefault(str(uid), [])
            for code in codes:
                orders[str(uid)].append(f"🧺 BigBasket : {code}")

        # ---------- SAVE & SEND ----------
        save_orders(orders)

        pending_payments[uid]["approved"] = True

        await context.bot.send_message(
            uid,
            "✅ Your Coupon Codes:\n" + "\n".join(codes)
        )

        await update.callback_query.message.reply_text("Approved & Sent ✅")

    # ---------------- REJECT ----------------
    else:
        pending_payments[uid]["approved"] = True
        await context.bot.send_message(uid, "❌ Payment Rejected")
        await update.callback_query.message.reply_text("Rejected ❌")

    user_state.pop(uid, None)



# ---------- MY ORDERS ----------

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = load_orders()
    uid = str(update.effective_user.id)

    if uid not in orders or not orders[uid]:
        await update.message.reply_text("You have no orders yet.")
    else:
        await update.message.reply_text("📦 Your Orders:\n" + "\n".join(orders[uid]))

# ---------- NEW GIVEAWAY ----------

async def new_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎁 *Special Giveaway*\n\n"
        "To participate, you must complete *20 referrals*.\n Prize Pool Is 1000Rs Shein Coupon.\n\n"
        "Use the button below to invite friends 👇"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Refer & Earn", callback_data="go_refer")],
        [InlineKeyboardButton("✅ Check Eligibility", callback_data="check_refs")]
    ])

    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# ---------- GIVEAWAY BUTTON HANDLER ----------

async def giveaway_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    uid = update.effective_user.id

    if data == "go_refer":
        await refer(update, context)

    elif data == "check_refs":
        await update.callback_query.answer(
            "❌ You have not completed 10 referrals yet!",
            show_alert=True
        )


# ---------- SUPPORT ----------

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 Support:\nContact: @voucherzone_support")


# ---------- HANDLERS ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- USER COMMANDS ----------
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_coupon))
app.add_handler(CommandHandler("makecode", makecode))   # Giveaway command

# ---------- ADMIN COMMANDS ----------
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("bulk", bulk_add))

# ---------- CALLBACK BUTTONS ----------
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CallbackQueryHandler(button_handler, pattern="shein_|bb_"))
app.add_handler(CallbackQueryHandler(shein_quantity_handler, pattern="sq_"))
app.add_handler(CallbackQueryHandler(admin_action, pattern="approve_|reject_"))
app.add_handler(CallbackQueryHandler(admin_buttons, pattern="admin_"))
app.add_handler(CallbackQueryHandler(free_handler, pattern="free_"))
app.add_handler(CallbackQueryHandler(lottery_pay, pattern="lottery_pay"))

# Giveaway Buttons
app.add_handler(CallbackQueryHandler(giveaway_buttons, pattern="go_refer|check_refs"))

# ---------- MAIN MENU TEXT BUTTONS ----------
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🛍 Shein$"), shein))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^BigBasket$"), bigbasket))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📦 My Orders$"), my_orders))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🆘 Support$"), support))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎁 Refer & Earn$"), refer))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⭐ My Points$"), my_points))

# IMPORTANT: Giveaway FIRST
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎟 Free Giveaway$"), makebonus))

# Then Free Code
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🎉 Free Code$"), free_code))

app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Golden"), golden_lottery))

# ---------- CUSTOM QTY TEXT ----------
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_text_handler))

# ---------- ADMIN TEXT INPUT ----------
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_IDS), admin_text)
)

# ---------- SCREENSHOT ----------
app.add_handler(MessageHandler(filters.PHOTO, receive_screenshot))

print("Bot Running...")
app.run_polling()

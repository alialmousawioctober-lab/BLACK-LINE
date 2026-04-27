import disnake
from disnake.ext import commands
import json, os

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"

# =====================
# DATABASE
# =====================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =====================
# USER
# =====================
def get_user(gid, uid):
    db = load(BANK_FILE)
    gid, uid = str(gid), str(uid)

    if gid not in db:
        db[gid] = {}

    if uid not in db[gid]:
        db[gid][uid] = {"cash": 1000, "bank": 0}
        save(BANK_FILE, db)

    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)

# =====================
# TEST
# =====================
@bot.command()
async def test(ctx):
    await ctx.send("✅ البوت شغال")

# =====================
# حسابي
# =====================
@bot.command(name="حسابي")
async def balance(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)

    embed = disnake.Embed(
        title=f"🏦 حساب {ctx.author.display_name}",
        color=0x2b2d31
    )

    embed.add_field(name="💵 الكاش", value=user["cash"])
    embed.add_field(name="🏦 البنك", value=user["bank"])
    embed.add_field(name="📊 المجموع", value=user["cash"] + user["bank"])

    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

# =====================
# المخالفات
# =====================
VIOLATIONS = [
    ("زره", "500"),
    ("قطع اشاره", "3000"),
    ("عكس سير متعمد", "منع يومين"),
    ("سحب جلنط متقصد", "1000"),
    ("سرعه 75 الى 80", "منع يومين"),
    ("سرعه 81 الى 90 ميل", "منع ثلاث ايام"),
    ("سرعه 90 و فوق", "منع خمس ايام"),
    ("تجاوز سيارات", "1000"),
    ("هروب من عسكري", "باند"),
    ("تطلع الرصيف", "500"),
    ("عدم وجود لوحه و ماعندك تصريح", "3000"),
    ("التفحيط", "4500"),
    ("مركبه سبورت و ماشريت تصريح", "3000"),
    ("تديور على خط اصفر", "1000"),
    ("عدم تشغيل اضواء", "500"),
    ("لوحه مميزه و ما معك تصريح", "3000"),
]

class Select(disnake.ui.Select):
    def __init__(self, member):
        options = [
            disnake.SelectOption(label=v[0], description=f"العقوبة: {v[1]}")
            for v in VIOLATIONS
        ]
        super().__init__(placeholder="اختر المخالفة...", options=options)
        self.member = member

    async def callback(self, inter):
        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(self.member.id)

        if gid not in db:
            db[gid] = {}
        if uid not in db[gid]:
            db[gid][uid] = []

        selected = self.values[0]
        fine = next(v[1] for v in VIOLATIONS if v[0] == selected)

        db[gid][uid].append({"type": selected, "fine": fine})
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(
            title="🚨 تم تسجيل مخالفة",
            color=0xff0000
        )

        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="📄 المخالفة", value=selected)
        embed.add_field(name="⚖️ العقوبة", value=fine)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class View(disnake.ui.View):
    def __init__(self, member):
        super().__init__()
        self.add_item(Select(member))

@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):
    await ctx.send("اختر نوع المخالفة:", view=View(member))

# =====================
# تسديد
# =====================
@bot.command(name="تسديد")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid]:
        return await ctx.send("❌ ما عندك مخالفات")

    fines = [v for v in db[gid][uid] if str(v["fine"]).isdigit()]
    total = sum(int(v["fine"]) for v in fines)

    user = get_user(ctx.guild.id, ctx.author.id)

    if user["bank"] < total:
        return await ctx.send("❌ البنك ما يكفي")

    user["bank"] -= total
    update_user(ctx.guild.id, ctx.author.id, user)

    db[gid][uid] = []
    save(VIOLATION_FILE, db)

    await ctx.send(f"✅ تم دفع {total}")

# =====================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

# =====================
@bot.event
async def on_ready():
    print("Bot Ready")

bot.run(os.getenv("TOKEN"))

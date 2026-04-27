import disnake
from disnake.ext import commands
import json, os, datetime

intents = disnake.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"
SALARY_AMOUNT = 500

# =======================
# DATABASE
# =======================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# =======================
# USER (🎁 1000)
# =======================
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

# =======================
# مخالفات (جديدة 🔥)
# =======================
VIOLATIONS = [
    ("زره", 500),
    ("قطع اشاره", 3000),
    ("عكس سير متعمد", "منع يومين"),
    ("سحب جلنط متقصد", 1000),
    ("سرعه 75 الى 80", "منع يومين"),
    ("سرعه 81 الى 90", "منع ثلاث ايام"),
    ("سرعه 90 وفوق", "منع خمس ايام"),
    ("تجاوز سيارات", 1000),
    ("هروب من عسكري", "باند"),
    ("تطلع الرصيف", 500),
    ("عدم وجود لوحه", 3000),
    ("التفحيط", 4500),
    ("مركبه سبورت بدون تصريح", 3000),
    ("تديور خط اصفر", 1000),
    ("عدم تشغيل اضواء", 500),
    ("لوحه مميزه بدون تصريح", 3000),
]

# =======================
# SELECT
# =======================
class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, image):
        options = [disnake.SelectOption(label=v[0], description=str(v[1])) for v in VIOLATIONS]
        super().__init__(placeholder="اختر المخالفة...", options=options)
        self.member = member
        self.image = image

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

        embed = disnake.Embed(title="🚨 تم تسجيل مخالفة", color=0xff0000)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="📄 المخالفة", value=selected)
        embed.add_field(name="💰 العقوبة", value=str(fine))

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class ViolationView(disnake.ui.View):
    def __init__(self, member, image):
        super().__init__()
        self.add_item(ViolationSelect(member, image))

# =======================
# اعطاء مخالفة
# =======================
@bot.command(name="اعطاء مخالفة")
async def violation(ctx, member: disnake.Member):
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(title="🚓 نظام المخالفات")
    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=ViolationView(member, image))

# =======================
# تسديد مخالفاتي
# =======================
@bot.command(name="تسديد مخالفاتي")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid] or not db[gid][uid]:
        return await ctx.send("❌ ما عندك مخالفات")

    total = sum(v["fine"] for v in db[gid][uid] if isinstance(v["fine"], int))
    user = get_user(ctx.guild.id, ctx.author.id)

    if user["bank"] < total:
        return await ctx.send("❌ البنك ما يكفي")

    user["bank"] -= total
    update_user(ctx.guild.id, ctx.author.id, user)

    db[gid][uid] = []
    save(VIOLATION_FILE, db)

    await ctx.send(f"✅ تم دفع {total}")

# =======================
# حسابي الشخصي
# =======================
@bot.command(name="حسابي الشخصي")
async def balance(ctx, member: disnake.Member=None):
    if not member:
        member = ctx.author

    data = get_user(ctx.guild.id, member.id)

    embed = disnake.Embed(
        title=f"🏦 مصرف الراجحي | {member.display_name}",
        color=0x2b2d31
    )

    embed.add_field(name="💵 الكاش", value=data["cash"])
    embed.add_field(name="🏦 البنك", value=data["bank"])
    embed.add_field(name="📊 المجموع", value=data["cash"]+data["bank"])

    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# =======================
# تشغيل
# =======================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(os.getenv("TOKEN"))

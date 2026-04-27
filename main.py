import disnake
from disnake.ext import commands
import json, os

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"

# ===================== DATABASE =====================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ===================== USER =====================
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

# ===================== مخالفات =====================
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
    ("عدم وجود لوحه", "3000"),
    ("التفحيط", "4500"),
    ("مركبه سبورت بدون تصريح", "3000"),
    ("تديور خط اصفر", "1000"),
    ("عدم تشغيل اضواء", "500"),
    ("لوحه مميزه بدون تصريح", "3000"),
]

# ===================== اعطاء مخالفة =====================
class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, officer, image):
        options = [disnake.SelectOption(label=v[0]) for v in VIOLATIONS]
        super().__init__(placeholder="اختر المخالفة...", options=options)
        self.member = member
        self.officer = officer
        self.image = image

    async def callback(self, inter):
        selected = self.values[0]
        fine = next(v[1] for v in VIOLATIONS if v[0] == selected)

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(self.member.id)

        db.setdefault(gid, {}).setdefault(uid, [])
        db[gid][uid].append({
            "type": selected,
            "fine": fine,
            "officer": str(self.officer),
            "image": self.image
        })
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="🚨 تم تسجيل مخالفة", color=0xff0000)
        embed.add_field(name="👤 المواطن", value=self.member.mention)
        embed.add_field(name="👮 العسكري", value=self.officer.mention)
        embed.add_field(name="📄 المخالفة", value=selected)
        embed.add_field(name="💰 الغرامة", value=fine)

        if self.image:
            embed.set_image(url=self.image)

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class ViolationView(disnake.ui.View):
    def __init__(self, member, officer, image):
        super().__init__()
        self.add_item(ViolationSelect(member, officer, image))

@bot.command(name="مخالفة")
async def violation(ctx, member: disnake.Member):
    image = None
    if ctx.message.attachments:
        image = ctx.message.attachments[0].url

    embed = disnake.Embed(title="🚓 نظام المخالفات", color=0x2b2d31)
    if image:
        embed.set_image(url=image)

    await ctx.send(embed=embed, view=ViolationView(member, ctx.author, image))

# ===================== تسديد =====================
class PaySelect(disnake.ui.Select):
    def __init__(self, user, violations):
        options = [
            disnake.SelectOption(label=v["type"], description=v["fine"])
            for v in violations
        ]
        super().__init__(placeholder="اختر المخالفة للدفع", options=options)
        self.user = user
        self.violations = violations

    async def callback(self, inter):
        selected = self.values[0]

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(inter.author.id)

        for v in self.violations:
            if v["type"] == selected:
                chosen = v
                break

        if not str(chosen["fine"]).isdigit():
            return await inter.response.send_message("❌ ما تقدر تدفعها", ephemeral=True)

        user_data = get_user(inter.guild.id, inter.author.id)

        if user_data["bank"] < int(chosen["fine"]):
            return await inter.response.send_message("❌ رصيدك ما يكفي", ephemeral=True)

        user_data["bank"] -= int(chosen["fine"])
        update_user(inter.guild.id, inter.author.id, user_data)

        db[gid][uid].remove(chosen)
        save(VIOLATION_FILE, db)

        embed = disnake.Embed(title="✅ تم التسديد", color=0x00ff00)
        embed.add_field(name="👤 المواطن", value=inter.author.mention)
        embed.add_field(name="👮 العسكري", value=chosen["officer"])
        embed.add_field(name="📄 المخالفة", value=chosen["type"])
        embed.add_field(name="💰 الغرامة", value=chosen["fine"])

        if chosen["image"]:
            embed.set_image(url=chosen["image"])

        await inter.message.delete()
        await inter.channel.send(embed=embed)

class PayView(disnake.ui.View):
    def __init__(self, user, violations):
        super().__init__()
        self.add_item(PaySelect(user, violations))

@bot.command(name="تسديد")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid] or not db[gid][uid]:
        return await ctx.send("❌ ما عندك مخالفات")

    embed = disnake.Embed(title="💳 اختر مخالفة للتسديد", color=0x2b2d31)
    await ctx.send(embed=embed, view=PayView(ctx.author, db[gid][uid]))

# =====================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print("Bot Ready")

bot.run(os.getenv("TOKEN"))

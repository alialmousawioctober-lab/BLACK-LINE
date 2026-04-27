import disnake
from disnake.ext import commands
import json, os

intents = disnake.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

BANK_FILE = "bank.json"
VIOLATION_FILE = "violations.json"

# ================= DATABASE =================
def load(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= USER =================
def get_user(gid, uid):
    db = load(BANK_FILE)
    gid, uid = str(gid), str(uid)

    db.setdefault(gid, {})
    if uid not in db[gid]:
        db[gid][uid] = {"cash": 1000, "bank": 0}
        save(BANK_FILE, db)

    return db[gid][uid]

def update_user(gid, uid, data):
    db = load(BANK_FILE)
    db[str(gid)][str(uid)] = data
    save(BANK_FILE, db)

# ================= أوامر البنك =================
@bot.command(name="حسابي")
async def my_account(ctx):
    user = get_user(ctx.guild.id, ctx.author.id)

    embed = disnake.Embed(title="🏦 حسابك", color=0x2b2d31)
    embed.add_field(name="💵 الكاش", value=user["cash"])
    embed.add_field(name="🏦 البنك", value=user["bank"])
    embed.add_field(name="📊 المجموع", value=user["cash"] + user["bank"])
    embed.set_thumbnail(url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command(name="تحويل")
async def transfer(ctx, member: disnake.Member, amount: int):
    sender = get_user(ctx.guild.id, ctx.author.id)
    receiver = get_user(ctx.guild.id, member.id)

    if sender["cash"] < amount:
        return await ctx.send("❌ ما عندك كاش كافي")

    sender["cash"] -= amount
    receiver["cash"] += amount

    update_user(ctx.guild.id, ctx.author.id, sender)
    update_user(ctx.guild.id, member.id, receiver)

    await ctx.send(f"💸 تم تحويل {amount} إلى {member.mention}")

@bot.command(name="ايداع")
async def deposit(ctx, amount: int):
    user = get_user(ctx.guild.id, ctx.author.id)

    if user["cash"] < amount:
        return await ctx.send("❌ ما عندك كاش")

    user["cash"] -= amount
    user["bank"] += amount

    update_user(ctx.guild.id, ctx.author.id, user)

    await ctx.send(f"🏦 تم إيداع {amount}")

@bot.command(name="سحب")
async def withdraw(ctx, amount: int):
    user = get_user(ctx.guild.id, ctx.author.id)

    if user["bank"] < amount:
        return await ctx.send("❌ ما عندك رصيد بالبنك")

    user["bank"] -= amount
    user["cash"] += amount

    update_user(ctx.guild.id, ctx.author.id, user)

    await ctx.send(f"💵 تم سحب {amount}")

# ================= ادارة =================
@bot.command(name="اعطاء")
@commands.has_permissions(administrator=True)
async def give(ctx, member: disnake.Member, amount: int):
    user = get_user(ctx.guild.id, member.id)
    user["cash"] += amount
    update_user(ctx.guild.id, member.id, user)

    await ctx.send(f"💰 تم إعطاء {amount} لـ {member.mention}")

@bot.command(name="حساب-السيرفر")
@commands.has_permissions(administrator=True)
async def server_accounts(ctx):
    db = load(BANK_FILE)
    gid = str(ctx.guild.id)

    if gid not in db:
        return await ctx.send("❌ لا يوجد بيانات")

    embed = disnake.Embed(title="📊 حسابات السيرفر", color=0x2b2d31)

    for uid, data in db[gid].items():
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else uid

        embed.add_field(
            name=name,
            value=f"💵 {data['cash']} | 🏦 {data['bank']}",
            inline=False
        )

    await ctx.send(embed=embed)

# ================= مخالفات =================
VIOLATIONS = [
    ("زره", "500"),
    ("قطع اشاره", "3000"),
    ("عكس سير متعمد", "منع يومين"),
    ("سحب جلنط", "1000"),
]

class ViolationSelect(disnake.ui.Select):
    def __init__(self, member, officer, image):
        options = [
            disnake.SelectOption(label=f"{v[0]} | {v[1]}")
            for v in VIOLATIONS
        ]
        super().__init__(placeholder="اختر المخالفة", options=options)

        self.member = member
        self.officer = officer
        self.image = image

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]
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

# ================= تسديد =================
class PaySelect(disnake.ui.Select):
    def __init__(self, violations):
        options = [
            disnake.SelectOption(label=f"{v['type']} | {v['fine']}")
            for v in violations
        ]
        super().__init__(placeholder="اختر للدفع", options=options)
        self.violations = violations

    async def callback(self, inter):
        selected = self.values[0].split(" | ")[0]

        db = load(VIOLATION_FILE)
        gid = str(inter.guild.id)
        uid = str(inter.author.id)

        for v in self.violations:
            if v["type"] == selected:
                chosen = v
                break

        if not str(chosen["fine"]).isdigit():
            return await inter.response.send_message("❌ ما تقدر تدفعها", ephemeral=True)

        user = get_user(inter.guild.id, inter.author.id)

        if user["bank"] < int(chosen["fine"]):
            return await inter.response.send_message("❌ البنك ما يكفي", ephemeral=True)

        user["bank"] -= int(chosen["fine"])
        update_user(inter.guild.id, inter.author.id, user)

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
    def __init__(self, violations):
        super().__init__()
        self.add_item(PaySelect(violations))

@bot.command(name="تسديد")
async def pay(ctx):
    db = load(VIOLATION_FILE)
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    if gid not in db or uid not in db[gid]:
        return await ctx.send("❌ ما عندك مخالفات")

    embed = disnake.Embed(title="💳 اختر مخالفة للتسديد", color=0x2b2d31)
    await ctx.send(embed=embed, view=PayView(db[gid][uid]))

# =================
@bot.event
async def on_message(message):
    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))

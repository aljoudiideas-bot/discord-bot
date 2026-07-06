import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio
import time
from datetime import datetime, timedelta
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

# ==================== التهيئة ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
    print("📌 تأكد من تعيين المتغير BOT_TOKEN في Render أو جهازك")
    exit(1)
PREFIX = "!"
DATA_FILE = "server_data.json"
LOG_CHANNEL_KEY = "log_channel"
APPLY_CHANNEL_KEY = "apply_channel"
APPLY_ROLE_KEY = "apply_role"

# ==================== إدارة البيانات ====================
def load_data():
    if not os.path.exists(DATA_FILE):
        default = {"levels": {}, "warns": {}, "config": {}}
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== توليد صور الترحيب والوداع ====================
def fix_arabic(text):
    return text

def make_welcome_image(avatar_url, name, guild_name, member_count, is_welcome=True):
    try:
        size = (700, 350)
        bg_color = (32, 34, 46) if is_welcome else (40, 30, 30)
        accent = (88, 101, 242) if is_welcome else (231, 76, 60)
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)
        for i in range(size[0]):
            alpha = i / size[0]
            color = tuple(int(bg_color[j] * (1 - alpha) + accent[j] * alpha * 0.3) for j in range(3))
            draw.line([(i, 0), (i, size[1])], fill=color)
        try:
            req = urllib.request.Request(avatar_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            avatar_data = resp.read()
            avatar_img = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
            avatar_size = 160
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar_img = avatar_img.resize((avatar_size, avatar_size), Image.LANCZOS)
            avatar_pos = (270, 30)
            img.paste(avatar_img, avatar_pos, mask)
            draw.ellipse([avatar_pos[0]-3, avatar_pos[1]-3, avatar_pos[0]+avatar_size+3, avatar_pos[1]+avatar_size+3],
                         outline=accent, width=4)
        except:
            pass
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 22)
        font_bold = ImageFont.truetype("arialbd.ttf", 28)
        text = "اهلا بك!" if is_welcome else "وداعا!"
        draw.text((350, 210), text, fill="white", font=font_large, anchor="mm")
        display_name = (name[:20] + "..") if len(name) > 20 else name
        draw.text((350, 255), display_name, fill=accent, font=font_bold, anchor="mm")
        sub = f"#{member_count}"
        draw.text((350, 295), sub, fill=(180, 180, 180), font=font_small, anchor="mm")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except:
        return None

# ==================== إعدادات البوت ====================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ==================== هيكل السيرفر ====================
ROLES_CONFIG = [
    {"name": "🟢 عضو", "color": 0x2ECC71, "hoist": True, "reason": "الدور الأساسي للأعضاء"},
    {"name": "🔵 عضو نشط", "color": 0x3498DB, "hoist": True, "reason": "للأعضاء النشطين"},
    {"name": "🟣 VIP", "color": 0x9B59B6, "hoist": True, "reason": "أعضاء مميزون"},
    {"name": "🔴 Streamer", "color": 0xE74C3C, "hoist": True, "reason": "للمذيعين"},
    {"name": "🟡 Mod", "color": 0xF1C40F, "hoist": True, "reason": "فريق الإشراف"},
    {"name": "💎 Booster", "color": 0xE91E63, "hoist": True, "reason": "داعمو السيرفر"},
]

CATEGORIES_CONFIG = {
    "📢 الإعلانات والقوانين": {
        "everyone_view": True,
        "channels": [
            {"name": "القوانين", "type": "text", "read_only": True, "topic": "قوانين السيرفر - يرجى القراءة"},
            {"name": "الإعلانات", "type": "text", "read_only": True, "topic": "آخر الإعلانات والتحديثات"},
            {"name": "التحديثات", "type": "text", "read_only": True, "topic": "تحديثات السيرفر"},
        ]
    },
    "💬 التواصل العام": {
        "everyone_view": True,
        "channels": [
            {"name": "الركن-العام", "type": "text", "topic": "للحديث العام والنقاشات"},
            {"name": "التعريف-بنفسك", "type": "text", "topic": "قدم نفسك للأعضاء ❤️"},
            {"name": "الاقتراحات", "type": "text", "topic": "اقتراحاتك لتطوير السيرفر"},
        ]
    },
    "🎮 الألعاب": {
        "everyone_view": True,
        "channels": [
            {"name": "سوالف-الألعاب", "type": "text", "topic": "نقاشات الألعاب"},
            {"name": "تحدث عام", "type": "voice"},
            {"name": "غرفة الألعاب", "type": "voice"},
        ]
    },
    "📺 البث المباشر": {
        "everyone_view": True,
        "channels": [
            {"name": "إعلانات-البث", "type": "text", "read_only": True, "topic": "إعلانات البث المباشر"},
            {"name": "جدول-البث", "type": "text", "topic": "جدول مواعيد البث"},
            {"name": "فيديو-مقترحة", "type": "text", "topic": "اقترح فيديوهات"},
        ]
    },
    "📈 النمو والتفاعل": {
        "everyone_view": False,
        "channels": [
            {"name": "المسابقات", "type": "text", "topic": "مسابقات وجوائز 🏆"},
            {"name": "الرفع-bump", "type": "text", "topic": "استخدم ! bump لرفع السيرفر", "read_only": False},
            {"name": "المشرفين", "type": "text", "topic": "غرفة المشرفين", "mod_only": True},
        ]
    },
}

# ==================== الأحداث ====================
@bot.event
async def on_ready():
    print(f"✅ البوت متصل كـ {bot.user}")
    print(f"🔗 متصل في {len(bot.guilds)} سيرفر")
    for guild in bot.guilds:
        print(f"   - {guild.name} (ID: {guild.id})")
    check_giveaways.start()
    voice_rewards.start()
    bump_reminder.start()
    update_stats.start()
    auto_post_check.start()
    wc_announce.start()
    news_auto.start()

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    data = load_data()
    guild_config = data["config"].get(str(member.guild.id), {})

    auto_role_id = guild_config.get("auto_role")
    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass

    welcome_channel_id = guild_config.get("welcome_channel")
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            embed = discord.Embed(
                title="🎉 عضو جديد انضم إلينا!",
                description=(
                    f"**{member.mention}** أهلاً بك في **{member.guild.name}** 🤍\n\n"
                    f"📌 اقرأ القوانين\n"
                    f"📝 عرّف بنفسك\n"
                    f"🛍️ تسوق من المتجر بـ `!shop`\n"
                    f"💰 اكسب عملات بـ `!daily` و `!weekly`\n"
                    f"🎲 راهن وجرب حظك بـ `!bet`\n\n"
                    f"**أنت العضو رقم #{len(member.guild.members)}** 🎯"
                ),
                color=0x2ECC71
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            banner = data.get("welcome_banner", {}).get(str(member.guild.id))
            if banner:
                embed.set_image(url=banner)
            embed.set_footer(text=f"{member.guild.name} • نحن سعداء بانضمامك")
            try:
                await channel.send(embed=embed)
            except:
                pass

@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    data = load_data()
    guild_config = data["config"].get(str(member.guild.id), {})
    leave_channel_id = guild_config.get("leave_channel")
    if leave_channel_id:
        channel = member.guild.get_channel(leave_channel_id)
        if channel:
            try:
                await channel.send(f"👋 {member.name} غادر السيرفر...")
            except:
                pass
    try:
        farewell = data.get("farewell_msg", {}).get(str(member.guild.id), f"وداعاً {member.name} 🤍 نتمنى لك التوفيق!")
        await member.send(farewell)
    except:
        pass

# ==================== كأس العالم ====================
WC_KEY = "worldcup"
WC_CHANNEL_KEY = "wc_channel"

@bot.command(name="wcsetup")
@commands.has_permissions(administrator=True)
async def wc_setup(ctx, channel: discord.TextChannel = None):
    """إعداد قناة إعلانات كأس العالم: !wcsetup #قناة"""
    if not channel:
        return await ctx.send("❌ استخدم: `!wcsetup #القناة`")
    data = load_data()
    if WC_CHANNEL_KEY not in data:
        data[WC_CHANNEL_KEY] = {}
    data[WC_CHANNEL_KEY][str(ctx.guild.id)] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة كأس العالم: {channel.mention}")

@bot.command(name="wcaddmatch")
@commands.has_permissions(administrator=True)
async def wc_add_match(ctx, team1: str, team2: str, day: int, month: int, hour: int, minute: int = 0):
    """إضافة مباراة: !wcaddmatch السعودية الأرجنتين 20 11 18 00"""
    data = load_data()
    gid = str(ctx.guild.id)
    if WC_KEY not in data:
        data[WC_KEY] = {}
    if gid not in data[WC_KEY]:
        data[WC_KEY][gid] = []
    match = {
        "team1": team1,
        "team2": team2,
        "day": day,
        "month": month,
        "hour": hour,
        "minute": minute,
        "score1": None,
        "score2": None,
        "status": "upcoming"
    }
    data[WC_KEY][gid].append(match)
    save_data(data)
    num = len(data[WC_KEY][gid])
    await ctx.send(f"✅ تم إضافة المباراة #{num}: {team1} vs {team2} ({day}/{month} {hour}:{minute:02d})")

@bot.command(name="wcresult")
@commands.has_permissions(administrator=True)
async def wc_set_result(ctx, num: int, score1: int, score2: int):
    """تسجيل نتيجة مباراة: !wcresult 1 2 1"""
    data = load_data()
    gid = str(ctx.guild.id)
    matches = data.get(WC_KEY, {}).get(gid, [])
    if num < 1 or num > len(matches):
        return await ctx.send("❌ رقم المباراة غير صحيح")
    m = matches[num - 1]
    m["score1"] = score1
    m["score2"] = score2
    m["status"] = "finished"
    save_data(data)
    team = m["team1"] if score1 > score2 else m["team2"] if score2 > score1 else "تعادل"
    await ctx.send(f"✅ تم تسجيل نتيجة المباراة #{num}: {m['team1']} {score1}-{score2} {m['team2']}")

@bot.command(name="wcmatches", aliases=["كأس_العالم"])
async def wc_matches(ctx):
    """عرض مباريات كأس العالم: !wcmatches"""
    data = load_data()
    gid = str(ctx.guild.id)
    matches = data.get(WC_KEY, {}).get(gid, [])
    if not matches:
        return await ctx.send("❌ لا توجد مباريات مسجلة")
    embed = discord.Embed(title="🏆 كأس العالم 2026", color=0xFFD700)
    upcoming = [m for m in matches if m["status"] == "upcoming"]
    finished = [m for m in matches if m["status"] == "finished"]
    if upcoming:
        text = ""
        for i, m in enumerate(upcoming, 1):
            text += f"**#{i}** {m['team1']} vs {m['team2']} — {m['day']}/{m['month']} {m['hour']:02d}:{m['minute']:02d}\n"
        embed.add_field(name="📅 المباريات القادمة", value=text, inline=False)
    if finished:
        text = ""
        for i, m in enumerate(finished, 1):
            text += f"**#{i}** {m['team1']} {m['score1']}-{m['score2']} {m['team2']}\n"
        embed.add_field(name="✅ النتائج", value=text, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="wcremove")
@commands.has_permissions(administrator=True)
async def wc_remove(ctx, num: int):
    """حذف مباراة: !wcremove 1"""
    data = load_data()
    gid = str(ctx.guild.id)
    matches = data.get(WC_KEY, {}).get(gid, [])
    if num < 1 or num > len(matches):
        return await ctx.send("❌ رقم المباراة غير صحيح")
    m = matches.pop(num - 1)
    save_data(data)
    await ctx.send(f"✅ تم حذف المباراة: {m['team1']} vs {m['team2']}")

@bot.command(name="wcclear")
@commands.has_permissions(administrator=True)
async def wc_clear(ctx):
    """مسح كل المباريات: !wcclear"""
    data = load_data()
    gid = str(ctx.guild.id)
    data.setdefault(WC_KEY, {}).pop(gid, None)
    save_data(data)
    await ctx.send("✅ تم مسح جميع المباريات")

# ==================== نظام الأخبار ====================
import feedparser
NEWS_KEY = "news_channel"
NEWS_FEEDS = [
    "https://www.aljazeera.net/aljazeerarss/a7c18e3e-51bc-4f88-a3e0-53a2be01fa8d/73a3b558-70dc-4ff6-95b6-9234dbc74a61",
    "https://www.alarabiya.net/service/arabic/feed/all",
]

@bot.command(name="newssetup")
@commands.has_permissions(administrator=True)
async def news_setup(ctx, channel: discord.TextChannel = None):
    """إعداد قناة الأخبار: !newssetup #قناة"""
    if not channel:
        return await ctx.send("❌ استخدم: `!newssetup #القناة`")
    data = load_data()
    if NEWS_KEY not in data:
        data[NEWS_KEY] = {}
    data[NEWS_KEY][str(ctx.guild.id)] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة الأخبار: {channel.mention}")

@bot.command(name="news")
async def news_manual(ctx):
    """جلب آخر الأخبار يدوي: !news"""
    await ctx.send("📡 جاري جلب الأخبار...")
    count = 0
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:6]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                if title and link:
                    await ctx.send(f"📰 **{title}**\n{link}")
                    count += 1
            break
        except:
            continue
    if count == 0:
        await ctx.send("❌ تعذر جلب الأخبار حالياً")

@tasks.loop(hours=6)
async def news_auto():
    data = load_data()
    for guild in bot.guilds:
        gid = str(guild.id)
        ch_id = data.get(NEWS_KEY, {}).get(gid)
        if not ch_id:
            continue
        ch = guild.get_channel(ch_id)
        if not ch:
            continue
        for feed_url in NEWS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                sent = 0
                for entry in feed.entries[:3]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    if title and link:
                        await ch.send(f"📰 **{title}**\n{link}")
                        sent += 1
                if sent > 0:
                    break
            except:
                continue

@tasks.loop(hours=1)
async def wc_announce():
    data = load_data()
    now = datetime.utcnow()
    for guild in bot.guilds:
        gid = str(guild.id)
        ch_id = data.get(WC_CHANNEL_KEY, {}).get(gid)
        if not ch_id:
            continue
        ch = guild.get_channel(ch_id)
        if not ch:
            continue
        matches = data.get(WC_KEY, {}).get(gid, [])
        for m in matches:
            if m["status"] != "upcoming":
                continue
            match_time = datetime(now.year, m["month"], m["day"], m["hour"], m["minute"])
            diff = (match_time - now).total_seconds()
            if 0 < diff <= 3600:
                try:
                    await ch.send(f"⚽ **قبل ساعة!** {m['team1']} 🆚 {m['team2']}\n{m['day']}/{m['month']} {m['hour']:02d}:{m['minute']:02d}\n@here")
                except:
                    pass

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    guild = member.guild
    gid = str(guild.id)
    data = load_data()
    creator_id = data.get("vc_creator", {}).get(gid)
    temp_ids = set(data.get("temp_vcs", {}).get(gid, []))

    if after.channel and after.channel.id == creator_id:
        cat = after.channel.category
        new_ch = await guild.create_voice_channel(
            name=f"🔊 {member.display_name}",
            category=cat,
            user_limit=5
        )
        await member.move_to(new_ch)
        if "temp_vcs" not in data:
            data["temp_vcs"] = {}
        if gid not in data["temp_vcs"]:
            data["temp_vcs"][gid] = []
        data["temp_vcs"][gid].append(new_ch.id)
        save_data(data)
        await asyncio.sleep(300)
        try:
            if len(new_ch.members) == 0:
                await new_ch.delete()
                data["temp_vcs"][gid].remove(new_ch.id)
                save_data(data)
        except:
            pass

    if before.channel and before.channel.id in temp_ids:
        if len(before.channel.members) == 0:
            try:
                await asyncio.sleep(10)
                if len(before.channel.members) == 0:
                    await before.channel.delete()
                    if before.channel.id in data["temp_vcs"].get(gid, []):
                        data["temp_vcs"][gid].remove(before.channel.id)
                        save_data(data)
            except:
                pass

    # ===== Voice leave message =====
    if before.channel and not after.channel and before.channel.id != creator_id:
        vc_leave_ch = data.get("vc_leave_channel", {}).get(gid)
        if vc_leave_ch:
            ch = guild.get_channel(vc_leave_ch)
            if ch:
                await ch.send(f"👋 مع السلامة **{member.display_name}**")

    STREAM_ANNOUNCE_CACHE = {}

@bot.event
async def on_member_update(before, after):
    if after.bot:
        return
    if after.activity and after.activity.type == discord.ActivityType.streaming and not (before.activity and before.activity.type == discord.ActivityType.streaming):
        gid = str(after.guild.id)
        now = time.time()
        last = STREAM_ANNOUNCE_CACHE.get(after.id, 0)
        if now - last < 3600:
            return
        STREAM_ANNOUNCE_CACHE[after.id] = now
        data = load_data()
        for ch in after.guild.text_channels:
            if "بث" in ch.name or "stream" in ch.name.lower():
                try:
                    embed = discord.Embed(
                        title=f"🔴 {after.display_name} بدأ بث!",
                        description=f"تعال شوف البث الآن!\n{after.activity.url}",
                        color=0xE74C3C
                    )
                    embed.set_thumbnail(url=after.display_avatar.url)
                    await ch.send(f"@everyone", embed=embed)
                except:
                    pass
                break

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        await bot.process_commands(message)
        return

    data = load_data()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # ===== Auto-mod =====
    guild_mod = data.get("automod", {}).get(guild_id, {})
    if guild_mod.get("enabled") and not message.author.guild_permissions.administrator:
        bad_words = guild_mod.get("badwords", [])
        msg_lower = message.content.lower()
        for word in bad_words:
            if word in msg_lower:
                try:
                    await message.delete()
                    await message.channel.send(f"⚠️ {message.author.mention} ممنوع استخدام كلمات سيئة!", delete_after=3)
                except:
                    pass
                break

    # ===== Spam detection =====
    if guild_mod.get("antispam"):
        if "spam_track" not in data:
            data["spam_track"] = {}
        if guild_id not in data["spam_track"]:
            data["spam_track"][guild_id] = {}
        if user_id not in data["spam_track"][guild_id]:
            data["spam_track"][guild_id][user_id] = []
        now_time = time.time()
        data["spam_track"][guild_id][user_id] = [t for t in data["spam_track"][guild_id][user_id] if now_time - t < 5]
        data["spam_track"][guild_id][user_id].append(now_time)
        if len(data["spam_track"][guild_id][user_id]) > 5:
            try:
                await message.delete()
                await message.author.timeout(timedelta(minutes=1), reason="سبام تلقائي")
                await message.channel.send(f"⛔ {message.author.mention} تم كتمك دقيقة بسبب السبام!", delete_after=3)
                data["spam_track"][guild_id][user_id] = []
            except:
                pass

    if guild_id not in data["levels"]:
        data["levels"][guild_id] = {}
    if user_id not in data["levels"][guild_id]:
        data["levels"][guild_id][user_id] = {"xp": 0, "level": 1, "last_xp": 0}

    cooldown = data["levels"][guild_id][user_id].get("last_xp", 0)
    now = datetime.now().timestamp()
    if now - cooldown > 60:
        xp_gain = random.randint(10, 20)
        data["levels"][guild_id][user_id]["xp"] += xp_gain
        data["levels"][guild_id][user_id]["last_xp"] = now

        total_xp = data["levels"][guild_id][user_id]["xp"]
        current_level = data["levels"][guild_id][user_id]["level"]
        needed = current_level * 100

        if total_xp >= needed:
            data["levels"][guild_id][user_id]["level"] += 1
            data["levels"][guild_id][user_id]["xp"] -= needed
            new_level = data["levels"][guild_id][user_id]["level"]

            guild_config = data["config"].get(guild_id, {})
            level_channel_id = guild_config.get("level_channel")
            if level_channel_id:
                channel = message.guild.get_channel(level_channel_id)
                if channel:
                    try:
                        await channel.send(f"🎉 {message.author.mention} وصل للمستوى **{new_level}**!")
                    except:
                        pass

            level_roles = data.get("level_roles", {}).get(guild_id, {})
            if str(new_level) in level_roles:
                role = message.guild.get_role(level_roles[str(new_level)])
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role)
                    except:
                        pass

        coin_gain = random.randint(1, 3)
        if "coins" not in data:
            data["coins"] = {}
        if guild_id not in data["coins"]:
            data["coins"][guild_id] = {}
        if user_id not in data["coins"][guild_id]:
            data["coins"][guild_id][user_id] = 0
        data["coins"][guild_id][user_id] += coin_gain

    # Auto-reply check
    guild_replies = data.get("replies", {}).get(guild_id, {})
    msg_lower = message.content.lower()
    for trigger, response_text in guild_replies.items():
        if trigger in msg_lower:
            try:
                await message.reply(response_text.format(user=message.author.mention))
            except:
                pass
            break

    save_data(data)
    await bot.process_commands(message)

# ==================== أمر إعداد السيرفر ====================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """ينشئ جميع الأدوار والأقسام والقنوات في السيرفر"""
    msg = await ctx.send("⏳ جاري إعداد السيرفر... قد يستغرق دقيقة")
    guild = ctx.guild

    # 1. إنشاء الأدوار
    created_roles = {}
    for rc in ROLES_CONFIG:
        existing = discord.utils.get(guild.roles, name=rc["name"])
        if existing:
            created_roles[rc["name"]] = existing
        else:
            try:
                role = await guild.create_role(
                    name=rc["name"],
                    color=discord.Color(rc["color"]),
                    hoist=rc["hoist"],
                    reason=rc["reason"]
                )
                created_roles[rc["name"]] = role
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"خطأ في إنشاء دور {rc['name']}: {e}")

    # 2. إنشاء الأقسام والقنوات
    for cat_name, cat_cfg in CATEGORIES_CONFIG.items():
        existing_cat = discord.utils.get(guild.categories, name=cat_name)
        if not existing_cat:
            cat_overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=cat_cfg.get("everyone_view", True),
                    connect=cat_cfg.get("everyone_view", True)
                )
            }
            mod_role = created_roles.get("🟡 Mod")
            if mod_role:
                cat_overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    connect=True,
                    speak=True
                )
            try:
                existing_cat = await guild.create_category(cat_name, overwrites=cat_overwrites)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"خطأ في إنشاء قسم {cat_name}: {e}")
                continue

        for ch_cfg in cat_cfg["channels"]:
            ch_name = ch_cfg["name"]
            ch_type = ch_cfg.get("type", "text")
            read_only = ch_cfg.get("read_only", False)
            mod_only = ch_cfg.get("mod_only", False)

            existing_ch = discord.utils.get(existing_cat.channels, name=ch_name)
            if existing_ch:
                continue

            overwrites = {}
            if mod_only:
                overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                mod_role = created_roles.get("🟡 Mod")
                if mod_role:
                    overwrites[mod_role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    )
                streamer_role = created_roles.get("🔴 Streamer")
                if streamer_role:
                    overwrites[streamer_role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    )
            elif read_only:
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=False
                )

            try:
                if ch_type == "voice":
                    await guild.create_voice_channel(ch_name, category=existing_cat)
                else:
                    topic = ch_cfg.get("topic", "")
                    clean_name = ch_name.replace(" ", "-")
                    if overwrites:
                        await guild.create_text_channel(
                            clean_name, category=existing_cat,
                            topic=topic, overwrites=overwrites
                        )
                    else:
                        await guild.create_text_channel(
                            clean_name, category=existing_cat, topic=topic
                        )
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"خطأ في إنشاء قناة {ch_name}: {e}")

    # 3. حفظ الإعدادات الأساسية
    data = load_data()
    if str(guild.id) not in data["config"]:
        data["config"][str(guild.id)] = {}

    for cat in guild.categories:
        for ch in cat.channels:
            if "القوانين" in ch.name:
                data["config"][str(guild.id)]["rules_channel"] = ch.id
            if "الركن-العام" in ch.name or "العام" in ch.name:
                if "قوانين" not in ch.name and "إعلان" not in ch.name:
                    data["config"][str(guild.id)]["general_channel"] = ch.id
            if "التعريف" in ch.name:
                data["config"][str(guild.id)]["intro_channel"] = ch.id

    save_data(data)
    await msg.edit(content="✅ **تم إعداد السيرفر بنجاح!**\nتم إنشاء جميع الأدوار والأقسام والقنوات.")

# ==================== أوامر الإعداد ====================
@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def set_welcome(ctx, channel: discord.TextChannel):
    """تحديد قناة الترحيب: !setwelcome #القناة"""
    data = load_data()
    if str(ctx.guild.id) not in data["config"]:
        data["config"][str(ctx.guild.id)] = {}
    data["config"][str(ctx.guild.id)]["welcome_channel"] = channel.id
    data["config"][str(ctx.guild.id)]["leave_channel"] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة الترحيب: {channel.mention}")

@bot.command(name="setvoicemsg")
@commands.has_permissions(administrator=True)
async def set_voice_msg(ctx, channel: discord.TextChannel = None):
    """تعيين قناة رسائل خروج الروم الصوتي: !setvoicemsg #قناة"""
    if not channel:
        return await ctx.send("❌ استخدم: `!setvoicemsg #القناة`")
    data = load_data()
    gid = str(ctx.guild.id)
    if "vc_leave_channel" not in data:
        data["vc_leave_channel"] = {}
    data["vc_leave_channel"][gid] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة رسائل الخروج من الصوت: {channel.mention}")

@bot.command(name="removevoicemsg")
@commands.has_permissions(administrator=True)
async def remove_voice_msg(ctx):
    """إلغاء رسائل خروج الروم الصوتي: !removevoicemsg"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "vc_leave_channel" in data and gid in data["vc_leave_channel"]:
        data["vc_leave_channel"].pop(gid)
        save_data(data)
        await ctx.send("✅ تم إلغاء رسائل الخروج من الصوت")
    else:
        await ctx.send("❌ لا توجد رسائل خروج صوتي مفعلة")

@bot.command(name="setleave")
@commands.has_permissions(administrator=True)
async def set_leave(ctx, channel: discord.TextChannel):
    """تحديد قناة الوداع: !setleave #القناة"""
    data = load_data()
    if str(ctx.guild.id) not in data["config"]:
        data["config"][str(ctx.guild.id)] = {}
    data["config"][str(ctx.guild.id)]["leave_channel"] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة الوداع: {channel.mention}")

@bot.command(name="setwelcomebanner")
@commands.has_permissions(administrator=True)
async def set_welcome_banner(ctx, *, url: str = None):
    """تعيين صورة خلفية للترحيب: !setwelcomebanner رابط_الصورة"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "welcome_banner" not in data:
        data["welcome_banner"] = {}
    if url:
        if "imgur.com" in url and "i.imgur.com" not in url:
            parts = url.split("/")
            file_id = parts[-1].split("?")[0].split(".")[0]
            url = f"https://i.imgur.com/{file_id}.jpg"
        data["welcome_banner"][gid] = url
        save_data(data)
        await ctx.send(f"✅ تم تعيين الصورة: `{url}`\nاستخدم `!previewwelcome` للمعاينة")
    else:
        data["welcome_banner"].pop(gid, None)
        save_data(data)
        await ctx.send(f"✅ تم إزالة صورة الترحيب")

@bot.command(name="setfarewell")
@commands.has_permissions(administrator=True)
async def set_farewell(ctx, *, message: str = None):
    """تعيين رسالة وداع للخاص: !setfarewell وداعاً {name} 🤍"""
    if not message:
        return await ctx.send("❌ اكتب رسالة الوداع\nمثال: `!setfarewell وداعاً {name} 🤍 نتمنى لك التوفيق!`")
    data = load_data()
    if "farewell_msg" not in data:
        data["farewell_msg"] = {}
    data["farewell_msg"][str(ctx.guild.id)] = message
    save_data(data)
    await ctx.send(f"✅ تم تعيين رسالة الوداع\nالرسالة: `{message}`")

@bot.command(name="testfarewell")
@commands.has_permissions(administrator=True)
async def test_farewell(ctx, member: discord.Member = None):
    """اختبار رسالة الوداع: !testfarewell @عضو"""
    if not member:
        member = ctx.author
    data = load_data()
    farewell = data.get("farewell_msg", {}).get(str(ctx.guild.id), f"وداعاً {member.name} 🤍 نتمنى لك التوفيق!")
    try:
        await member.send(f"🧪 **اختبار رسالة الوداع**\n{farewell.replace('{name}', member.name)}")
        await ctx.send(f"✅ تم إرسال اختبار الوداع لـ {member.mention}")
    except:
        await ctx.send(f"❌ ما قدرت أوصل {member.mention}\nتأكد إن الخاص مفتوح عنده")

@bot.command(name="previewwelcome")
@commands.has_permissions(administrator=True)
async def preview_welcome(ctx):
    """معاينة رسالة الترحيب: !previewwelcome"""
    member = ctx.author
    embed = discord.Embed(
        title="🎉 عضو جديد انضم إلينا!",
        description=(
            f"**{member.mention}** أهلاً بك في **{member.guild.name}** 🤍\n\n"
            f"📌 اقرأ القوانين\n"
            f"📝 عرّف بنفسك\n"
            f"🛍️ تسوق من المتجر بـ `!shop`\n"
            f"💰 اكسب عملات بـ `!daily` و `!weekly`\n"
            f"🎲 راهن وجرب حظك بـ `!bet`\n\n"
            f"**أنت العضو رقم #{len(member.guild.members)}** 🎯"
        ),
        color=0x2ECC71
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    data = load_data()
    banner = data.get("welcome_banner", {}).get(str(ctx.guild.id))
    if banner:
        embed.set_image(url=banner)
    embed.set_footer(text=f"{member.guild.name} • نحن سعداء بانضمامك")
    await ctx.send(embed=embed)

@bot.command(name="setservericon")
@commands.has_permissions(administrator=True)
async def set_server_icon(ctx, *, url: str):
    """تغيير صورة السيرفر: !setservericon رابط_الصورة"""
    if "imgur.com" in url and "i.imgur.com" not in url:
        parts = url.split("/")
        file_id = parts[-1].split("?")[0].split(".")[0]
        url = f"https://i.imgur.com/{file_id}.png"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            image_data = resp.read()
        await ctx.guild.edit(icon=image_data)
        await ctx.send(f"✅ تم تغيير صورة السيرفر!")
    except Exception as e:
        await ctx.send(f"❌ فشل: {e}")

@bot.command(name="setautorole")
@commands.has_permissions(administrator=True)
async def set_auto_role(ctx, *, role_name: str):
    """تحديد الدور التلقائي: !setautorole اسم_الدور"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        roles_list = "\n".join(f"• {r.name}" for r in ctx.guild.roles if not r.is_default())
        return await ctx.send(f"❌ الدور '{role_name}' غير موجود\nالأدوار المتاحة:\n{roles_list}")
    data = load_data()
    if str(ctx.guild.id) not in data["config"]:
        data["config"][str(ctx.guild.id)] = {}
    data["config"][str(ctx.guild.id)]["auto_role"] = role.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين الدور التلقائي: {role.name}")

@bot.command(name="setlevel")
@commands.has_permissions(administrator=True)
async def set_level_channel(ctx, channel: discord.TextChannel):
    """تحديد قناة إعلانات المستويات: !setlevel #القناة"""
    data = load_data()
    if str(ctx.guild.id) not in data["config"]:
        data["config"][str(ctx.guild.id)] = {}
    data["config"][str(ctx.guild.id)]["level_channel"] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين قناة المستويات: {channel.mention}")

# ==================== أوامر الإشراف ====================
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="بدون سبب"):
    """طرد عضو: !kick @العضو السبب"""
    data = load_data()
    farewell = data.get("farewell_msg", {}).get(str(ctx.guild.id), f"وداعاً {member.name} 🤍 نتمنى لك التوفيق!")
    try:
        await member.send(farewell.replace("{name}", member.name))
    except:
        pass
    await member.kick(reason=reason)
    await ctx.send(f"👢 تم طرد {member.mention}\nالسبب: {reason}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="بدون سبب"):
    """حظر عضو: !ban @العضو السبب"""
    data = load_data()
    farewell = data.get("farewell_msg", {}).get(str(ctx.guild.id), f"وداعاً {member.name} 🤍 نتمنى لك التوفيق!")
    try:
        await member.send(farewell.replace("{name}", member.name))
    except:
        pass
    await member.ban(reason=reason)
    await ctx.send(f"🔨 تم حظر {member.mention}\nالسبب: {reason}")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """مسح رسائل: !clear عدد"""
    if amount < 1 or amount > 100:
        return await ctx.send("❌ العدد يجب أن يكون بين 1 و 100")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم مسح {len(deleted) - 1} رسالة")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="cleanall")
@commands.has_permissions(administrator=True)
async def clean_all(ctx):
    """مسح كل القنوات النصية (يحتفظ بالمثبتات): !cleanall"""
    await ctx.send("🧹 جاري تنظيف السيرفر...", delete_after=3)
    count = 0
    for channel in ctx.guild.text_channels:
        try:
            deleted = await channel.purge(limit=500, check=lambda m: not m.pinned)
            count += len(deleted)
        except:
            pass
    await ctx.send(f"✅ تم مسح **{count}** رسالة من جميع القنوات\nالمثبتات باقية 🔒", delete_after=10)

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="بدون سبب"):
    """تحذير عضو: !warn @العضو السبب"""
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    if guild_id not in data["warns"]:
        data["warns"][guild_id] = {}
    if user_id not in data["warns"][guild_id]:
        data["warns"][guild_id][user_id] = []

    warn_info = {
        "reason": reason,
        "by": ctx.author.id,
        "date": datetime.now().isoformat()
    }
    data["warns"][guild_id][user_id].append(warn_info)
    save_data(data)

    await ctx.send(
        f"⚠️ تم تحذير {member.mention}\n"
        f"السبب: {reason}\n"
        f"عدد التحذيرات: {len(data['warns'][guild_id][user_id])}"
    )

@bot.command(name="warns")
@commands.has_permissions(kick_members=True)
async def warns(ctx, member: discord.Member):
    """عرض تحذيرات عضو: !warns @العضو"""
    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    user_warns = data["warns"].get(guild_id, {}).get(user_id, [])
    if not user_warns:
        return await ctx.send(f"✅ {member.mention} لا يوجد له تحذيرات")

    embed = discord.Embed(
        title=f"⚠️ سجل تحذيرات {member.display_name}",
        description=f"إجمالي التحذيرات: **{len(user_warns)}**",
        color=0xE74C3C
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    for i, w in enumerate(user_warns[:10], 1):
        mod = ctx.guild.get_member(w["by"])
        mod_name = mod.display_name if mod else "غير معروف"
        embed.add_field(
            name=f"⚠️ تحذير #{i}",
            value=(
                f"```📝 {w['reason']}```"
                f"👮 {mod_name} | 📅 {w['date'][:10]}"
            ),
            inline=False
        )
    if len(user_warns) > 10:
        embed.set_footer(text=f"وعنده {len(user_warns) - 10} تحذيرات أخرى")
    await ctx.send(embed=embed)

# ==================== أوامر المستويات ====================
@bot.command(name="level")
async def level(ctx, member: discord.Member = None):
    """عرض مستوى عضو: !level @العضو"""
    if member is None:
        member = ctx.author

    data = load_data()
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    user_data = data["levels"].get(guild_id, {}).get(user_id, {"xp": 0, "level": 1})
    lvl = user_data["level"]
    xp = user_data["xp"]
    needed = lvl * 100

    embed = discord.Embed(
        title=f"مستوى {member.display_name}",
        color=0x3498DB
    )
    embed.add_field(name="🎯 المستوى", value=str(lvl), inline=True)
    embed.add_field(name="⚡ XP", value=f"{xp}/{needed}", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    """بطاقة رتبة احترافية: !rank @العضو"""
    if member is None:
        member = ctx.author
    data = load_data()
    guild_id = str(ctx.guild.id)
    uid = str(member.id)
    user_data = data["levels"].get(guild_id, {}).get(uid, {"xp": 0, "level": 1})
    lvl = user_data["level"]
    xp = user_data["xp"]
    needed = lvl * 100
    pct = min(xp / needed, 1.0)

    img = Image.new("RGB", (600, 200), (30, 32, 43))
    draw = ImageDraw.Draw(img)
    for i in range(200):
        c = int(30 + (i / 200) * 15)
        draw.line([(0, i), (600, i)], fill=(c, c-2, c-8))
    try:
        req = urllib.request.Request(str(member.display_avatar.url), headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        avatar_img = Image.open(io.BytesIO(resp.read())).convert("RGBA")
        mask = Image.new("L", (120, 120), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 120, 120), fill=255)
        avatar_img = avatar_img.resize((120, 120), Image.LANCZOS)
        img.paste(avatar_img, (40, 40), mask)
    except:
        pass

    font_name = ImageFont.truetype("arialbd.ttf", 28)
    font_lvl = ImageFont.truetype("arialbd.ttf", 22)
    font_xp = ImageFont.truetype("arial.ttf", 18)

    draw.text((190, 45), member.display_name[:25], fill=(255, 255, 255), font=font_name)
    draw.text((190, 85), f"Level {lvl}", fill=(88, 101, 242), font=font_lvl)

    bar_x, bar_y, bar_w, bar_h = 190, 120, 370, 20
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=(60, 60, 80))
    fill_w = int(bar_w * pct)
    if fill_w > 0:
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], fill=(88, 101, 242))
    draw.text((bar_x, bar_y + bar_h + 5), f"{xp} / {needed} XP", fill=(180, 180, 180), font=font_xp)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    file = discord.File(buf, filename="rank.png")
    await ctx.send(file=file)

@bot.command(name="setlevelrole")
@commands.has_permissions(administrator=True)
async def set_level_role(ctx, level: int, *, role_name: str):
    """ربط رتبة بمستوى: !setlevelrole 5 🔵 عضو نشط"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ الرتبة '{role_name}' غير موجودة")
    data = load_data()
    gid = str(ctx.guild.id)
    if "level_roles" not in data:
        data["level_roles"] = {}
    if gid not in data["level_roles"]:
        data["level_roles"][gid] = {}
    data["level_roles"][gid][str(level)] = role.id
    save_data(data)
    await ctx.send(f"✅ المستوى **{level}** → رتبة **{role.name}**")

@bot.command(name="removelevelrole")
@commands.has_permissions(administrator=True)
async def remove_level_role(ctx, level: int):
    """حذف ربط رتبة بمستوى: !removelevelrole 5"""
    data = load_data()
    gid = str(ctx.guild.id)
    if data.get("level_roles", {}).get(gid, {}).pop(str(level), None):
        save_data(data)
        await ctx.send(f"✅ تم حذف ربط المستوى {level}")
    else:
        await ctx.send(f"❌ ما في ربط للمستوى {level}")

@bot.command(name="levelroles")
async def list_level_roles(ctx):
    """عرض ربط المستويات بالرتب"""
    data = load_data()
    gid = str(ctx.guild.id)
    roles = data.get("level_roles", {}).get(gid, {})
    if not roles:
        return await ctx.send("📋 لا يوجد ربط مستويات\nالمشرف يستخدم `!setlevelrole مستوى اسم_الرتبة`")
    embed = discord.Embed(title="📋 ربط المستويات بالرتب", color=0x2ECC71)
    for lvl, rid in sorted(roles.items(), key=lambda x: int(x[0])):
        role = ctx.guild.get_role(rid)
        if role:
            embed.add_field(name=f"المستوى {lvl}", value=role.mention, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """ترتيب الأعضاء حسب المستوى"""
    data = load_data()
    guild_id = str(ctx.guild.id)
    guild_data = data["levels"].get(guild_id, {})

    sorted_users = sorted(
        guild_data.items(),
        key=lambda x: (x[1]["level"], x[1]["xp"]),
        reverse=True
    )[:10]

    if not sorted_users:
        return await ctx.send("❌ لا يوجد بيانات مستويات بعد")

    embed = discord.Embed(
        title="🏆 قائمة المتصدرين",
        description="أفضل 10 أعضاء نشاطاً",
        color=0xF1C40F
    )

    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, user_data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else "مغادر"
        medal = medals[i - 1] if i <= 3 else f"#{i}"
        embed.add_field(
            name=f"{medal} {name}",
            value=f"المستوى: {user_data['level']} | XP: {user_data['xp']}",
            inline=False
        )

    await ctx.send(embed=embed)

# ==================== أوامر عامة ====================
@bot.command(name="ping")
async def ping(ctx):
    """سرعة الاتصال"""
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    """إرسال رسالة بواسطة البوت: !say النص"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel_name: str, *, message):
    """إرسال إعلان مع تثبيت: !announce 📢-الإعلانات النص"""
    channel = None
    clean = channel_name.lstrip("#")
    # Handle mention <#ID>
    if clean.startswith("<#") and clean.endswith(">"):
        try:
            cid = int(clean[2:-1])
            channel = ctx.guild.get_channel(cid)
        except:
            pass
    else:
        channel = discord.utils.get(ctx.guild.text_channels, name=clean)
    if not channel:
        channels_list = "\n".join(f"• {c.name}" for c in ctx.guild.text_channels)
        return await ctx.send(f"❌ القناة غير موجودة\nالقنوات النصية:\n{channels_list}")
    await ctx.message.delete()
    msg = await channel.send(f"📢 **إعلان**\n\n{message}")
    try:
        await msg.pin()
    except:
        pass
    await ctx.send(f"✅ تم الإعلان في {channel.mention}", delete_after=5)

@bot.command(name="advertise")
@commands.has_permissions(administrator=True)
async def advertise(ctx, *, message):
    """إعلان في قناة الإعلانات مع تثبيت: !advertise النص"""
    channel = discord.utils.find(lambda c: "إعلان" in c.name, ctx.guild.text_channels)
    if not channel:
        return await ctx.send("❌ لا توجد قناة إعلانات")
    await ctx.message.delete()
    msg = await channel.send(f"📢 **إعلان**\n\n{message}")
    try:
        await msg.pin()
    except:
        pass
    await ctx.send(f"✅ تم الإعلان في {channel.mention} ✨", delete_after=5)

@bot.command(name="setchannelimg")
@commands.has_permissions(administrator=True)
async def set_channel_image(ctx, channel_name: str, *, image_url: str):
    """إرسال وتثبيت صورة بقناة: !setchannelimg اسم_القناة الرابط"""
    channel = discord.utils.find(lambda c: channel_name.lower() in c.name.lower(), ctx.guild.text_channels)
    if not channel:
        return await ctx.send("❌ القناة غير موجودة")
    if "imgur.com" in image_url and "i.imgur.com" not in image_url:
        parts = image_url.split("/")
        file_id = parts[-1].split("?")[0].split(".")[0]
        image_url = f"https://i.imgur.com/{file_id}.png"
    embed = discord.Embed(color=0x2ECC71)
    embed.set_image(url=image_url)
    await ctx.message.delete()
    msg = await channel.send(embed=embed)
    try:
        await msg.pin()
    except:
        pass
    await ctx.send(f"✅ تم نشر الصورة في {channel.mention}", delete_after=5)

# ==================== نظام الحماية ====================
@bot.command(name="antispam")
@commands.has_permissions(administrator=True)
async def anti_spam(ctx, state: str = "on"):
    """تشغيل/إيقاف منع السبام: !antispam on/off"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "automod" not in data:
        data["automod"] = {}
    if gid not in data["automod"]:
        data["automod"][gid] = {}
    data["automod"][gid]["antispam"] = state.lower() == "on"
    data["automod"][gid]["enabled"] = True
    save_data(data)
    await ctx.send(f"✅ الحماية من السبام: {'🟢 مفعلة' if state.lower() == 'on' else '🔴 معطلة'}")

@bot.command(name="addbadword")
@commands.has_permissions(administrator=True)
async def add_bad_word(ctx, *, word: str):
    """إضافة كلمة ممنوعة: !addbadword كلمة"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "automod" not in data:
        data["automod"] = {}
    if gid not in data["automod"]:
        data["automod"][gid] = {}
    if "badwords" not in data["automod"][gid]:
        data["automod"][gid]["badwords"] = []
    data["automod"][gid]["badwords"].append(word.lower())
    data["automod"][gid]["enabled"] = True
    save_data(data)
    await ctx.send(f"✅ تم إضافة كلمة ممنوعة: `{word}`")

@bot.command(name="removebadword")
@commands.has_permissions(administrator=True)
async def remove_bad_word(ctx, *, word: str):
    """حذف كلمة ممنوعة: !removebadword كلمة"""
    data = load_data()
    gid = str(ctx.guild.id)
    words = data.get("automod", {}).get(gid, {}).get("badwords", [])
    if word.lower() in words:
        words.remove(word.lower())
        save_data(data)
        await ctx.send(f"✅ تم حذف كلمة: `{word}`")
    else:
        await ctx.send(f"❌ الكلمة غير موجودة")

@bot.command(name="badwords")
@commands.has_permissions(administrator=True)
async def list_bad_words(ctx):
    """عرض الكلمات الممنوعة"""
    data = load_data()
    gid = str(ctx.guild.id)
    words = data.get("automod", {}).get(gid, {}).get("badwords", [])
    if not words:
        return await ctx.send("📋 لا يوجد كلمات ممنوعة")
    await ctx.send(f"📋 **الكلمات الممنوعة ({len(words)}):**\n" + "\n".join(f"• {w}" for w in words))

ARABIC_BAD_WORDS = [
    "كس", "كسم", "شرموط", "قحبة", "عرص", "متناك", "خول", "زب", "طيز",
    "منيوك", "انيك", "نييك", "لوطي", "سحق", "ولف", "ديث", "سكسي",
    "porn", "sex", "fuck", "shit", "bitch", "asshole", "nigga", "nigger",
    "evil", "devil", "kill yourself", "kys", "suicide", "حرامي", "كلب",
    "حمار", "خنزير", "يا كلب", "يا حمار", "انقلع", "اطرد", "سيب"
]

@bot.command(name="loadbadwords")
@commands.has_permissions(administrator=True)
async def load_bad_words(ctx):
    """تحميل مكتبة كلمات ممنوعة عربية: !loadbadwords"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "automod" not in data:
        data["automod"] = {}
    if gid not in data["automod"]:
        data["automod"][gid] = {}
    if "badwords" not in data["automod"][gid]:
        data["automod"][gid]["badwords"] = []
    existing = set(data["automod"][gid]["badwords"])
    added = 0
    for w in ARABIC_BAD_WORDS:
        if w not in existing:
            data["automod"][gid]["badwords"].append(w)
            added += 1
    data["automod"][gid]["enabled"] = True
    save_data(data)
    await ctx.send(f"✅ تم تحميل {added} كلمة ممنوعة (المجموع: {len(data['automod'][gid]['badwords'])})")

@bot.command(name="help")
async def help_cmd(ctx):
    """عرض قائمة الأوامر"""
    embed = discord.Embed(
        title="📋 قائمة الأوامر",
        description="**البوت العربي المتكامل لإدارة السيرفر**\nاستخدم `!` قبل كل أمر",
        color=0x2ECC71
    )

    embed.add_field(
        name="⚙️ **الإعداد**",
        value=(
            "`!setup` - إعداد السيرفر بالكامل\n"
            "`!setwelcome #قناة` - تعيين قناة الترحيب\n"
            "`!setwelcomebanner رابط` - تعيين صورة ترحيب\n"
            "`!previewwelcome` - معاينة الترحيب\n"
            "`!setautorole @دور` - تعيين الدور التلقائي\n"
            "`!setlevel #قناة` - تعيين قناة المستويات\n"
            "`!setupvc` - إنشاء رومات صوتية مؤقتة\n"
            "`!removevc` - حذف الرومات المؤقتة\n"
            "`!suggestsetup` - إعداد قناة الاقتراحات\n"
            "`!setbump #قناة` - تعيين قناة تذكير البمب"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ **الإشراف**",
        value=(
            "`!kick @عضو سبب` - طرد عضو\n"
            "`!ban @عضو سبب` - حظر عضو\n"
            "`!clear عدد` - مسح رسائل\n"
            "`!warn @عضو سبب` - تحذير عضو\n"
            "`!warns @عضو` - عرض تحذيرات\n"
            "`!fixperms` - ترقية صلاحيات البوت\n"
            "`!advertise نص` - إعلان مثبت\n"
            "`!say نص` - البوت يتكلم\n"
            "`!antispam on/off` - تشغيل منع السبام\n"
            "`!addbadword كلمة` - إضافة كلمة ممنوعة\n"
            "`!removebadword كلمة` - حذف كلمة ممنوعة\n"
            "`!badwords` - عرض الكلمات الممنوعة\n"
            "`!loadbadwords` - تحميل مكتبة عربية جاهزة"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 **المستويات**",
        value=(
            "`!level @عضو` - عرض مستواك\n"
            "`!leaderboard` - قائمة المتصدرين\n"
            "`!setlevelrole مستوى اسم_الرتبة` - ربط رتبة بمستوى (مشرف)\n"
            "`!removelevelrole مستوى` - حذف ربط (مشرف)\n"
            "`!levelroles` - عرض ربط المستويات"
        ),
        inline=False
    )

    embed.add_field(
        name="🎉 **السحوبات**",
        value=(
            "`!gstart 1h 2 جائزة` - بدء سحب\n"
            "`!gend message_id` - إنهاء سحب"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 **التذاكر**",
        value=(
            "`!new سبب` - فتح تذكرة\n"
            "`!close` - إغلاق التذكرة\n"
            "`!adduser @عضو` - إضافة عضو"
        ),
        inline=False
    )

    embed.add_field(
        name="🤝 **الشركاء**",
        value=(
            "`!partnersetup` - إعداد نظام الشركاء\n"
            "`!addpartner @عضو` - إضافة شريك\n"
            "`!removepartner @عضو` - إزالة شريك\n"
            "`!partners` - قائمة الشركاء"
        ),
        inline=False
    )

    embed.add_field(
        name="📅 **الفعاليات**",
        value=(
            "`!addevent اسم تاريخ وصف` - إضافة فعالية\n"
            "`!events` - عرض الفعاليات\n"
            "`!removeevent رقم` - حذف فعالية"
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ **أخرى**",
        value=(
            "`!help` - هذه القائمة\n"
            "`!ping` - سرعة الاتصال\n"
            "`!activities` - أنشطة الرومات\n"
            "`!cmdchannel` - إنشاء قناة أوامر\n"
            "`!addreply كلمة رد` - إضافة رد تلقائي\n"
            "`!removereply كلمة` - حذف رد\n"
            "`!replies` - عرض الردود\n"
             "`!daily` - مكافأة يومية 💰\n"
             "`!weekly` - مكافأة أسبوعية 🎁\n"
            "`!leaderboard` - لوحة المستويات 🏆\n"
            "`!rich` - لوحة الأغنياء 💰\n"
            "`!suggest نص` - إرسال اقتراح 💡\n"
            "`!stats` - إحصائيات السيرفر 📊\n"
            "`!dashboard` - لوحة التحكم 📊\n"
            "`!bet مبلغ` - مضاعفة عملات 🎲\n"
            "`!dice مبلغ` - زهر (4+ ربح) 🎲\n"
            "`!slots مبلغ` - آلة سلوتس 🎰"
        ),
        inline=False
    )

    embed.add_field(
        name="🛒 **المتجر**",
        value=(
            "`!shop` - عرض المتجر\n"
            "`!buy id` - شراء منتج\n"
            "`!balance` - رصيدك\n"
            "`!additem id السعر اسم_الدور` - إضافة منتج (مشرف)\n"
            "`!removeitem id` - حذف منتج (مشرف)\n"
            "`!addcoins 100 @عضو` - إضافة عملات (مشرف)"
        ),
        inline=False
    )

    embed.add_field(
        name="🎨 **الألوان والنقش**",
        value=(
            "`!nick اسم` - تغيير نقشك (VIP)\n"
            "`!setnick @عضو اسم` - تغيير نقش عضو (مشرف)\n"
            "`!colors` - عرض الألوان\n"
            "`!buycolor اسم` - شراء لون\n"
            "`!addcolor اسم #كود السعر` - إضافة لون (مشرف)\n"
            "`!removecolor اسم` - حذف لون (مشرف)"
        ),
        inline=False
    )

    embed.add_field(
        name="💡 **الاقتراحات**",
        value=(
            "`!suggest نص` - إرسال اقتراح\n"
            "`!approve id` - موافقة على اقتراح (مشرف)\n"
            "`!reject id` - رفض اقتراح (مشرف)"
        ),
        inline=False
    )

    embed.add_field(
        name="⭐ **عضو الأسبوع**",
        value=(
            "`!nominate @عضو` - ترشيح عضو\n"
            "`!weekvotes` - عرض التصويتات\n"
            "`!weekwinner @عضو` - إعلان الفائز (مشرف)"
        ),
        inline=False
    )

    embed.set_footer(text=f"{len(bot.commands)} أمر متاح | Made with ❤️")
    await ctx.send(embed=embed)

# ==================== أنشطة الديسكورد ====================
@bot.command(name="activities")
async def activities_info(ctx):
    """قائمة الأنشطة المتاحة في الرومات الصوتية"""
    embed = discord.Embed(
        title="🎮 أنشطة الديسكورد",
        description="اروح لأي روم صوتي ← اضغط 'Start Activity' واختر من القائمة:",
        color=0x9B59B6
    )
    embed.add_field(name="🖥️ Watch Together", value="مشاهدة فيديوهات يوتيوب سوا", inline=False)
    embed.add_field(name="🎲 Betrayal.io", value="لعبة خيانة جماعية", inline=False)
    embed.add_field(name="♟️ Chess", value="شطرنج", inline=False)
    embed.add_field(name="🃏 Poker Night", value="بوكر", inline=False)
    embed.add_field(name="🖌️ Gartic Phone", value="لعبة الرسم والتخمين", inline=False)
    embed.add_field(name="🎤 Jamspace", value="جلسة موسيقية", inline=False)
    embed.set_footer(text="هذه الأنشطة رسمية من ديسكورد ومجانية")
    await ctx.send(embed=embed)

# ==================== نظام السحوبات ====================
@tasks.loop(seconds=30)
async def check_giveaways():
    data = load_data()
    changed = False
    for guild_id in list(data.get("giveaways", {}).keys()):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        for gid in list(data["giveaways"][guild_id].keys()):
            gw = data["giveaways"][guild_id][gid]
            if gw.get("ended") or time.time() < gw.get("end_time", 0):
                continue
            gw["ended"] = True
            changed = True
            channel = guild.get_channel(gw["channel_id"])
            if not channel:
                continue
            try:
                msg = await channel.fetch_message(int(gid))
                users = []
                for reaction in msg.reactions:
                    async for user in reaction.users():
                        if not user.bot:
                            users.append(user)
                if not users:
                    await channel.send(f"🎉 **سحب: {gw['prize']}**\nلا يوجد مشاركين 😅")
                    continue
                winners_count = gw.get("winners", 1)
                winners = random.sample(users, min(winners_count, len(users)))
                mentions = " ".join(w.mention for w in winners)
                embed = discord.Embed(
                    title="🎉 انتهى السحب!",
                    description=f"**الجائزة:** {gw['prize']}\n**الفائز:** {mentions}",
                    color=0x2ECC71
                )
                await channel.send(embed=embed)
            except:
                pass
    if changed:
        save_data(data)

@check_giveaways.before_loop
async def before_check():
    await bot.wait_until_ready()

VOICE_CACHE = {}

@tasks.loop(minutes=5)
async def voice_rewards():
    """مكافآت الرومات الصوتية (كل 5 دقائق)"""
    for guild in bot.guilds:
        gid = str(guild.id)
        for channel in guild.voice_channels:
            for member in channel.members:
                if member.bot:
                    continue
                uid = str(member.id)
                now = time.time()
                last = VOICE_CACHE.get(uid, 0)
                if now - last < 300:
                    continue
                VOICE_CACHE[uid] = now
                data = load_data()
                if "coins" not in data:
                    data["coins"] = {}
                if gid not in data["coins"]:
                    data["coins"][gid] = {}
                if uid not in data["coins"][gid]:
                    data["coins"][gid][uid] = 0
                data["coins"][gid][uid] += random.randint(5, 15)
                save_data(data)

@voice_rewards.before_loop
async def before_voice():
    await bot.wait_until_ready()

@tasks.loop(hours=2)
async def bump_reminder():
    """تذكير البمب كل ساعتين"""
    for guild in bot.guilds:
        gid = str(guild.id)
        data = load_data()
        ch_id = data.get("bump_channel", {}).get(gid)
        if ch_id:
            ch = guild.get_channel(ch_id)
            if ch:
                try:
                    await ch.send(f"⏰ **حان وقت البمب!**\nارسل `/bump` لدعم السيرفر 🚀")
                except:
                    pass

@bump_reminder.before_loop
async def before_bump():
    await bot.wait_until_ready()

@bot.command(name="setbump")
@commands.has_permissions(administrator=True)
async def set_bump(ctx, channel: discord.TextChannel = None):
    """تعيين قناة تذكير البمب: !setbump #قناة"""
    if channel is None:
        channel = ctx.channel
    data = load_data()
    gid = str(ctx.guild.id)
    if "bump_channel" not in data:
        data["bump_channel"] = {}
    data["bump_channel"][gid] = channel.id
    save_data(data)
    await ctx.send(f"✅ سيتم تذكير البمب كل ساعتين في {channel.mention}")

# ==================== عضو الأسبوع ====================
@bot.command(name="nominate")
async def nominate(ctx, member: discord.Member):
    """ترشيح عضو لعضو الأسبوع: !nominate @عضو"""
    if member.bot:
        return await ctx.send("❌ لا يمكن ترشيح بوت")
    if member == ctx.author:
        return await ctx.send("❌ لا يمكن ترشيح نفسك")
    data = load_data()
    gid = str(ctx.guild.id)
    if "motw" not in data:
        data["motw"] = {}
    if gid not in data["motw"]:
        data["motw"][gid] = {"votes": {}, "nominated": []}
    motw = data["motw"][gid]
    uid = str(ctx.author.id)
    if uid in motw.get("voted", {}):
        return await ctx.send("❌ لقد صوت مسبقاً هذا الأسبوع")
    target = str(member.id)
    motw["voted"] = motw.get("voted", {})
    motw["voted"][uid] = target
    motw["votes"][target] = motw["votes"].get(target, 0) + 1
    if target not in motw.get("nominated", []):
        motw["nominated"].append(target)
    save_data(data)
    embed = discord.Embed(title="⭐ ترشيح", description=f"{ctx.author.mention} رشح {member.mention} لعضو الأسبوع! 🎉", color=0xF1C40F)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="weekvotes")
async def week_votes(ctx):
    """عرض تصويتات عضو الأسبوع"""
    data = load_data()
    gid = str(ctx.guild.id)
    motw = data.get("motw", {}).get(gid, {})
    votes = motw.get("votes", {})
    if not votes:
        return await ctx.send("📋 لا يوجد تصويتات هذا الأسبوع\nاستخدم `!nominate @عضو` للترشيح")
    sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    embed = discord.Embed(title="⭐ تصويتات عضو الأسبوع", color=0xF1C40F)
    for i, (uid, count) in enumerate(sorted_votes[:5], 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else "مغادر"
        embed.add_field(name=f"#{i} {name}", value=f"🎫 {count} صوت", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="weekwinner")
@commands.has_permissions(administrator=True)
async def week_winner(ctx, member: discord.Member = None):
    """إعلان فائز عضو الأسبوع: !weekwinner @عضو"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "motw" not in data:
        data["motw"] = {}
    if member:
        embed = discord.Embed(title="🏆 عضو الأسبوع!", description=f"مبروك {member.mention} أنت عضو الأسبوع 🌟", color=0xF1C40F)
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        data["motw"][gid] = {"votes": {}, "nominated": [], "voted": {}}
        save_data(data)
    else:
        votes = data.get("motw", {}).get(gid, {}).get("votes", {})
        if not votes:
            return await ctx.send("📋 لا يوجد ترشيحات")
        winner_id = max(votes, key=votes.get)
        winner = ctx.guild.get_member(int(winner_id))
        if winner:
            await ctx.invoke(week_winner, member=winner)

@bot.command(name="gstart")
@commands.has_permissions(administrator=True)
async def giveaway_start(ctx, duration: str, winners: int = 1, *, prize: str = "جائزة"):
    """بدء سحب: !gstart 1h 2 جائزة نينتندو (1h = ساعة, 1d = يوم, 30m = 30 دقيقة)"""
    unit = duration[-1]
    num = int(duration[:-1])
    if unit == "m":
        seconds = num * 60
    elif unit == "h":
        seconds = num * 3600
    elif unit == "d":
        seconds = num * 86400
    else:
        return await ctx.send("❌ استخدم: m (دقائق), h (ساعات), d (أيام) مثال: !gstart 1h 2 جائزة")
    end_time = time.time() + seconds

    embed = discord.Embed(
        title="🎉 سحب!",
        description=(
            f"**الجائزة:** {prize}\n"
            f"**عدد الفائزين:** {winners}\n"
            f"**المدة:** {duration}\n"
            f"**ينتهي:** <t:{int(end_time)}:R>\n\n"
            f"تفاعل بـ 🎉 للمشاركة!"
        ),
        color=0x9B59B6
    )
    embed.set_footer(text="بوت إدارة السيرفر")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    data = load_data()
    gid = str(ctx.guild.id)
    if "giveaways" not in data:
        data["giveaways"] = {}
    if gid not in data["giveaways"]:
        data["giveaways"][gid] = {}
    data["giveaways"][gid][str(msg.id)] = {
        "prize": prize,
        "winners": winners,
        "end_time": end_time,
        "channel_id": ctx.channel.id,
        "ended": False
    }
    save_data(data)
    await ctx.send(f"✅ تم بدء السحب! 🎉 ينتهي <t:{int(end_time)}:R>")

@bot.command(name="gend")
@commands.has_permissions(administrator=True)
async def giveaway_end(ctx, message_id: str):
    """إنهاء سحب يدوياً: !gend message_id"""
    data = load_data()
    gid = str(ctx.guild.id)
    gw_data = data.get("giveaways", {}).get(gid, {})
    if message_id not in gw_data:
        return await ctx.send("❌ السحب غير موجود")
    gw_data[message_id]["end_time"] = time.time()
    gw_data[message_id]["ended"] = False
    save_data(data)
    await ctx.send("✅ تم إنهاء السحب، جاري إعلان الفائز...")

# ==================== نظام التذاكر ====================
TICKET_CATEGORY_NAME = "🎫 التذاكر"

@bot.command(name="new")
async def new_ticket(ctx, *, reason="لا يوجد"):
    """فتح تذكرة دعم: !new سبب المشكلة"""
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        mod_role = discord.utils.get(guild.roles, name="🟡 Mod")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        try:
            category = await guild.create_category(TICKET_CATEGORY_NAME, overwrites=overwrites)
        except:
            return await ctx.send("❌ صلاحياتي لا تسمح بإنشاء قسم التذاكر")

    existing = discord.utils.get(guild.text_channels, name=f"ticket-{ctx.author.name}".lower())
    if existing:
        return await ctx.send(f"❌ لديك تذكرة مفتوحة بالفعل: {existing.mention}")

    mod_role = discord.utils.get(guild.roles, name="🟡 Mod")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

    ch_name = f"ticket-{ctx.author.name}".lower().replace(" ", "-")
    ticket_ch = await guild.create_text_channel(
        ch_name, category=category, overwrites=overwrites,
        topic=f"تذكرة {ctx.author.name} - {reason}"
    )
    embed = discord.Embed(
        title="🎫 تذكرة دعم",
        description=f"مرحباً {ctx.author.mention}\nسيتم الرد عليك بأسرع وقت\nالسبب: {reason}",
        color=0x3498DB
    )
    embed.add_field(name="!close", value="لإغلاق التذكرة", inline=False)
    await ticket_ch.send(embed=embed)
    await ctx.send(f"✅ تم فتح التذكرة: {ticket_ch.mention}")

@bot.command(name="close")
@commands.has_permissions(manage_channels=True)
async def close_ticket(ctx):
    """إغلاق التذكرة الحالية"""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send("❌ هذه ليست قناة تذكرة")
    await ctx.send("🔒 جاري إغلاق التذكرة خلال 5 ثوان...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

@bot.command(name="adduser")
@commands.has_permissions(manage_channels=True)
async def add_ticket_user(ctx, member: discord.Member):
    """إضافة عضو للتذكرة: !adduser @العضو"""
    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send("❌ هذه ليست قناة تذكرة")
    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
    await ctx.send(f"✅ تم إضافة {member.mention} للتذكرة")

# ==================== نظام الشركاء ====================
@bot.command(name="partnersetup")
@commands.has_permissions(administrator=True)
async def partner_setup(ctx):
    """إعداد نظام الشركاء: إنشاء رتبة وقناة الشركاء"""
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name="🤝 شريك")
    if not role:
        role = await guild.create_role(name="🤝 شريك", color=0x00FF88, hoist=True)
    category = discord.utils.get(guild.categories, name="🤝 الشركاء")
    if not category:
        category = await guild.create_category("🤝 الشركاء")
    channel = discord.utils.get(category.text_channels, name="الشركاء")
    if not channel:
        channel = await guild.create_text_channel("الشركاء", category=category, topic="قائمة شركاء السيرفر")
    data = load_data()
    gid = str(guild.id)
    if gid not in data["config"]:
        data["config"][gid] = {}
    data["config"][gid]["partner_role"] = role.id
    data["config"][gid]["partner_channel"] = channel.id
    save_data(data)
    await ctx.send(f"✅ تم إعداد نظام الشركاء\nالرتبة: {role.mention}\nالقناة: {channel.mention}")

@bot.command(name="addpartner")
@commands.has_permissions(administrator=True)
async def add_partner(ctx, member: discord.Member):
    """إضافة شريك: !addpartner @العضو"""
    data = load_data()
    gid = str(ctx.guild.id)
    role_id = data["config"].get(gid, {}).get("partner_role")
    if not role_id:
        return await ctx.send("❌ استخدم !partnersetup أولاً")
    role = ctx.guild.get_role(role_id)
    if not role:
        return await ctx.send("❌ رتبة الشريك غير موجودة")
    await member.add_roles(role)
    channel_id = data["config"].get(gid, {}).get("partner_channel")
    if channel_id:
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            await channel.send(f"🎉 نرحب بشريكنا الجديد {member.mention}!")
    await ctx.send(f"✅ {member.mention} أصبح شريكاً!")

@bot.command(name="removepartner")
@commands.has_permissions(administrator=True)
async def remove_partner(ctx, member: discord.Member):
    """إزالة شريك: !removepartner @العضو"""
    data = load_data()
    gid = str(ctx.guild.id)
    role_id = data["config"].get(gid, {}).get("partner_role")
    if not role_id:
        return await ctx.send("❌ لم يتم إعداد نظام الشركاء بعد")
    role = ctx.guild.get_role(role_id)
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ تم إزالة {member.mention} من الشركاء")
    else:
        await ctx.send(f"❌ {member.mention} ليس شريكاً")

@bot.command(name="partners")
async def list_partners(ctx):
    """عرض قائمة الشركاء"""
    data = load_data()
    gid = str(ctx.guild.id)
    role_id = data["config"].get(gid, {}).get("partner_role")
    if not role_id:
        return await ctx.send("❌ لم يتم إعداد نظام الشركاء بعد")
    role = ctx.guild.get_role(role_id)
    if not role or not role.members:
        return await ctx.send("❌ لا يوجد شركاء حالياً")
    embed = discord.Embed(title="🤝 قائمة الشركاء", color=0x00FF88)
    for member in role.members:
        embed.add_field(name=member.display_name, value=member.mention, inline=False)
    await ctx.send(embed=embed)

# ==================== نظام الفعاليات ====================
@bot.command(name="addevent")
@commands.has_permissions(administrator=True)
async def add_event(ctx, name, date, *, description):
    """إضافة فعالية: !addevent اسم_الفعالية التاريخ التفاصيل"""
    data = load_data()
    gid = str(ctx.guild.id)
    if gid not in data["config"]:
        data["config"][gid] = {}
    if "events" not in data["config"][gid]:
        data["config"][gid]["events"] = []
    event = {
        "name": name,
        "date": date,
        "description": description,
        "author": ctx.author.id,
        "created": datetime.now().isoformat()
    }
    data["config"][gid]["events"].append(event)
    save_data(data)

    embed = discord.Embed(
        title=f"📅 {name}",
        description=description,
        color=0xE67E22
    )
    embed.add_field(name="التاريخ", value=date, inline=False)
    embed.set_footer(text=f"أضافها: {ctx.author.display_name}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")

@bot.command(name="events")
async def list_events(ctx):
    """عرض الفعاليات القادمة"""
    data = load_data()
    gid = str(ctx.guild.id)
    events = data["config"].get(gid, {}).get("events", [])
    if not events:
        return await ctx.send("❌ لا يوجد فعاليات حالياً")
    embed = discord.Embed(title="📅 الفعاليات القادمة", color=0xE67E22)
    for i, ev in enumerate(events, 1):
        embed.add_field(
            name=f"{i}. {ev['name']}",
            value=f"📆 {ev['date']}\n{ev['description']}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="removeevent")
@commands.has_permissions(administrator=True)
async def remove_event(ctx, number: int):
    """حذف فعالية: !removeevent رقم_الفعالية"""
    data = load_data()
    gid = str(ctx.guild.id)
    events = data["config"].get(gid, {}).get("events", [])
    if not events or number < 1 or number > len(events):
        return await ctx.send("❌ رقم الفعالية غير صحيح")
    removed = events.pop(number - 1)
    save_data(data)
    await ctx.send(f"✅ تم حذف: {removed['name']}")

# ==================== قناة الأوامر ====================
@bot.command(name="cmdchannel")
@commands.has_permissions(administrator=True)
async def cmd_channel(ctx):
    """إنشاء قناة مخصصة للأوامر: !cmdchannel"""
    guild = ctx.guild
    existing = discord.utils.get(guild.text_channels, name="🤖-الأوامر")
    if existing:
        return await ctx.send(f"✅ قناة الأوامر موجودة بالفعل: {existing.mention}")
    channel = await guild.create_text_channel(
        "🤖-الأوامر",
        topic="هذه القناة مخصصة لأوامر البوت - !help",
        slowmode_delay=1
    )
    await channel.send(
        "🤖 **قناة الأوامر**\n"
        "استخدم الأوامر هنا عشان ما تزعج القنوات الثانية\n"
        "اكتب `!help` لعرض جميع الأوامر\nاستخدم `!guide` لدليل المميزات الكامل 📋"
    )
    await ctx.send(f"✅ تم إنشاء قناة الأوامر: {channel.mention}")

# ==================== محتوى القنوات ====================
CONTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channel_content.json")

def load_content():
    try:
        with open(CONTENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

@bot.command(name="content")
@commands.has_permissions(administrator=True)
async def channel_content(ctx):
    """نشر المحتوى الاحترافي للقناة الحالية (للمشرفين)"""
    content_data = load_content()
    if not content_data:
        return await ctx.send("❌ ملف المحتوى غير موجود")

    ch_name = ctx.channel.name
    ch_name_clean = ch_name.replace("-", " ").replace("_", " ").strip()

    data = None
    if ch_name in content_data:
        data = content_data[ch_name]
    elif ch_name_clean in content_data:
        data = content_data[ch_name_clean]
    else:
        for key in content_data:
            kw = key.replace("-", " ").replace("_", " ")
            if kw in ch_name_clean or ch_name_clean in kw:
                data = content_data[key]
                break
        for key in content_data:
            if key in ch_name or ch_name in key:
                data = content_data[key]
                break

    if not data:
        available = "\n".join(f"• {k}" for k in content_data.keys())
        return await ctx.send(
            f"❌ لا يوجد محتوى لهذه القناة (`{ch_name}`)\n"
            f"القنوات المتاحة:\n{available}\n\n"
            f"💡 استخدم `!postall` لنشر المحتوى في جميع القنوات"
        )

    title = data.get("title", "")
    lines = data.get("content", [])

    embed = discord.Embed(title=title, color=0x2ECC71)
    text = "\n".join(lines)

    if len(text) <= 4000:
        embed.description = text
        await ctx.send(embed=embed)
    else:
        parts = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > 1900:
                parts.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            parts.append(current)
        await ctx.send(embed=embed)
        for part in parts:
            await ctx.send(part)

@bot.command(name="postall")
@commands.has_permissions(administrator=True)
async def post_all_content(ctx):
    """نشر المحتوى في جميع قنوات السيرفر"""
    content_data = load_content()
    if not content_data:
        return await ctx.send("❌ ملف المحتوى غير موجود")
    msg = await ctx.send("⏳ جاري نشر المحتوى في جميع القنوات...")
    count = 0
    for cat in ctx.guild.categories:
        for channel in cat.text_channels:
            ch_name = channel.name
            data = None
            if ch_name in content_data:
                data = content_data[ch_name]
            else:
                for key in content_data:
                    if key in ch_name or ch_name in key:
                        data = content_data[key]
                        break
            if not data:
                continue
            try:
                await channel.purge(limit=10)
                embed = discord.Embed(title=data["title"], color=0x2ECC71)
                text = "\n".join(data["content"])
                if len(text) <= 4000:
                    embed.description = text
                    await channel.send(embed=embed)
                else:
                    await channel.send(embed=embed)
                    for i in range(0, len(data["content"]), 20):
                        chunk = data["content"][i:i+20]
                        await channel.send("\n".join(chunk))
                count += 1
                await asyncio.sleep(1)
            except:
                pass
    await msg.edit(content=f"✅ تم نشر المحتوى في {count} قناة")

# ==================== عرض القنوات ====================
@bot.command(name="channels")
async def list_channels(ctx):
    """عرض جميع القنوات في السيرفر"""
    embed = discord.Embed(title="📋 قنوات السيرفر", color=0x3498DB)
    for cat in ctx.guild.categories:
        ch_list = "\n".join(f"  {ch.mention}" for ch in cat.channels if isinstance(ch, discord.TextChannel))
        voice_list = "\n".join(f"  🔈 {ch.name}" for ch in cat.channels if isinstance(ch, discord.VoiceChannel))
        text = ""
        if ch_list:
            text += ch_list + "\n"
        if voice_list:
            text += voice_list
        if text:
            embed.add_field(name=f"📁 {cat.name}", value=text, inline=False)
    text_chs = [ch.mention for ch in ctx.guild.text_channels if ch.category is None]
    if text_chs:
        embed.add_field(name="📁 بدون قسم", value="\n".join(text_chs), inline=False)
    await ctx.send(embed=embed)

# ==================== إصلاح القنوات الناقصة ====================
@bot.command(name="fixchannels")
@commands.has_permissions(administrator=True)
async def fix_channels(ctx):
    """إنشاء القنوات والأقسام الناقصة فقط"""
    guild = ctx.guild
    msg = await ctx.send("🔍 جاري فحص القنوات الناقصة...")
    created = []

    for cat_name, cat_cfg in CATEGORIES_CONFIG.items():
        cat = discord.utils.get(guild.categories, name=cat_name)
        if not cat:
            cat_overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=cat_cfg.get("everyone_view", True)
                )
            }
            mod_role = discord.utils.get(guild.roles, name="🟡 Mod")
            if mod_role:
                cat_overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )
            try:
                cat = await guild.create_category(cat_name, overwrites=cat_overwrites)
                created.append(f"📁 {cat_name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                await ctx.send(f"❌ خطأ في إنشاء قسم {cat_name}: {e}")
                continue

        for ch_cfg in cat_cfg["channels"]:
            ch_name = ch_cfg["name"]
            ch_type = ch_cfg.get("type", "text")
            exists = discord.utils.get(cat.channels, name=ch_name)
            if exists:
                continue

            try:
                if ch_type == "voice":
                    await guild.create_voice_channel(ch_name, category=cat)
                else:
                    clean_name = ch_name.replace(" ", "-")
                    topic = ch_cfg.get("topic", "")
                    read_only = ch_cfg.get("read_only", False)
                    mod_only = ch_cfg.get("mod_only", False)
                    overwrites = {}
                    if mod_only:
                        overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                        mod_role = discord.utils.get(guild.roles, name="🟡 Mod")
                        if mod_role:
                            overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    elif read_only:
                        overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
                    if overwrites:
                        await guild.create_text_channel(
                            clean_name, category=cat, topic=topic, overwrites=overwrites
                        )
                    else:
                        await guild.create_text_channel(
                            clean_name, category=cat, topic=topic
                        )
                created.append(f"  # {ch_name}")
                await asyncio.sleep(0.5)
            except Exception as e:
                await ctx.send(f"❌ خطأ في إنشاء {ch_name}: {e}")

    if created:
        result = "\n".join(created)
        await msg.edit(content=f"✅ تم إنشاء:\n{result}")
    else:
        await msg.edit(content="✅ جميع القنوات موجودة بالفعل!")

# ==================== الرومات الصوتية المؤقتة ====================
@bot.command(name="setupvc")
@commands.has_permissions(administrator=True)
async def setup_vc(ctx):
    """إنشاء روم صوتي لإنشاء رومات مؤقتة: !setupvc"""
    guild = ctx.guild
    cat = discord.utils.get(guild.categories, name="🔊 الرومات الصوتية")
    if not cat:
        cat = await guild.create_category("🔊 الرومات الصوتية")
    existing = discord.utils.get(guild.voice_channels, name="➕ أنشئ رومك")
    if existing:
        return await ctx.send("✅ الروم موجود بالفعل!")
    vc = await guild.create_voice_channel(
        name="➕ أنشئ رومك",
        category=cat,
        user_limit=0
    )
    data = load_data()
    gid = str(ctx.guild.id)
    if "vc_creator" not in data:
        data["vc_creator"] = {}
    data["vc_creator"][gid] = vc.id
    save_data(data)
    await ctx.send(f"✅ تم إنشاء {vc.mention}\nأي عضو يدخله ينشأ له روم خاص مؤقت!")

@bot.command(name="removevc")
@commands.has_permissions(administrator=True)
async def remove_vc(ctx):
    """حذف الروم المؤقت: !removevc"""
    guild = ctx.guild
    data = load_data()
    gid = str(ctx.guild.id)
    creator_id = data.get("vc_creator", {}).pop(gid, None)
    if creator_id:
        ch = guild.get_channel(creator_id)
        if ch:
            await ch.delete()
        save_data(data)
        await ctx.send("✅ تم حذف الروم المؤقت")
    else:
        await ctx.send("❌ ما في روم مؤقت")

@bot.command(name="quranvc")
@commands.has_permissions(administrator=True)
async def quran_vc(ctx):
    """إنشاء روم قرآن للبث الصوتي فقط: !quranvc"""
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(speak=False, connect=True, view_channel=True, stream=True),
        ctx.guild.me: discord.PermissionOverwrite(speak=True, connect=True, view_channel=True, manage_channels=True)
    }
    cat = discord.utils.get(ctx.guild.categories, name="🔊 رومات صوتية")
    if not cat:
        cat = await ctx.guild.create_category("🔊 رومات صوتية")
    existing = discord.utils.get(ctx.guild.voice_channels, name="📖 القرآن الكريم")
    if existing:
        await existing.edit(overwrites=overwrites)
        return await ctx.send(f"✅ تم تحديث صلاحيات الروم: {existing.mention}\nالآن الأعضاء يستمعون فقط 🎧")
    ch = await ctx.guild.create_voice_channel("📖 القرآن الكريم", category=cat, overwrites=overwrites)
    await ctx.send(f"✅ تم إنشاء {ch.mention}\nالأعضاء: 🎧 استماع فقط\nالمشرفين: 🎤 تكلم")

@bot.command(name="fixquran")
@commands.has_permissions(administrator=True)
async def fix_quran(ctx):
    """إصلاح صلاحية البوت في روم القرآن: !fixquran"""
    ch = discord.utils.get(ctx.guild.voice_channels, name="📖 القرآن الكريم")
    if not ch:
        return await ctx.send("❌ لا يوجد روم باسم 📖 القرآن الكريم")
    sunnah_bot = ctx.guild.get_member(1224063131949600829)
    if not sunnah_bot:
        return await ctx.send("❌ SunnahBot غير موجود في السيرفر\nادعوه أولاً")
    await ch.set_permissions(sunnah_bot, speak=True, connect=True, view_channel=True)
    await ctx.send(f"✅ تم إعطاء SunnahBot صلاحية التحدث في {ch.mention}\nجرب `/quranradio24_7 channel: 📖 القرآن الكريم`")

# ==================== نظام الاقتراحات ====================
@bot.command(name="suggestsetup")
@commands.has_permissions(administrator=True)
async def suggest_setup(ctx):
    """إعداد قناة الاقتراحات: !suggestsetup"""
    guild = ctx.guild
    cat = discord.utils.get(guild.categories, name="📋 الاقتراحات")
    if not cat:
        cat = await guild.create_category("📋 الاقتراحات")
    ch = discord.utils.get(guild.text_channels, name="اقتراحات")
    if not ch:
        ch = await guild.create_text_channel("اقتراحات", category=cat, topic="شاركنا باقتراحاتك!")
    data = load_data()
    gid = str(guild.id)
    if "suggestions" not in data:
        data["suggestions"] = {}
    data["suggestions"][gid] = ch.id
    save_data(data)
    await ctx.send(f"✅ تم إعداد الاقتراحات في {ch.mention}\nالأعضاء يستخدمون `!suggest نص الاقتراح`")

@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    """إرسال اقتراح: !suggest نص الاقتراح"""
    data = load_data()
    gid = str(ctx.guild.id)
    ch_id = data.get("suggestions", {}).get(gid)
    if not ch_id:
        return await ctx.send("❌ لم يتم إعداد الاقتراحات بعد\nالمشرف يستخدم `!suggestsetup`")
    channel = ctx.guild.get_channel(ch_id)
    if not channel:
        return await ctx.send("❌ قناة الاقتراحات غير موجودة")
    embed = discord.Embed(title="💡 اقتراح جديد", description=suggestion, color=0x3498DB, timestamp=datetime.now())
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"الحالة: قيد المراجعة")
    msg = await channel.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"✅ تم إرسال اقتراحك إلى {channel.mention}", delete_after=5)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command(name="approve")
@commands.has_permissions(administrator=True)
async def approve_suggestion(ctx, message_id: int):
    """الموافقة على اقتراح: !approve message_id"""
    try:
        msg = await ctx.channel.fetch_message(message_id)
        embed = msg.embeds[0] if msg.embeds else None
        if embed:
            embed.color = 0x2ECC71
            embed.set_footer(text="✅ تمت الموافقة")
            await msg.edit(embed=embed)
            await ctx.send(f"✅ تمت الموافقة على الاقتراح", delete_after=5)
    except:
        await ctx.send("❌ لم أجد الرسالة", delete_after=5)

@bot.command(name="reject")
@commands.has_permissions(administrator=True)
async def reject_suggestion(ctx, message_id: int):
    """رفض اقتراح: !reject message_id"""
    try:
        msg = await ctx.channel.fetch_message(message_id)
        embed = msg.embeds[0] if msg.embeds else None
        if embed:
            embed.color = 0xE74C3C
            embed.set_footer(text="❌ تم الرفض")
            await msg.edit(embed=embed)
            await ctx.send(f"✅ تم رفض الاقتراح", delete_after=5)
    except:
        await ctx.send("❌ لم أجد الرسالة", delete_after=5)

# ==================== نظام الردود التلقائية ====================
@bot.command(name="addreply")
@commands.has_permissions(administrator=True)
async def add_reply(ctx, trigger, *, response):
    """إضافة رد تلقائي: !addreply كلمة الرد"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "replies" not in data:
        data["replies"] = {}
    if gid not in data["replies"]:
        data["replies"][gid] = {}
    trigger_lower = trigger.lower()
    data["replies"][gid][trigger_lower] = response
    save_data(data)
    await ctx.send(f"✅ تم إضافة رد تلقائي:\n**إذا أحد كتب:** {trigger}\n**يرد:** {response}")

@bot.command(name="removereply")
@commands.has_permissions(administrator=True)
async def remove_reply(ctx, trigger):
    """حذف رد تلقائي: !removereply كلمة"""
    data = load_data()
    gid = str(ctx.guild.id)
    trigger_lower = trigger.lower()
    if data.get("replies", {}).get(gid, {}).pop(trigger_lower, None):
        save_data(data)
        await ctx.send(f"✅ تم حذف الرد لـ: {trigger}")
    else:
        await ctx.send(f"❌ لا يوجد رد للكلمة: {trigger}")

@bot.command(name="replies")
async def list_replies(ctx):
    """عرض جميع الردود التلقائية"""
    data = load_data()
    gid = str(ctx.guild.id)
    replies = data.get("replies", {}).get(gid, {})
    if not replies:
        return await ctx.send("❌ لا يوجد ردود تلقائية")

    chunks = list(replies.keys())
    msg = "**🤖 الردود التلقائية المتاحة:**\n"
    for i, word in enumerate(chunks, 1):
        msg += f"`{word}` "
        if i % 10 == 0:
            msg += "\n"

    if len(msg) <= 2000:
        await ctx.send(msg)
    else:
        lines = msg.split("\n")
        current = ""
        for line in lines:
            if len(current) + len(line) > 1900:
                await ctx.send(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            await ctx.send(current)

# ==================== تحميل مكتبة ردود جاهزة ====================
REPLY_LIBRARY = {
    # ===== تحيات =====
    "مرحبا": "أهلاً وسهلاً {user} ❤️",
    "مرحباً": "مرحباً مليون {user} 🎉",
    "هلا": "هلا والله {user} 🌟",
    "هلا والله": "هلا بك {user} نورتنا ❤️",
    "هلا وغلا": "هلا وغلا {user} ياهلاً 🌹",
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته {user} 🌙",
    "عليكم السلام": "وعليكم السلام {user} 🤍",
    "صباح الخير": "صباح النور والسرور {user} ☀️",
    "صباح النور": "صباح الفل {user} 🌸",
    "مساء الخير": "مساء النور والجمال {user} 🌆",
    "مساء النور": "مساء الورد {user} 🌹",
    "مساء الفل": "مساء السعادة {user} ✨",
    "نورت": "نورت والله {user} ياهلاً 🌟",
    "نورتي": "نورتي السيرفر {user} 🌸",
    "منور": "المنور صديقنا {user} 🔥",
    "ترحيب": "أهلاً بك في سيرفرنا {user} 🎉 تشرفنا",
    "ياهلا": "ياهلا ومرحبا {user} ❤️",
    "يا هلا": "يا هلا بك {user} نورتنا",

    # ===== ردود على التحية =====
    "كيفك": "الحمدلله {user} كيف أنت؟ ❤️",
    "كيف حالك": "تمام الحمدلله {user} وأنت؟ 😊",
    "شلونك": "الحمدلله {user} شلونك أنت؟ ❤️",
    "كيف الأمور": "تمام {user} الحمدلله على كل حال ✨",
    "اخبارك": "الحمدلله {user} وانت اخبارك؟",
    "بخير": "الحمدلله دايم {user} ✨",
    "الحمدلله": "دايماً يا رب {user} ❤️",
    "ماشي الحال": "ماشيها {user} 🚶",
    "تم": "تمام {user} ✅",
    "تمام": "تمام التمام {user} ✅",
    "تمامم": "تمام يا عسل {user} 🍯",

    # ===== شكر وامتنان =====
    "شكرا": "العفو {user} ❤️",
    "شكراً": "الشكر لله {user} 🤍",
    "شكرًا": "الله يسلمك {user} 🙏",
    "تسلم": "يسلم قلبك {user} 🤍",
    "تسلملي": "تسلملي أنت {user} ❤️",
    "تسلمين": "تسلم هالطلة {user} 🌸",
    "يعطيك العافية": "الله يعافيك {user} ❤️",
    "عافية": "يعافيك ربي {user} 🤍",
    "مشكور": "العفو {user} هذا واجبنا ❤️",
    "مشكورة": "العفو حبيبتي {user} ❤️",
    "ثانكس": "You're welcome {user} ❤️",
    "thank": "You're welcome {user} 🤍",
    "thanks": "Anytime {user} 💪",

    # ===== وداع =====
    "باي": "مع السلامة {user} 👋",
    "مع السلامة": "يسلمك ربي {user} 🌙",
    "تصبح على خير": "وأنت من أهله {user} 🌙",
    "تصبحون على خير": "وأنتم من أهله {user} 🌙",
    "تصبح": "وأنت بخير {user} 🤍",
    "ليلة سعيدة": "ليلة هنية {user} 🌙",
    "good night": "Good night {user} 🌙 sweet dreams",
    "gn": "gn {user} 🌙",
    "بشوفكم": "الله معكم {user} 👋",

    # ===== عبارات اجتماعية =====
    "الحمدلله": "دايماً يارب {user} ❤️",
    "ما شاء الله": "تبارك الله {user} ما شاء الله 🔥",
    "إن شاء الله": "إن شاء الله 🙏",
    "ان شاء الله": "ان شاء الله يارب {user} 🤲",
    "بالتوفيق": "الله يوفقك {user} 🌟",
    "عقبالك": "اللهم آمين {user} 🎉",
    "مبروك": "الله يبارك لك {user} 🎉",
    "الف مبروك": "مبروك والله يبارك لك {user} 🎊",
    "ماشاء": "ما شاء الله تبارك الله {user} 🔥",
    "الله يرحمها": "رحمها الله واسكنها فسيح جناته 🤲",
    "رحمة": "الله يرحمه ويسكنه الجنة 🤲",
    "عظم الله اجرك": "عظم الله أجرك {user} 🤲",
    "البقرة": "البقرة {user} 🐄",
    "صدق": "صدقت {user} 👍",
    "صحيح": "صحيح {user} 100% 💯",
    "حقيقة": "حقيقة {user} فعلاً 👍",
    "على طلاق": "ههههه {user} مسوينها 😂",
    "انا ضحكت": "هههههه {user} 😂🔥",
    "هههه": "هههههه {user} ضحكتني 😂",
    "ههههه": "ههههههه {user} 😂😂",
    "😂": "😂😂 {user}",
    "😭": "😭 شد حيلك {user}",
    "🔥": "🔥 {user} نار",
    "❤️": "❤️ حبينا {user}",

    # ===== ألعاب =====
    "لعبة": "عندنا العاب كثيرة {user}! 🎮",
    "بلاي": "جاهز نلعب {user}؟ 🎮",
    "فورت": "فورتنايت 🔫 {user} تجي؟",
    "فالورنت": "Valorant 🎯 {user} عزمها",
    "ماینکرافت": "Minecraft ⛏️ {user} جاهز؟",
    "مك craft": "Minecraft ⛏️",
    "pubg": "PUBG 🔫 {user}",
    "ببجي": "ببجي 🔫 {user} تجي نجيب عشوائي؟",
    "الات": "الات 🎮 في ذا ايم",
    "what the": "what the sigma {user} 🗿",
    "sigma": "sigma grindset {user} 🗿",
    "skibidi": "skibidi dop dop {user} 🚽",

    # ===== أسئلة شائعة =====
    "اقتراح": "شكراً لاقتراحك {user} سننظر فيه 👀",
    "اقتراحك": "اقتراحك وصل الإدارة {user} ✅",
    "ممكن": "أكيد {user} شو طلبك؟ 😊",
    "ممكن اسأل": "تفضل {user} اسأل وأنا حاضر 😊",
    "عندك سؤال": "تفضل {user} اسأل 😊",
    "سؤال": "تفضل {user} 👂",
    "استفسار": "تفضل {user} نحن هنا لخدمتك ❤️",
    "وين": "ودك تدلني على شيء {user}؟ 🔍",
    "كيف": "شرح؟ {user} 😊",
    "ليه": "سبب منطقي؟ {user} 🤔",
    "ايش": "أي خدمة {user}؟ 😊",
    "معلومة": "أكيد {user} تفضل 🌟",
    "مساعدة": "أكيد {user} كيف أقدر أساعدك؟ 🤖",
    "help": "I'm here to help {user}! How can I assist? 🤖",
    "محمد": "ﷺ صلى الله عليه وسلم ❤️",
    "صلى الله عليه وسلم": "اللهم صل وسلم على نبينا محمد ﷺ ❤️",
    "الله": "سبحان الله ❤️",

    # ===== تفاعل =====
    "بوت": "أنا بوت السيرفر {user} 🤖 تحت أمرك!",
    "البوت": "أنا موجود يا {user} 🤖",
    "يا بوت": "أمرك {user} 🤖",
    "بوتي": "نعم {user} 🤖 ❤️",
    "بوتنا": "فدوة {user} ❤️🤖",
    "واش": "واش {user} مالك؟ 😄",
    "وشو": "أهلاً {user} وشو في؟ 😄",
    "وش": "وش في {user}؟ 😄",
    "ايوه": "أيوه {user} 😊",
    "ايوا": "ايوا {user} 😊",
    "اي": "أي {user} 😊",
    "لا": "لا {user} 😅",
    "ايه": "أيه {user}؟ 😊",
    "اوكي": "أوكي {user} ✅",
    "ok": "OK {user} ✅",
    "yes": "Yes {user} ✅",
    "no": "No {user} ❌",
    "cool": "Cool {user} 🔥",
    "nice": "Nice {user} 💪",
    "lol": "lol {user} 😂",
    "lmao": "LMAO {user} 😂🔥",
    "موجود": "أنا موجود يا {user} ✅",
    "غبت": "غبت عنك {user} 😅 رجعت",
    "وحشتنا": "وحشتنا والله {user} ❤️",
    "وحشتني": "حشتني أنت {user} 🥺❤️",
    "مشتاق": "مشتاقين لك {user} ❤️",
    "اشتقت": "اشتقتنا لك {user} 🥰",
    "حبيب": "حبيبنا {user} ❤️",
    "حبيبي": "حبيبي والله {user} ❤️",
    "حبيبتي": "حبيبتنا {user} ❤️",
    "قلبي": "قلبنا {user} ❤️",
    "عمري": "عمرنا {user} ❤️",
    "روحي": "روحي {user} ❤️",
    "غلطان": "غلطان {user} 😅",
    "صح": "صح لسانك {user} 👏",
    "صح لسانك": "الله يسلم لسانك {user} 👏",
    "فكرة": "فكرة جميلة {user}! 🧠",
    "عجبني": "عجبني ذوقك {user} 👌",
    "ذوق": "ذوق عالي {user} 👌",
    "عسل": "سكر زيادة {user} 🍯",
    "قهوة": "قهوة الصباح {user} ☕",
    "شاي": "شاي وناي {user} 🍵",
    "جوعان": "يلا نطلب {user} 🍕",
    "نعسان": "نم {user} الله يحلمك بخير 🌙",
    "مزاج": "مزاج {user} ؟ 🎵",
    "زعلان": "لاتزعل {user} ❤️",
    "تعبان": "الله يقومك بالسلامة {user} ❤️",
    "مرض": "الله يشافيك {user} ❤️",
    "شفاك": "اللهم اشفه {user} 🤲",
    "موت": "لا تذكر الموت {user} 😅",
    "حلم": "حلم جميل {user} 🌙",
    "خير": "اللهم اجعله خير {user} 🤲",

    # ===== أغاني وفن =====
    "اغنية": "أغنية ولا فيلم {user}؟ 🎵",
    "أغنية": "عندنا Jockie Music `m!play` 🎵",
    "موسيقى": "موسيقى 🎵 جرب `m!play` في الروم الصوتي",
    "راب": "راب {user} 🎤",
    "انغام": "انغام {user} 🎵",

    # ===== ستريمنق =====
    "بث": "البث قريباً {user} 📡 تابع الإعلانات",
    "بث مباشر": "جاري التحضير {user} 📺",
    "يوتيوب": "يوتيوب {user} اشترك بالقناة ❤️",
    "تيك": "تيك توك {user} 📱",
    "انستا": "انستغرام {user} 📸",
    "تويتر": "تويتر {user} 🐦",
    "سناب": "سناب شات {user} 👻",
    "discord": "Discord {user} نحن هنا ❤️",
    "دسكورد": "دسكورد أحلى منزل {user} ❤️",
    "سيرفر": "سيرفرنا بيتك {user} ❤️",
    "كوميونتي": "كوميونتي رهيب {user} 🔥",
    "محتوى": "محتوى متنوع قريباً {user} 🎬",
    "انتظر": "ننتظرك {user} 💪",
    "نتطلع": "ننتظر ونشوف {user} 👀",

    # ===== إيموجيات =====
    "ضحك": "😂😂 {user}",
    "بكي": "😭😭 {user} مو ذاك الزود",
    "غضب": "😤 {user} هد الأعصاب",
    "حب": "😍 {user} حب",
    "عشق": "🥰 {user} عشق",
    "نار": "🔥 {user} ناررر",
    "فل": "🌸 {user} فل",
    "ورد": "🌹 {user} ورد",
    "نجمة": "⭐ {user} نجمة السيرفر",
    "ميدالية": "🏅 {user} ميدالية ذهبية",
    "كأس": "🏆 {user} بطولة",
    "لعبة": "🎮 {user} نلعب؟",
    "هدية": "🎁 {user} هدية منا",
    "بالون": "🎈 {user} عيد ميلاد؟",
    "كيك": "🎂 {user} كل عام وأنت بخير",
    "عيد": "🎉 كل عام وأنت بخير {user}",
    "سنة": "🎊 سنة جديدة سعيدة {user}",
    "رمضان": "🌙 رمضان كريم {user}",
    "عيد فطر": "🎉 عيد مبارك {user}",
    "اضحى": "🕋 أضحى مبارك {user}",

    # ===== عامية =====
    "شنو": "شنو {user}؟ 😄",
    "شكو": "شكو ماكو {user}؟ 😂",
    "شلون": "تمام {user} وأنت؟ ❤️",
    "دش": "دش {user} نورتنا 🌟",
    "دخلت": "نورت السيرفر {user} ❤️",
    "طلع": "الله معاك {user} 👋",
    "طالع": "الله يوفقك {user} 🌟",
    "طق": "طق {user} 😂",
    "عزم": "عزمها {user} 🔥",
    "عزمه": "عزمها ي {user} 🎯",
    "زود": "زود {user} 🔥",
    "كفو": "كفو {user} 👏",
    "كفؤ": "كفؤ والله {user} 💪",
    "نشمية": "نشمية {user} 🔥",
    "شهم": "شهم {user} 💪",
    "طيب": "طيب {user} ❤️",
    "طيبة": "طيبة قلبك {user} ❤️",
    "قسم": "قسم {user} 😂",
    "والله": "والله {user} صدقني 😅",
    "بجد": "بجد {user}؟ 😲",
    "جد": "جد {user}؟ 😲",
    "فعلا": "فعلاً {user} 👍",
    "بالضبط": "بالضبط {user} 🎯",
    "ظبط": "ظبطنها {user} ✅",
    "يخي": "يخي {user} 😂",
    "ياخي": "ياخي {user} 😅",
    "يابو": "يابو {user} هههه",
    "يقلع": "يقلع {user} 😂",
    "يسطا": "يسطا {user} 💪",
    "عم": "عم {user} 😅",
    "خيو": "خيو {user} هلا",
    "رفيق": "رفيق الدرب {user} ❤️",
    "صاحبي": "صاحبي {user} هلا",
    "أخوي": "هلا أخوي {user} ❤️",
    "اختي": "هلا أختي {user} ❤️",
    "يالبى": "يالبى قلبك {user} ❤️",

    # ===== تريندات =====
    "رياكشن": "رياكشن {user} 😂",
    "ميم": "ميمز {user} 😂 شاركنا",
    "meme": "meme time {user} 😂",
    "جديد": "جديد {user}؟ وش صار؟",
    "خراب": "خراب {user} 😂",
    "طقطقة": "طقطقة {user} 😂",
    "سدح": "سدح {user} 😂",
    "سدحها": "سدحها {user} 😂🔥",
    "بوز": "بوز {user} 😂",
    "فلاش": "فلاش {user} 📸",
    "فضائح": "فضائح {user} 😂",
    "عيب": "عيب {user} 😅",
    "حرام": "حرام {user} 😂",
    "مسوي": "مسوي {user} فاهم 😂",
    "فاهم": "فاهمك {user} 😎",
    "عقل": "عقل {user} 😂",
    "مفكر": "مفكر حالك {user} 😂",
    "منجد": "منجد {user}؟ 😲",
    "اكيد": "أكيد {user} ✅",
    "طبعا": "طبعاً {user} ✅",
    "متفقين": "متفقين {user} ✅",
    "اتفق": "متفقين {user} 👌",
    "معاك": "معاك {user} 100% 💯",
    "ضد": "ضد {user} ليش؟ 😅",

    # ===== ترحيب خاص =====
    "عضو جديد": "أهلاً بك عضواً جديداً {user} 🎊",
    "جديد": "نورتنا {user} 🌟",
    "انضم": "نورت السيرفر {user} ❤️",
    "تشرفت": "تشرفنا والله {user} 🤍",
    "شرفت": "شرفتنا {user} ❤️",
    "فخر": "فخر بوجودك {user} 🏆",

    # ===== أوامر =====
    "دعم": "دعم {user} تفضل! استخدم !new للتذكرة 🎫",
    "ابلاغ": "للإبلاغ استخدم !new {user} 🎫",
    "تبليغ": "تبليغ {user} تفضل 🎫",
    "مشكلة": "للإبلاغ عن مشكلة استخدم !new {user} 🎫",
    "شكوى": "شكوى {user} استخدم !new 🎫",
    "قوانين": "القوانين في #القوانين {user} 📜",
    "رولز": "اختار رتب ألعابك من #get-roles {user} 🎮",
    "رتبة": "شوف الرتب في !channels {user} 🏷️",
    "روم": "الرومات الصوتية تحت 🎮 {user} 🔈",
    "بوتات": "عندنا عدة بوتات: Carl-bot, Jockie Music, Disboard {user} 🤖",
    "امر": "الأوامر في `!help` {user} 📋",

    # ===== تشجيع =====
    "ممتاز": "ممتاز {user} 👏🔥",
    "أحسنت": "أحسنت {user} 💪",
    "برافو": "برافو {user} 👏🌟",
    "واو": "واو {user} 🔥",
    "جميل": "جميل {user} 👌",
    "رهيب": "رهيب {user} 🔥",
    "رائع": "رائع {user} 🌟",
    "مبدع": "مبدع {user} 💪",
    "عبقري": "عبقري {user} 🧠",
    "أسطورة": "أسطورة {user} 🏆",
    "خرافي": "خرافي {user} 🔥",
    "فنان": "فنان {user} 🎨",
    "نادر": "نادر {user} 💎",
    "ممتازة": "ممتازة {user} 👏",
    "بطلة": "بطلة {user} 🏆",
    "مبدعة": "مبدعة {user} 💪",
    "نشيطة": "نشيطة {user} 🔥",
    "نشيط": "نشيط {user} 🔥",
    "شاطر": "شاطر {user} 👏",
    "شاطرة": "شاطرة {user} 👏",
    "يبارك": "الله يبارك فيك {user} ❤️",
    "يسعد": "الله يسعدك {user} ❤️",
    "يحفظ": "الله يحفظك {user} ❤️",
    "يرحم": "الله يرحم والديك {user} 🤲",

    # ===== ردود انجليزية =====
    "hello": "Hello {user}! Welcome ❤️",
    "hi": "Hi {user}! How are you? 😊",
    "hey": "Hey {user}! 👋",
    "sup": "Sup {user}! 😎",
    "whats up": "What's up {user}! 🔥",
    "how are you": "I'm good {user}! Thanks for asking 🤖",
    "good": "Good {user}! 👍",
    "great": "Great {user}! 🔥",
    "awesome": "Awesome {user}! 🌟",
    "amazing": "Amazing {user}! 💪",
    "welcome": "Welcome {user}! We're happy to have you ❤️",
    "bye": "Bye {user}! Take care 👋",
    "goodbye": "Goodbye {user}! See you later 👋",
    "cya": "Cya {user}! 👋",
    "brb": "BRB {user}! We'll wait ⏰",
    "gtg": "GTG {user}! Bye 👋",
    "ty": "You're welcome {user}! ❤️",
}

@bot.command(name="loadreplies")
@commands.has_permissions(administrator=True)
async def load_replies(ctx):
    """تحميل مكتبة ردود جاهزة (20 رد)"""
    data = load_data()
    gid = str(ctx.guild.id)
    if "replies" not in data:
        data["replies"] = {}
    if gid not in data["replies"]:
        data["replies"][gid] = {}
    count = 0
    for trigger, response in REPLY_LIBRARY.items():
        if trigger not in data["replies"][gid]:
            data["replies"][gid][trigger] = response
            count += 1
    save_data(data)
    await ctx.send(f"✅ تم تحميل {count} رد تلقائي جديد!\nاستخدم `!replies` لعرضهم")

# ==================== إحصائيات السيرفر ====================
@bot.command(name="stats", aliases=["احصائيات"])
async def server_stats(ctx):
    """إحصائيات السيرفر: !stats"""
    guild = ctx.guild
    bots = sum(1 for m in guild.members if m.bot)
    humans = guild.member_count - bots
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    channels = len(guild.text_channels) + len(guild.voice_channels)
    roles = len([r for r in guild.roles if not r.is_default()])
    boosters = guild.premium_subscription_count
    embed = discord.Embed(title=f"📊 إحصائيات {guild.name}", color=0x2ECC71)
    embed.add_field(name="👥 الأعضاء", value=f"المجموع: {guild.member_count}\nبشر: {humans}\nبوتات: {bots}\nأونلاين: {online}", inline=True)
    embed.add_field(name="📁 القنوات", value=f"المجموع: {channels}\n📝 نصية: {len(guild.text_channels)}\n🔊 صوتية: {len(guild.voice_channels)}", inline=True)
    embed.add_field(name="⭐ أخرى", value=f"🆔 ID: {guild.id}\n👑 المالك: {guild.owner.mention}\n🎖️ رتب: {roles}\n💎 Boost: {boosters}", inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text=f"تم الإنشاء: {guild.created_at.strftime('%Y-%m-%d')}")
    await ctx.send(embed=embed)

@bot.command(name="dashboard", aliases=["داشبورد"])
async def dashboard(ctx):
    """لوحة تحكم السيرفر: !dashboard"""
    guild = ctx.guild
    data = load_data()
    gid = str(guild.id)
    coins_data = data.get("coins", {}).get(gid, {})
    total_coins = sum(coins_data.values())
    users_with_coins = len(coins_data)
    levels_data = data.get("levels", {}).get(gid, {})
    total_xp = sum(u.get("xp", 0) for u in levels_data.values())
    shop_items = len(data.get("shop", {}).get(gid, {}))
    color_items = len(data.get("color_roles", {}).get(gid, {}))
    items = data.get("shop", {}).get(gid, {})
    colors_data = data.get("color_roles", {}).get(gid, {})
    products = shop_items + color_items
    embed = discord.Embed(title=f"📊 لوحة تحكم {guild.name}", color=0x2ECC71)
    embed.add_field(name="👥 السيرفر", value=f"الأعضاء: {guild.member_count}\nالرتب: {len([r for r in guild.roles if not r.is_default()])}\nالبوسترات: {guild.premium_subscription_count}", inline=True)
    embed.add_field(name="💰 الإقتصاد", value=f"إجمالي العملات: {total_coins}\nأعضاء بعملات: {users_with_coins}\nمنتجات بالمتجر: {products}", inline=True)
    embed.add_field(name="📈 النشاط", value=f"مستويات مسجلة: {len(levels_data)}\nإجمالي XP: {total_xp}\nالأعضاء النشطين: {sum(1 for u in levels_data.values() if u.get('xp', 0) > 0)}", inline=True)
    top_user = max(coins_data, key=coins_data.get) if coins_data else None
    if top_user:
        member = guild.get_member(int(top_user))
        embed.add_field(name="🏆 أغنى عضو", value=f"{member.mention if member else 'مغادر'}: {coins_data[top_user]} 💰", inline=False)
    mod_on = data.get("automod", {}).get(gid, {}).get("enabled", False)
    antispam = data.get("automod", {}).get(gid, {}).get("antispam", False)
    badwords_count = len(data.get("automod", {}).get(gid, {}).get("badwords", []))
    embed.add_field(name="🛡️ الحماية", value=f"الحماية: {'🟢 مفعلة' if mod_on else '🔴 معطلة'}\nمنع سبام: {'🟢' if antispam else '🔴'}\nكلمات ممنوعة: {badwords_count}", inline=True)
    embed.set_footer(text=f"آخر تحديث • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    await ctx.send(embed=embed)

# ==================== نظام المتجر ====================
@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    """مكافأة يومية: !daily (مرة كل 24 ساعة)"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if uid not in data["coins"][gid]:
        data["coins"][gid][uid] = 0
    reward = random.randint(50, 150)
    data["coins"][gid][uid] += reward
    save_data(data)
    await ctx.send(f"🎁 {ctx.author.mention} حصلت على **{reward}** 💰 عملة يومية!")

@bot.command(name="balance")
async def balance(ctx, member: discord.Member = None):
    """رصيدك: !balance @عضو"""
    if member is None:
        member = ctx.author
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(member.id)
    coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    await ctx.send(f"💰 رصيد {member.mention}: **{coins}** عملة")

@bot.command(name="shop")
async def shop(ctx):
    """عرض المتجر"""
    data = load_data()
    gid = str(ctx.guild.id)
    items = data.get("shop", {}).get(gid, {})
    if not items:
        return await ctx.send("🛒 المتجر فارغ حالياً\nاستخدم !additem لإضافة منتجات")
    embed = discord.Embed(title="🛒 المتجر", color=0xF1C40F, description="استخدم !buy id للشراء")
    for item_id, item in items.items():
        embed.add_field(
            name=f"`{item_id}` - {item['name']}",
            value=f"💰 {item['price']} عملة\n{item.get('description', '')}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="buy")
async def buy(ctx, item_id: str):
    """شراء من المتجر: !buy id_المنتج"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    items = data.get("shop", {}).get(gid, {})
    if item_id not in items:
        return await ctx.send("❌ المنتج غير موجود\nاستخدم !shop لعرض المنتجات")
    item = items[item_id]
    user_coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    if user_coins < item["price"]:
        return await ctx.send(f"❌ معك {user_coins} 💰 والمنتج بـ {item['price']}")
    role = ctx.guild.get_role(item["role_id"])
    if role:
        if role in ctx.author.roles:
            return await ctx.send("❌ عندك هالرتبة بالفعل")
        await ctx.author.add_roles(role)
    data["coins"][gid][uid] -= item["price"]
    save_data(data)
    await ctx.send(f"✅ {ctx.author.mention} اشتريت **{item['name']}** بنجاح! 🎉")

@bot.command(name="listroles")
async def list_roles(ctx):
    """عرض جميع أدوار السيرفر"""
    roles = [r for r in ctx.guild.roles if not r.is_default() and not r.managed]
    if not roles:
        return await ctx.send("ما في أدوار مخصصة")
    embed = discord.Embed(title=f"📋 أدوار السيرفر ({len(roles)})", color=0x2ECC71)
    for r in roles:
        embed.add_field(name=r.name, value=f"ID: {r.id}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="additem")
@commands.has_permissions(administrator=True)
async def add_item(ctx, item_id: str, price: int, *, role_name: str):
    """إضافة منتج: !additem id_مختصر السعر اسم_الدور"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        roles_list = "\n".join(f"• {r.name}" for r in ctx.guild.roles if not r.is_default() and not r.managed)
        return await ctx.send(f"❌ الدور '{role_name}' غير موجود\nالأدوار المتاحة:\n{roles_list}")
    data = load_data()
    gid = str(ctx.guild.id)
    if "shop" not in data:
        data["shop"] = {}
    if gid not in data["shop"]:
        data["shop"][gid] = {}
    data["shop"][gid][item_id] = {
        "name": role.name,
        "price": price,
        "role_id": role.id,
        "description": ""
    }
    save_data(data)
    await ctx.send(f"✅ تم إضافة **{role.name}** للمتجر بـ {price} 💰\nالأيدي: `{item_id}`")

@bot.command(name="removeitem")
@commands.has_permissions(administrator=True)
async def remove_item(ctx, item_id: str):
    """حذف منتج: !removeitem id_المنتج"""
    data = load_data()
    gid = str(ctx.guild.id)
    if data.get("shop", {}).get(gid, {}).pop(item_id, None):
        save_data(data)
        await ctx.send(f"✅ تم حذف المنتج `{item_id}`")
    else:
        await ctx.send("❌ المنتج غير موجود")

@bot.command(name="addcoins")
async def add_coins(ctx, amount: int, member: discord.Member = None):
    """إضافة عملات: !addcoins 100 @عضو"""
    if not ctx.author.guild_permissions.administrator and ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("❌ هذا الأمر للمشرفين فقط")
    if member is None:
        member = ctx.author
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(member.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if uid not in data["coins"][gid]:
        data["coins"][gid][uid] = 0
    data["coins"][gid][uid] += amount
    save_data(data)
    await ctx.send(f"✅ تم إضافة {amount} 💰 لـ {member.mention}")

@bot.command(name="rich", aliases=["اغنياء"])
async def rich(ctx):
    """لوحة أغنى الأعضاء: !rich"""
    data = load_data()
    gid = str(ctx.guild.id)
    users = data.get("coins", {}).get(gid, {})
    sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)[:10]
    if not sorted_users:
        return await ctx.send("💰 لا يوجد أعضاء بعد")
    embed = discord.Embed(title="🏆 أغنى الأعضاء", color=0xF1C40F)
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, coins) in enumerate(sorted_users):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else "مغادر"
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        embed.add_field(name=f"{medal} {name}", value=f"💰 {coins}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="weekly")
@commands.cooldown(1, 604800, commands.BucketType.user)
async def weekly(ctx):
    """مكافأة أسبوعية: !weekly"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if uid not in data["coins"][gid]:
        data["coins"][gid][uid] = 0
    reward = random.randint(300, 700)
    data["coins"][gid][uid] += reward
    save_data(data)
    await ctx.send(f"🎁 {ctx.author.mention} حصلت على **{reward}** 💰 مكافأة أسبوعية!")

# ==================== ألعاب الرهان ====================
@bot.command(name="bet")
async def bet(ctx, amount: int):
    """مضاعفة عملات (50%): !bet 50"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    if amount < 10:
        return await ctx.send("❌ الحد الأدنى 10 عملات")
    if amount > coins:
        return await ctx.send(f"❌ معك {coins} 💰 فقط")
    win = random.choice([True, False])
    if win:
        data["coins"][gid][uid] += amount
        save_data(data)
        await ctx.send(f"🎲 {ctx.author.mention} ربحت **{amount}** 💰! (رصيدك: {data['coins'][gid][uid]})")
    else:
        data["coins"][gid][uid] -= amount
        save_data(data)
        await ctx.send(f"😢 {ctx.author.mention} خسرت {amount} 💰 (رصيدك: {data['coins'][gid][uid]})")

@bot.command(name="dice")
async def dice(ctx, amount: int):
    """زهر (4+ ربح): !dice 50"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    if amount < 10:
        return await ctx.send("❌ الحد الأدنى 10 عملات")
    if amount > coins:
        return await ctx.send(f"❌ معك {coins} 💰 فقط")
    roll = random.randint(1, 6)
    win = roll >= 4
    if win:
        data["coins"][gid][uid] += amount
        save_data(data)
        await ctx.send(f"🎲 {ctx.author.mention} رمية **{roll}** 🎉 ربحت **{amount}**! (رصيدك: {data['coins'][gid][uid]})")
    else:
        data["coins"][gid][uid] -= amount
        save_data(data)
        await ctx.send(f"🎲 {ctx.author.mention} رمية **{roll}** 😢 خسرت {amount} (رصيدك: {data['coins'][gid][uid]})")

@bot.command(name="slots")
async def slots(ctx, amount: int):
    """آلة سلوتس (جائزة كبرى ×10): !slots 50"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    if amount < 10:
        return await ctx.send("❌ الحد الأدنى 10 عملات")
    if amount > coins:
        return await ctx.send(f"❌ معك {coins} 💰 فقط")
    emojis = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    r1, r2, r3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    result = f"**{r1} | {r2} | {r3}**"
    if r1 == r2 == r3:
        if r1 == "7️⃣":
            win = amount * 10
        elif r1 == "💎":
            win = amount * 5
        else:
            win = amount * 3
        data["coins"][gid][uid] += win
        save_data(data)
        await ctx.send(f"🎰 {ctx.author.mention}\n{result}\n🎉 **جاكبوت!** ربحت **{win}** 💰!")
    elif r1 == r2 or r2 == r3 or r1 == r3:
        win = amount
        data["coins"][gid][uid] += win
        save_data(data)
        await ctx.send(f"🎰 {ctx.author.mention}\n{result}\n🎉 ربحت **{amount}** 💰!")
    else:
        data["coins"][gid][uid] -= amount
        save_data(data)
        await ctx.send(f"🎰 {ctx.author.mention}\n{result}\n😢 خسرت {amount} 💰")

# ==================== نظام النقش والألوان ====================
COLOR_ROLES_KEY = "color_roles"

@bot.command(name="nick")
async def change_nick(ctx, *, new_name: str = None):
    """تغيير نقشك (VIP أو مشرف): !nick الاسم"""
    vip = discord.utils.get(ctx.guild.roles, name="🟣 VIP")
    has_vip = vip and vip in ctx.author.roles
    is_admin = ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id
    if not has_vip and not is_admin:
        return await ctx.send("❌ هذا الأمر فقط لمشتري VIP والمشرفين")
    if new_name is None:
        await ctx.author.edit(nick=None)
        await ctx.send(f"✅ تم حذف نقشك")
    else:
        if len(new_name) > 32:
            return await ctx.send("❌ الاسم طويل جداً (الحد 32 حرف)")
        await ctx.author.edit(nick=new_name)
        await ctx.send(f"✅ تم تغيير نقشك إلى **{new_name}**")

@bot.command(name="setnick")
@commands.has_permissions(administrator=True)
async def set_nick(ctx, member_name: str, *, new_name: str = None):
    """تغيير نقش عضو (مشرف): !setnick اسم_العضو اللقب"""
    member = discord.utils.find(lambda m: member_name.lower() in m.name.lower() or member_name.lower() in m.display_name.lower() or f"<@{m.id}>" == member_name, ctx.guild.members)
    if not member:
        return await ctx.send(f"❌ العضو '{member_name}' غير موجود")
    if new_name is None:
        await member.edit(nick=None)
        await ctx.send(f"✅ تم حذف نقش {member.mention}")
    else:
        if len(new_name) > 32:
            return await ctx.send("❌ الاسم طويل جداً")
        await member.edit(nick=new_name)
        await ctx.send(f"✅ تم تغيير نقش {member.mention} إلى **{new_name}**")

@bot.command(name="colors")
async def show_colors(ctx):
    """عرض الألوان المتاحة"""
    data = load_data()
    gid = str(ctx.guild.id)
    colors = data.get(COLOR_ROLES_KEY, {}).get(gid, {})
    if not colors:
        return await ctx.send("🎨 لا يوجد ألوان.\nالمشرف يستخدم `!addcolor اسم #FF0000 السعر`")
    embed = discord.Embed(title="🎨 ألوان المتجر", color=0x9B59B6)
    for name, info in colors.items():
        role = ctx.guild.get_role(info["role_id"])
        if role:
            embed.add_field(name=role.name, value=f"`!buycolor {name}` - 💰 {info['price']}", inline=True)
    await ctx.send(embed=embed)

@bot.command(name="buycolor")
async def buy_color(ctx, name: str):
    """شراء لون: !buycolor اسم_اللون"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    colors = data.get(COLOR_ROLES_KEY, {}).get(gid, {})
    if name not in colors:
        return await ctx.send("❌ اللون غير موجود.\nاستخدم `!colors`")
    info = colors[name]
    user_coins = data.get("coins", {}).get(gid, {}).get(uid, 0)
    if user_coins < info["price"]:
        return await ctx.send(f"❌ معك {user_coins} 💰 واللون بـ {info['price']}")
    role = ctx.guild.get_role(info["role_id"])
    if not role:
        return await ctx.send("❌ رول اللون محذوف")
    existing = [r for r in ctx.author.roles if r.id in [c["role_id"] for c in colors.values()]]
    if existing:
        await ctx.author.remove_roles(*existing)
    await ctx.author.add_roles(role)
    data["coins"][gid][uid] -= info["price"]
    save_data(data)
    await ctx.send(f"✅ {ctx.author.mention} اشتريت لون **{role.name}** 🎨")

@bot.command(name="addcolor")
@commands.has_permissions(administrator=True)
async def add_color(ctx, name: str, hex_color: str, price: int):
    """إضافة لون للمتجر: !addcolor احمر #FF0000 200"""
    try:
        color = discord.Color(int(hex_color.strip("#"), 16))
    except:
        return await ctx.send("❌ كود لون خطأ (مثلاً #FF0000 للأحمر)")
    role = await ctx.guild.create_role(name=name, color=color, hoist=False, mentionable=False)
    data = load_data()
    gid = str(ctx.guild.id)
    if COLOR_ROLES_KEY not in data:
        data[COLOR_ROLES_KEY] = {}
    if gid not in data[COLOR_ROLES_KEY]:
        data[COLOR_ROLES_KEY][gid] = {}
    data[COLOR_ROLES_KEY][gid][name] = {"role_id": role.id, "price": price}
    save_data(data)
    await ctx.send(f"✅ تم إضافة لون **{name}** بـ {price} 💰\nالأعضاء يشترون بـ `!buycolor {name}`")

@bot.command(name="removecolor")
@commands.has_permissions(administrator=True)
async def remove_color(ctx, name: str):
    """حذف لون من المتجر: !removecolor اسم_اللون"""
    data = load_data()
    gid = str(ctx.guild.id)
    colors = data.get(COLOR_ROLES_KEY, {}).get(gid, {})
    if name not in colors:
        return await ctx.send("❌ اللون غير موجود")
    role = ctx.guild.get_role(colors[name]["role_id"])
    if role:
        await role.delete()
    del colors[name]
    save_data(data)
    await ctx.send(f"✅ تم حذف اللون `{name}`")

@bot.command(name="fixperms")
@commands.has_permissions(administrator=True)
async def fix_perms(ctx):
    """ترقية صلاحيات البوت تلقائياً: !fixperms"""
    bot_member = ctx.guild.get_member(bot.user.id)
    if not bot_member:
        return await ctx.send("❌ خطأ")
    bot_role = bot_member.top_role
    try:
        await bot_role.edit(administrator=True)
        await ctx.send("✅ تم منح البوت صلاحية **Administrator** 🚀\nجرب `!nick Narft 🔥 VIP`")
    except:
        await ctx.send("❌ ماقدرت أعدل صلاحيات البوت.\nاسحب رول **My Server Bot** لأعلى القائمة في Server Settings ← Roles، وفعّل Administrator يدوياً")

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    data = load_data()
    channel_id = data.get(LOG_CHANNEL_KEY, {}).get(str(message.guild.id))
    if not channel_id:
        return
    log_channel = message.guild.get_channel(channel_id)
    if not log_channel:
        return
    embed = discord.Embed(
        title="🗑️ حذف رسالة",
        description=f"**الكاتب:** {message.author.mention} (`{message.author}`)",
        color=0xE74C3C,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="القناة", value=message.channel.mention, inline=False)
    if message.content:
        embed.add_field(name="المحتوى", value=message.content[:1000], inline=False)
    embed.set_footer(text=f"ID: {message.author.id}")
    await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    data = load_data()
    channel_id = data.get(LOG_CHANNEL_KEY, {}).get(str(before.guild.id))
    if not channel_id:
        return
    log_channel = before.guild.get_channel(channel_id)
    if not log_channel:
        return
    embed = discord.Embed(
        title="✏️ تعديل رسالة",
        description=f"**الكاتب:** {before.author.mention} (`{before.author}`)",
        color=0xF39C12,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="القناة", value=before.channel.mention, inline=False)
    embed.add_field(name="قبل", value=before.content[:500] or "(فارغة)", inline=False)
    embed.add_field(name="بعد", value=after.content[:500] or "(فارغة)", inline=False)
    embed.set_footer(text=f"ID: {before.author.id}")
    await log_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    data = load_data()
    channel_id = data.get(LOG_CHANNEL_KEY, {}).get(str(member.guild.id))
    if not channel_id:
        return
    log_channel = member.guild.get_channel(channel_id)
    if not log_channel:
        return
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.target.id == member.id:
            embed = discord.Embed(
                title="👢 طرد عضو",
                description=f"**العضو:** {member.mention} (`{member}`)\n**بواسطة:** {entry.user.mention}",
                color=0xE67E22,
                timestamp=datetime.utcnow()
            )
            if entry.reason:
                embed.add_field(name="السبب", value=entry.reason, inline=False)
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)
            return
    embed = discord.Embed(
        title="🚪 غادر السيرفر",
        description=f"**العضو:** {member.mention} (`{member}`)",
        color=0x95A5A6,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"ID: {member.id}")
    await log_channel.send(embed=embed)

@bot.event
async def on_member_ban(guild, member):
    if member.bot:
        return
    data = load_data()
    channel_id = data.get(LOG_CHANNEL_KEY, {}).get(str(guild.id))
    if not channel_id:
        return
    log_channel = guild.get_channel(channel_id)
    if not log_channel:
        return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        if entry.target.id == member.id:
            embed = discord.Embed(
                title="⛔ حظر عضو",
                description=f"**العضو:** {member.mention} (`{member}`)\n**بواسطة:** {entry.user.mention}",
                color=0x000000,
                timestamp=datetime.utcnow()
            )
            if entry.reason:
                embed.add_field(name="السبب", value=entry.reason, inline=False)
            embed.set_footer(text=f"ID: {member.id}")
            await log_channel.send(embed=embed)
            return

@bot.command(name="logsetup")
@commands.has_permissions(administrator=True)
async def log_setup(ctx, channel: discord.TextChannel = None):
    """إعداد قناة التسجيل: !logsetup #قناة"""
    if not channel:
        return await ctx.send("❌ استخدم: `!logsetup #القناة`")
    data = load_data()
    if LOG_CHANNEL_KEY not in data:
        data[LOG_CHANNEL_KEY] = {}
    data[LOG_CHANNEL_KEY][str(ctx.guild.id)] = channel.id
    save_data(data)
    embed = discord.Embed(
        title="✅ تم إعداد التسجيل",
        description=f"سيتم تسجيل الأحداث في {channel.mention}",
        color=0x2ECC71
    )
    embed.add_field(name="سيتم تسجيل", value="🗑️ حذف رسائل\n✏️ تعديل رسائل\n👢 طرد\n⛔ حظر\n🚪 مغادرة", inline=False)
    await ctx.send(embed=embed)
    test = discord.Embed(title="📋 نظام التسجيل نشط", description="من هنا ستظهر جميع أحداث السيرفر", color=0x2ECC71)
    await channel.send(embed=test)

@bot.command(name="removelog")
@commands.has_permissions(administrator=True)
async def remove_log(ctx):
    """إلغاء قناة التسجيل: !removelog"""
    data = load_data()
    if LOG_CHANNEL_KEY in data and str(ctx.guild.id) in data[LOG_CHANNEL_KEY]:
        data[LOG_CHANNEL_KEY].pop(str(ctx.guild.id), None)
        save_data(data)
        await ctx.send("✅ تم إلغاء تسجيل الأحداث")
    else:
        await ctx.send("❌ لا يوجد قناة تسجيل مسجلة")

@bot.command(name="mute", aliases=["tempmute"])
@commands.has_permissions(moderate_members=True)
async def temp_mute(ctx, member: discord.Member, time: str = "10m", *, reason="بدون سبب"):
    """كتم عضو مؤقت: !mute @عضو 30m سبب"""
    try:
        unit = time[-1]
        val = int(time[:-1])
        if unit == "s":
            delta = timedelta(seconds=val)
        elif unit == "m":
            delta = timedelta(minutes=val)
        elif unit == "h":
            delta = timedelta(hours=val)
        elif unit == "d":
            delta = timedelta(days=val)
        else:
            return await ctx.send("❌ استخدم: `10s`/`10m`/`1h`/`1d`")
        if delta.total_seconds() > 864000:
            return await ctx.send("❌ الحد الأقصى 10 أيام")
        await member.timeout(delta, reason=reason)
        embed = discord.Embed(title="🔇 كتم مؤقت", color=0xE67E22)
        embed.add_field(name="العضو", value=member.mention, inline=True)
        embed.add_field(name="المدة", value=time, inline=True)
        embed.add_field(name="السبب", value=reason, inline=False)
        await ctx.send(embed=embed)
    except ValueError:
        await ctx.send("❌ استخدم: `10s`/`10m`/`1h`/`1d`")

@bot.command(name="unmute", aliases=["um"])
@commands.has_permissions(moderate_members=True)
async def un_mute(ctx, member: discord.Member):
    """فك الكتم: !unmute @عضو"""
    if not member.is_timed_out():
        return await ctx.send("❌ العضو غير مكتوم")
    await member.timeout(None)
    embed = discord.Embed(title="🔊 تم فك الكتم", description=member.mention, color=0x2ECC71)
    await ctx.send(embed=embed)

# ==================== نظام التقديم على الإشراف ====================
APPLY_QUESTIONS = [
    "📝 **ما اسمك الحقيقي؟**",
    "🎂 **كم عمرك؟**",
    "⏰ **كم ساعة تقدر تتفرغ يومياً؟**",
    "🎮 **ما هي خبرتك في الإشراف أو إدارة سيرفرات؟**",
    "⭐ **لماذا تريد أن تصبح مشرف؟**",
    "📌 **هل لديك أفكار لتطوير السيرفر؟**"
]

@bot.command(name="applysetup")
@commands.has_permissions(administrator=True)
async def apply_setup(ctx, channel: discord.TextChannel = None, *, role: discord.Role = None):
    """إعداد نظام التقديم: !applysetup #قناة @رتبة_المشرف"""
    if not channel:
        return await ctx.send("❌ استخدم: `!applysetup #القناة @رتبة_الإشراف`")
    data = load_data()
    gid = str(ctx.guild.id)
    if APPLY_CHANNEL_KEY not in data:
        data[APPLY_CHANNEL_KEY] = {}
    data[APPLY_CHANNEL_KEY][gid] = channel.id
    if role:
        if APPLY_ROLE_KEY not in data:
            data[APPLY_ROLE_KEY] = {}
        data[APPLY_ROLE_KEY][gid] = role.id
    save_data(data)
    await ctx.send(f"✅ تم إعداد التقديم على الإشراف!\nالقناة: {channel.mention}\nالرتبة: {role.mention if role else 'لم تحدد'}")

@bot.command(name="applyrole")
@commands.has_permissions(administrator=True)
async def apply_role(ctx, role: discord.Role):
    """تحديد رتبة المشرف للتقديم: !applyrole @رتبة"""
    data = load_data()
    if APPLY_ROLE_KEY not in data:
        data[APPLY_ROLE_KEY] = {}
    data[APPLY_ROLE_KEY][str(ctx.guild.id)] = role.id
    save_data(data)
    await ctx.send(f"✅ تم تعيين رتبة الإشراف إلى {role.mention}")

@bot.command(name="apply")
async def apply_cmd(ctx):
    """تقديم طلب إشراف: !apply"""
    data = load_data()
    gid = str(ctx.guild.id)
    channel_id = data.get(APPLY_CHANNEL_KEY, {}).get(gid)
    if not channel_id:
        return await ctx.send("❌ نظام التقديم غير مفعل")
    target = ctx.guild.get_channel(channel_id)
    if not target:
        return await ctx.send("❌ قناة التقديم غير موجودة")
    await ctx.send(f"📋 {ctx.author.mention} تم إرسال أسئلة التقديم في الخاص...")
    try:
        await ctx.author.send("🎯 **تقديم طلب إشراف - Elite Arena**\nأرسل إجاباتك واحدة تلو الأخرى:")
    except:
        return await ctx.send("❌ فتح الخاص أولاً (Accept Direct Messages)")

    answers = []
    for i, q in enumerate(APPLY_QUESTIONS, 1):
        await ctx.author.send(f"**س{i}:** {q}")
        try:
            msg = await bot.wait_for("message", timeout=300, check=lambda m: m.author == ctx.author and m.channel.type == discord.ChannelType.private)
            answers.append(msg.content)
        except asyncio.TimeoutError:
            await ctx.author.send("❌ انتهى الوقت، أعد المحاولة")
            return

    embed = discord.Embed(
        title="📋 طلب إشراف جديد",
        description=f"**مقدم الطلب:** {ctx.author.mention}\n**العضو:** {ctx.author}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    for i, (q, a) in enumerate(zip(APPLY_QUESTIONS, answers), 1):
        embed.add_field(name=f"❓ س{i}", value=f"**{q}**\n{a}", inline=False)
    embed.set_footer(text=f"ID: {ctx.author.id}")
    msg = await target.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.author.send("✅ **تم استلام طلبك!** الإدارة ستراجعه قريباً.")

@bot.command(name="accept")
@commands.has_permissions(administrator=True)
async def accept_apply(ctx, member: discord.Member = None, *, reason="مقبول"):
    """قبول طلب إشراف: !accept @عضو"""
    if not member:
        return await ctx.send("❌ استخدم: `!accept @العضو`")
    data = load_data()
    gid = str(ctx.guild.id)
    role_id = data.get(APPLY_ROLE_KEY, {}).get(gid)
    if not role_id:
        return await ctx.send("❌ لم تحدد رتبة الإشراف بعد\nاستخدم `!applyrole @الرتبة`")
    role = ctx.guild.get_role(role_id)
    if not role:
        return await ctx.send("❌ الرتبة غير موجودة")
    await member.add_roles(role)
    embed = discord.Embed(
        title="✅ تم قبول طلبك",
        description=f"**{member.name}**، مبروك! تم قبولك في فريق الإشراف 🎉",
        color=0x2ECC71
    )
    await ctx.send(embed=embed)
    try:
        await member.send(f"🎉 **مبروك!** تم قبول طلبك للإشراف في Elite Arena!\nرتبة {role.mention} تمت إضافتك.")
    except:
        pass

@bot.command(name="deny", aliases=["رفض"])
@commands.has_permissions(administrator=True)
async def reject_apply(ctx, member: discord.Member = None, *, reason="بدون سبب"):
    """رفض طلب إشراف: !deny @عضو سبب"""
    if not member:
        return await ctx.send("❌ استخدم: `!reject @العضو سبب`")
    embed = discord.Embed(
        title="❌ تم رفض طلبك",
        description=f"**{member.name}**، للأسف لم يتم قبول طلبك.\n**السبب:** {reason}",
        color=0xE74C3C
    )
    await ctx.send(embed=embed)
    try:
        await member.send(f"❌ عذراً **{member.name}**، لم يتم قبول طلبك للإشراف.\nالسبب: {reason}")
    except:
        pass

# ==================== نظام الوظائف والسرقة ====================
WORK_LIST = [
    "🚚 سوّقت شاحنة", "👨‍💻 برمجت موقع", "🎨 رسمت لوحة",
    "🔧 صلحت سيارة", "📦 وزعت طلبات", "🎤 غنيت في حفلة",
    "🍳 طبخت وجبة", "🏗️ بنيت جدار", "🌾 حصدت مزرعة",
    "📸 صورت حفل زفاف", "✈️ درت طيارة", "🛵 أوصلت طلب",
    "🧹 نظفت مكتب", "📝 درست طلاب", "🎮 اختبرت لعبة"
]

ROB_RESPONSES = [
    "🏃 ركض وراك وصادك", "🚔 صادك البوليس", "🐕 انهشمت من كلب",
    "🛡️ كان مسلح وضربك", "📸 انصورت بكاميرا وصار مقطع", "😅 قفلت باب السيارة بوجهك"
]

ROB_WINS = [
    "💰 كسبت", "🤑 خطفت", "💵 أخذت", "👛 سحبت", "🎯 حصلت على"
]

@bot.command(name="work")
@commands.cooldown(1, 1800, commands.BucketType.user)
async def work(ctx):
    """اشتغل واكسب عملات: !work (كل 30 دقيقة)"""
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if uid not in data["coins"][gid]:
        data["coins"][gid][uid] = 0
    earned = random.randint(20, 80)
    job = random.choice(WORK_LIST)
    data["coins"][gid][uid] += earned
    save_data(data)
    embed = discord.Embed(
        title="💼 عمل",
        description=f"{ctx.author.mention} **{job}** وربحت **{earned}** 💰",
        color=0x2ECC71
    )
    embed.set_footer(text=f"رصيدك: {data['coins'][gid][uid]} 💰")
    await ctx.send(embed=embed)

@bot.command(name="rob")
async def rob(ctx, member: discord.Member = None):
    """سرقة عضو: !rob @عضو"""
    if not member:
        return await ctx.send("❌ استخدم: `!rob @العضو`")
    if member == ctx.author:
        return await ctx.send("❌ تسرق نفسك؟ 😂")
    if member.bot:
        return await ctx.send("❌ البوتات ما عندهم فلوس")
    data = load_data()
    gid = str(ctx.guild.id)
    auid = str(ctx.author.id)
    muid = str(member.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if auid not in data["coins"][gid]:
        data["coins"][gid][auid] = 0
    if muid not in data["coins"][gid]:
        data["coins"][gid][muid] = 0
    if data["coins"][gid][muid] < 10:
        return await ctx.send(f"❌ {member.mention} ما عنده فلوس")
    if data["coins"][gid][auid] < 10:
        return await ctx.send(f"❌ معك اقل من 10 عملات، ما تقدر تسرق")
    if random.random() < 0.45:
        amount = random.randint(10, min(data["coins"][gid][muid], 100))
        data["coins"][gid][auid] += amount
        data["coins"][gid][muid] -= amount
        save_data(data)
        win_text = random.choice(ROB_WINS)
        embed = discord.Embed(
            title="🔫 سرقة ناجحة",
            description=f"{ctx.author.mention} {win_text} **{amount}** 💰 من {member.mention}",
            color=0x2ECC71
        )
        await ctx.send(embed=embed)
    else:
        fine = random.randint(10, 50)
        data["coins"][gid][auid] = max(0, data["coins"][gid][auid] - fine)
        save_data(data)
        fail = random.choice(ROB_RESPONSES)
        embed = discord.Embed(
            title="😅 فشلت السرقة",
            description=f"{ctx.author.mention} {fail} وخسرت **{fine}** 💰",
            color=0xE74C3C
        )
        await ctx.send(embed=embed)

# ==================== نظام الزواج ====================
MARRIAGE_KEY = "marriages"

@bot.command(name="marry")
async def marry(ctx, member: discord.Member = None):
    """زواج عضو: !marry @عضو"""
    if not member:
        return await ctx.send("❌ استخدم: `!marry @العضو`")
    if member == ctx.author:
        return await ctx.send("❌ تتزوج نفسك؟ 😂")
    if member.bot:
        return await ctx.send("❌ ما تتزوج بوت")
    data = load_data()
    gid = str(ctx.guild.id)
    if MARRIAGE_KEY not in data:
        data[MARRIAGE_KEY] = {}
    if gid not in data[MARRIAGE_KEY]:
        data[MARRIAGE_KEY][gid] = []
    for pair in data[MARRIAGE_KEY][gid]:
        if ctx.author.id in pair:
            return await ctx.send("❌ أنت متزوج/ة بالفعل")
        if member.id in pair:
            return await ctx.send(f"❌ {member.mention} متزوج/ة بالفعل")
    embed = discord.Embed(
        title="💍 طلب زواج",
        description=f"{ctx.author.mention} يطلب الزواج من {member.mention}\n\n{member.mention} رد بـ ✅ خلال 60 ثانية",
        color=0xFF69B4
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    def check(reaction, user):
        return user == member and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)
        if str(reaction.emoji) == "✅":
            data[MARRIAGE_KEY][gid].append([ctx.author.id, member.id])
            save_data(data)
            embed = discord.Embed(
                title="💞 مبروك الزواج!",
                description=f"🎉 **{ctx.author.name}** 💍 **{member.name}**\nألف مبروك! 🎊",
                color=0xFF69B4
            )
            embed.set_footer(text="💕 ربي يوفقكم")
            await msg.edit(embed=embed)
            await msg.clear_reactions()
        else:
            await ctx.send(f"😢 {ctx.author.mention} تم رفض طلب الزواج")
            await msg.clear_reactions()
    except asyncio.TimeoutError:
        await ctx.send(f"⌛ {ctx.author.mention} لم يرد {member.mention} في الوقت المحدد")
        await msg.clear_reactions()

@bot.command(name="divorce")
async def divorce(ctx, member: discord.Member = None):
    """طلاق: !divorce @عضو"""
    if not member:
        return await ctx.send("❌ استخدم: `!divorce @العضو`")
    data = load_data()
    gid = str(ctx.guild.id)
    if MARRIAGE_KEY not in data or gid not in data[MARRIAGE_KEY]:
        return await ctx.send("❌ ليس هناك زواج بينكما")
    for pair in data[MARRIAGE_KEY][gid]:
        if ctx.author.id in pair and member.id in pair:
            data[MARRIAGE_KEY][gid].remove(pair)
            save_data(data)
            embed = discord.Embed(
                title="💔 طلاق",
                description=f"**{ctx.author.name}** و **{member.name}** انفصلوا 💔",
                color=0x95A5A6
            )
            await ctx.send(embed=embed)
            return
    await ctx.send("❌ ليس هناك زواج بينكما")

@bot.command(name="married", aliases=["marriages"])
async def married_list(ctx):
    """عرض قائمة المتزوجين: !married"""
    data = load_data()
    gid = str(ctx.guild.id)
    if MARRIAGE_KEY not in data or gid not in data[MARRIAGE_KEY] or not data[MARRIAGE_KEY][gid]:
        return await ctx.send("❌ لا يوجد متزوجين في السيرفر")
    embed = discord.Embed(title="💞 المتزوجون", color=0xFF69B4)
    for i, pair in enumerate(data[MARRIAGE_KEY][gid], 1):
        p1 = ctx.guild.get_member(pair[0])
        p2 = ctx.guild.get_member(pair[1])
        if p1 and p2:
            embed.add_field(name=f"👫 زوج {i}", value=f"{p1.mention} 💍 {p2.mention}", inline=False)
        else:
            data[MARRIAGE_KEY][gid].remove(pair)
            save_data(data)
    await ctx.send(embed=embed)

# ==================== نظام الصيد ====================
FISH_LIST = [
    {"name": "🐟 سمكة صغيرة", "min": 5, "max": 15, "chance": 30},
    {"name": "🐠 سمكة متوسطة", "min": 15, "max": 35, "chance": 25},
    {"name": "🐡 سمكة منفوخة", "min": 20, "max": 45, "chance": 15},
    {"name": "🦐 روبيان", "min": 10, "max": 25, "chance": 20},
    {"name": "🦀 سلطعون", "min": 25, "max": 50, "chance": 10},
    {"name": "🐙 أخطبوط", "min": 30, "max": 60, "chance": 8},
    {"name": "🦈 قرش! 🦈", "min": 50, "max": 120, "chance": 5},
    {"name": "💎 كنز! 🏆", "min": 100, "max": 300, "chance": 2}
]

CHATTER = "ططططط ططط طططططط 🎣"

@bot.command(name="fish")
@commands.cooldown(1, 60, commands.BucketType.user)
async def fish(ctx):
    """صيد سمك: !fish (كل 60 ثانية)"""
    msg = await ctx.send(f"{ctx.author.mention} 🎣 ألقى الصنارة... {CHATTER}")
    await asyncio.sleep(3)
    data = load_data()
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    if "coins" not in data:
        data["coins"] = {}
    if gid not in data["coins"]:
        data["coins"][gid] = {}
    if uid not in data["coins"][gid]:
        data["coins"][gid][uid] = 0
    roll = random.randint(1, 100)
    total = 0
    for fish_type in FISH_LIST:
        total += fish_type["chance"]
        if roll <= total:
            amount = random.randint(fish_type["min"], fish_type["max"])
            data["coins"][gid][uid] += amount
            save_data(data)
            embed = discord.Embed(
                title="🎣 صيد!",
                description=f"{ctx.author.mention} اصطاد {fish_type['name']} بقيمة **{amount}** 💰",
                color=discord.Color.green() if amount > 50 else discord.Color.blue()
            )
            embed.set_footer(text=f"رصيدك: {data['coins'][gid][uid]} 💰")
            await msg.edit(embed=embed)
            return
    await msg.edit(content=f"😅 {ctx.author.mention} ما صاد شي، ارجع جرب 🎣")

# ==================== نظام التصويت ====================
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

@bot.command(name="poll")
async def poll(ctx, *, text: str = None):
    """تصويت: !poll سؤال | خيار1 | خيار2 | خيار3"""
    if not text:
        return await ctx.send("❌ استخدم: `!poll السؤال | خيار1 | خيار2 | خيار3`")
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        return await ctx.send("❌ استخدم: `!poll السؤال | خيار1 | خيار2`")
    question = parts[0]
    options = parts[1:]
    if len(options) < 2:
        return await ctx.send("❌ استخدم على الأقل خيارين")
    if len(options) > 10:
        return await ctx.send("❌ الحد الأقصى 10 خيارات")
    embed = discord.Embed(
        title=f"📊 {question}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    for i, opt in enumerate(options):
        embed.add_field(name=f"{NUMBER_EMOJIS[i]} {opt}", value="⠀", inline=False)
    embed.set_footer(text=f"بواسطة {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(NUMBER_EMOJIS[i])

# ==================== إحصائيات الرومات الصوتية ====================
STATS_CATEGORY_KEY = "stats_category"

@bot.command(name="statssetup")
@commands.has_permissions(administrator=True)
async def stats_setup(ctx):
    """إعداد رومات إحصائيات الصوت: !statssetup"""
    data = load_data()
    gid = str(ctx.guild.id)
    existing = data.get(STATS_CATEGORY_KEY, {}).get(gid)
    if existing:
        cat = ctx.guild.get_channel(existing)
        if cat:
            for ch in cat.voice_channels:
                try:
                    await ch.delete()
                except:
                    pass
            try:
                await cat.delete()
            except:
                pass
    overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(connect=False, speak=False, view_channel=True)}
    cat = await ctx.guild.create_category("📊 إحصائيات السيرفر", overwrites=overwrites)
    members = ctx.guild.member_count
    online = sum(1 for m in ctx.guild.members if m.status != discord.Status.offline)
    in_vc = sum(len(vc.members) for vc in ctx.guild.voice_channels)
    ch1 = await ctx.guild.create_voice_channel(f"👥 Members: {members}", category=cat)
    ch2 = await ctx.guild.create_voice_channel(f"🟢 Online: {online}", category=cat)
    ch3 = await ctx.guild.create_voice_channel(f"🔊 Voice: {in_vc}", category=cat)
    if STATS_CATEGORY_KEY not in data:
        data[STATS_CATEGORY_KEY] = {}
    data[STATS_CATEGORY_KEY][gid] = cat.id
    save_data(data)
    await ctx.send(f"✅ تم إنشاء رومات الإحصائيات في قسم **{cat.name}**")
    if not update_stats.is_running():
        update_stats.start()

@bot.command(name="removestats")
@commands.has_permissions(administrator=True)
async def remove_stats(ctx):
    """حذف رومات الإحصائيات: !removestats"""
    data = load_data()
    gid = str(ctx.guild.id)
    cat_id = data.get(STATS_CATEGORY_KEY, {}).get(gid)
    if not cat_id:
        return await ctx.send("❌ لا توجد رومات إحصائيات")
    cat = ctx.guild.get_channel(cat_id)
    if cat:
        for ch in cat.voice_channels:
            try:
                await ch.delete()
            except:
                pass
        try:
            await cat.delete()
        except:
            pass
    data[STATS_CATEGORY_KEY].pop(gid, None)
    save_data(data)
    await ctx.send("✅ تم حذف رومات الإحصائيات")

@tasks.loop(minutes=5)
async def update_stats():
    for guild in bot.guilds:
        gid = str(guild.id)
        data = load_data()
        cat_id = data.get(STATS_CATEGORY_KEY, {}).get(gid)
        if not cat_id:
            continue
        cat = guild.get_channel(cat_id)
        if not cat:
            continue
        channels = cat.voice_channels
        if len(channels) < 3:
            continue
        members = guild.member_count
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        in_vc = sum(len(vc.members) for vc in guild.voice_channels if vc.category_id != cat_id)
        try:
            await channels[0].edit(name=f"👥 Members: {members}")
            await channels[1].edit(name=f"🟢 Online: {online}")
            await channels[2].edit(name=f"🔊 Voice: {in_vc}")
        except:
            pass

# ==================== دليل الأوامر ====================
FEATURES_GUIDE = [
    ("🛡️ الإشراف", "`!kick` `!ban` `!clear` `!warn` `!warnings` `!mute` `!um` `!antispam`\n`!logsetup #قناة` – يسجل كل الأحداث"),
    ("💰 الإقتصاد", "`!daily` `!weekly` `!balance` `!rich` `!work` `!rob` `!fish` `!shop` `!buy`"),
    ("🎲 ألعاب", "`!bet` `!dice` `!slots` `!poll`"),
    ("💞 اجتماعيات", "`!marry` `!divorce` `!married` `!suggest`"),
    ("⭐ المستويات", "`!level` `!leaderboard` – تكسب عملات من الرسائل والصوت"),
    ("🎨 التخصيص", "`!nick` `!buycolor` `!colors` – اشترِ رتبة VIP وشخصن اسمك"),
    ("🎫 التقديم", "`!apply` – قدم على الإشراف"),
    ("📊 إحصائيات", "`!stats` `!dashboard` – رومات الإحصائيات تتحدث تلقائياً"),
    ("🖼️ ترحيب احترافي", "صورة ترحيب ووداع مخصصة لكل عضو عند دخوله وخروجه"),
]

@bot.command(name="guide", aliases=["الاوامر", "المميزات"])
async def guide(ctx):
    """دليل المميزات: !guide"""
    embed = discord.Embed(
        title="🎮 Elite Arena - دليل المميزات",
        description="جميع أنظمة السيرفر في مكان واحد",
        color=0x9B59B6
    )
    for name, value in FEATURES_GUIDE:
        embed.add_field(name=name, value=value, inline=False)
    embed.add_field(name="❓ مساعدة", value="جميع الأوامر: `!help`\nدليل المميزات: `!guide`", inline=False)
    embed.set_footer(text=f"{len(bot.commands)} أمر • Elite Arena")
    await ctx.send(embed=embed)

# ==================== نظام النشر التلقائي ====================
AUTO_POST_KEY = "auto_post"
AUTO_POST_INTERVAL_KEY = "auto_post_interval"

@bot.command(name="autopostsetup")
@commands.has_permissions(administrator=True)
async def auto_post_setup(ctx, channel: discord.TextChannel = None, interval_hours: int = 6, *, message: str = None):
    """إعداد نشر تلقائي: !autopostsetup #قناة 6 نص_المنشور"""
    if not channel:
        return await ctx.send("❌ استخدم: `!autopostsetup #القناة 6 نص المنشور`")
    if not message:
        return await ctx.send("❌ اكتب نص المنشور")
    data = load_data()
    gid = str(ctx.guild.id)
    if AUTO_POST_KEY not in data:
        data[AUTO_POST_KEY] = {}
    data[AUTO_POST_KEY][gid] = {
        "channel_id": channel.id,
        "interval": interval_hours * 3600,
        "message": message
    }
    save_data(data)
    await ctx.send(f"✅ تم إعداد النشر التلقائي في {channel.mention} كل {interval_hours} ساعة")

@bot.command(name="removeautopost")
@commands.has_permissions(administrator=True)
async def remove_auto_post(ctx):
    """إلغاء النشر التلقائي: !removeautopost"""
    data = load_data()
    gid = str(ctx.guild.id)
    if AUTO_POST_KEY in data and gid in data[AUTO_POST_KEY]:
        data[AUTO_POST_KEY].pop(gid)
        save_data(data)
        await ctx.send("✅ تم إلغاء النشر التلقائي")
    else:
        await ctx.send("❌ لا يوجد نشر تلقائي مفعل")

@tasks.loop(hours=1)
async def auto_post_check():
    data = load_data()
    for guild in bot.guilds:
        gid = str(guild.id)
        cfg = data.get(AUTO_POST_KEY, {}).get(gid)
        if not cfg:
            continue
        channel = guild.get_channel(cfg["channel_id"])
        if not channel:
            continue
        last = cfg.get("last_post", 0)
        if time.time() - last >= cfg["interval"]:
            try:
                await channel.send(cfg["message"])
                data[AUTO_POST_KEY][gid]["last_post"] = time.time()
                save_data(data)
            except:
                pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ هذا الأمر للمشرفين فقط")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ خطأ في الإدخال: {error}")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ انتظر {error.retry_after:.0f} ثانية")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ الأمر ناقص: `{error.param.name}`\nاستخدم `!help` لطريقة الاستخدام")
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandInvokeError):
        original = error.original
        if isinstance(original, discord.Forbidden):
            await ctx.send("❌ البوت ما عنده صلاحية\nادخل السيرفر ← الإعدادات ← الأدوار ← My Server Bot وفعّل **Administrator** أو **Manage Nicknames**")
        else:
            await ctx.send(f"❌ خطأ: `{original}`")
            print(original)
    else:
        await ctx.send(f"❌ خطأ: `{error}`")
        print(error)

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    if BOT_TOKEN == "ضع_التوكن_هنا":
        print("=" * 50)
        print("❌ خطأ: لم تقم بوضع توكن البوت!")
        print("📝 افتح ملف bot.py واستبدل 'ضع_التوكن_هنا' بتوكن البوت")
        print("=" * 50)
    else:
        print("🚀 جاري تشغيل البوت...")
        bot.run(BOT_TOKEN)

import os
import re
import datetime
from collections import defaultdict
import discord
from discord.ext import commands

# ---------------------------------------------------------------- #
# 1. إعدادات البوت
# ---------------------------------------------------------------- #

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# ---------------------------------------------------------------- #
# 2. القواميس والبيانات المخزنة في الذاكرة
# ---------------------------------------------------------------- #

# قاموس الكلمات المحظورة الخاص بك
BAD_WORDS = [
    "قحبة", "قحبه", "شرموطة", "شرموط", "شرموطه", "زانية", "زانيه", "زاني", "عاهرة", "عاهره",
    "مومس", "مومسة", "ديوث", "دويثان", "دويث", "ابن الزنا", "ولد الزنا", "ولد حرام", "بنت حرام",
    "عيال الحرام", "بنات الحرام", "منيوك", "منيوكه", "منيوكة", "منتاك", "متناكة", "كس", "زب",
    "مص", "نيك", "كس امك", "كس جدتك", "كس خالتك", "كس عمتك", "كس محارمك", "كس امواتك", "كس اهلك",
    "كس نسلك", "كس اجدادك", "يبن الشرموطتين", "يبن القحبه", "يبن الكاثولكية", "يبن النصرانية",
    "يبن المسيحية", "يبن المسيحيه", "يبن اليهودية", "يبن اليهوديه", "يبن الشيعية", "يبن الشيعيه",
    "يبن التمتع", "يبن المتعه", "يبن المتعة", "امك عندي", "امك قحبه", "امك قحبة", "كوس اومك",
    "كوس امك", "اومك", "امك", "يبن المترهله", "يبن المترهلة", "يبن الترهل", "يبن السمينة",
    "يبن السمينه", "يبن القواده", "يبن القوادة", "يبن القواد", "ياقواد", "هذا قواد", "فحل",
    "فحلتي", "احب النيك", "جرار", "ابن الجرار", "ياجرار", "كس عرضك", "كسم", "ياعيال القحبه",
    "ياعيال القحبة"
]

user_messages = defaultdict(list)
user_last_content = {}

# ---------------------------------------------------------------- #
# 3. نظام ذكي لكشف التشفير والحروف المتباعدة والمكررة (بدون ذكاء اصطناعي)
# ---------------------------------------------------------------- #
def build_anti_evasion_patterns(word_list):
    patterns = []
    for word in word_list:
        chars = []
        for char in word:
            if char == ' ':
                # السماح بوجود مسافات إضافية بين الكلمات
                chars.append(r'[\s\W]+')
            else:
                # السماح بتكرار الحرف أو وجود مسافات/رموز بين كل حرف وحرف
                chars.append(f'{char}+')
        
        core_pattern = r'[\s\W]*'.join(chars)
        # شرط (?<![أ-ي]) و (?![أ-ي]) يضمن أن الكلمة مستقلة وليست جزءاً من كلمة أخرى (مثل زبادي)
        full_pattern = fr'(?<![أ-يa-zA-Z]){core_pattern}(?![أ-يa-zA-Z])'
        patterns.append(re.compile(full_pattern, re.IGNORECASE))
    return patterns

BAD_PATTERNS = build_anti_evasion_patterns(BAD_WORDS)

def parse_duration(time_str: str) -> datetime.timedelta:
    time_str = time_str.strip().lower()
    match = re.match(r"(\d+)\s*([a-zA-Zأ-ي]+)?", time_str)
    if not match: return None
    amount = int(match.group(1))
    unit = match.group(2)
    if not unit: return datetime.timedelta(minutes=amount)
    if unit in ['ساعة', 'س', 'h', 'hours', 'hour']: return datetime.timedelta(hours=amount)
    elif unit in ['دقيقة', 'د', 'm', 'minutes', 'minute']: return datetime.timedelta(minutes=amount)
    elif unit in ['يوم', 'ي', 'd', 'days', 'day']: return datetime.timedelta(days=amount)
    return datetime.timedelta(minutes=amount)

# ---------------------------------------------------------------- #
# 4. الأحداث والأوامر
# ---------------------------------------------------------------- #

@bot.event
async def on_ready():
    print(f"تم تشغيل البوت بنجاح باسم: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    is_admin = message.author.guild_permissions.administrator or message.author.id == message.guild.owner_id
    
    if not is_admin:
        # ---- أ) نظام قاموس السب القوي (يكشف التشفير والمسافات) ----
        for pattern in BAD_PATTERNS:
            if pattern.search(message.content):
                try:
                    await message.delete()
                    await message.author.timeout(datetime.timedelta(minutes=1), reason="قول كلمة محظورة أو مشفرة")
                    await message.channel.send(f"⚠️ تم إسكات {message.author.mention} لمدة دقيقة لقول كلام غير لائق.", delete_after=5)
                    return 
                except Exception as e:
                    print(f"خطأ في تطبيق التايم آوت للكلمات المحظورة: {e}")

        # ---- ب) نظام مكافحة السبام (7 رسائل متطابقة في دقيقة) ----
        now = datetime.datetime.utcnow()
        current_user_id = message.author.id
        
        user_messages[current_user_id] = [t for t in user_messages[current_user_id] if (now - t).total_seconds() < 60]
        
        last_content = user_last_content.get(current_user_id)
        if last_content == message.content:
            user_messages[current_user_id].append(now)
        else:
            user_messages[current_user_id] = [now]
            user_last_content[current_user_id] = message.content

        if len(user_messages[current_user_id]) >= 7:
            try:
                await message.author.timeout(datetime.timedelta(minutes=9), reason="سبام وتكرار الرسائل")
                await message.channel.send(f"🚨 {message.author.mention} تم إسكاتك 9 دقائق بسبب السبام وتكرار الرسائل.", delete_after=10)
                user_messages[current_user_id].clear()
                return
            except Exception as e:
                print(f"خطأ في تطبيق تايم آوت السبام: {e}")

    # ---- ج) نظام الإدارة (أمر اسكت عبر الرد) ----
    if message.content.startswith("اسكت"):
        if is_admin:
            if message.reference and message.reference.message_id:
                try:
                    replied_message = await message.channel.fetch_message(message.reference.message_id)
                    target_member = replied_message.author
                    
                    if target_member.guild_permissions.administrator or target_member.bot:
                        await message.channel.send("❌ لا يمكنك إسكات هذا العضو.", delete_after=5)
                        return

                    command_parts = message.content.split(" ", 1)
                    if len(command_parts) < 2:
                        await message.channel.send("❓ يرجى تحديد المدة. مثال: `اسكت 1 ساعة` أو `اسكت 30د`", delete_after=5)
                        return
                    
                    duration_str = command_parts[1]
                    duration = parse_duration(duration_str)
                    
                    if duration:
                        await target_member.timeout(duration, reason=f"أمر إسكات من الإداري {message.author}")
                        await message.channel.send(f"🤐 تم إسكات {target_member.mention} بنجاح لمدة {duration_str}.", delete_after=10)
                    else:
                        await message.channel.send("❌ صيغة الوقت غير مفهومة. استخدم مثلاً: (1س، 30د، 1 ساعة).", delete_after=5)
                        
                except Exception as e:
                    await message.channel.send(f"❌ حدث خطأ أثناء تنفيذ الأمر أو نقص في الصلاحيات.", delete_after=5)
                    print(f"خطأ أمر اسكت: {e}")
            else:
                await message.channel.send("⚠️ يجب عليك الرد (Reply) على رسالة الشخص الذي تريد إسكاته ثم كتابة الأمر.", delete_after=5)

    await bot.process_commands(message)

if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("خطأ كاريثي: لم يتم العثور على التوكن DISCORD_TOKEN في بيئة التشغيل.")


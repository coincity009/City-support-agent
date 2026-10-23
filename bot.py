import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", "0"))

client = genai.Client(api_key=GEMINI_API_KEY)
user_topics = {}

SYSTEM_INSTRUCTION = """
তুমি 'Coin City' অ্যাপের অফিশিয়াল ২৪/৭ পেশাদার কাস্টমার সাপোর্ট এআই এজেন্ট।
তুমি সবসময় অত্যন্ত বিনয় ও নম্রতার সাথে সহজ ও সুন্দর বাংলায় সংক্ষিপ্ত উত্তর দেবে।

[COIN CITY APP DETAILS]
- অ্যাপের নাম: Coin City
- অ্যাপের কাজ: অ্যাপে বিভিন্ন সহজ টাস্ক (Task) সম্পন্ন করে, ক্যাচপা টাইপিং ও গেম খেলে কয়েন ইনকাম করা যায়।
- অ্যাকাউন্ট অ্যাক্টিভেশন ফি: ১৯০ টাকা (বিকাশ / নগদ: ০১৭XXXXXXXX)।
- অ্যাক্টিভেশন সময়: টাকা পাঠানোর পর TrxID এবং স্ক্রিনশট পাঠালে ৫ মিনিটের মধ্যে অ্যাকাউন্ট সক্রিয় হয়।
- পেমেন্ট তোলা (Withdrawal): সর্বনিম্ন ২০০ টাকা হলে বিকাশ বা নগদে টাকা তোলা যায়। ২৪ ঘণ্টার মধ্যে পেমেন্ট সম্পন্ন হয়।

[ছবি বা স্ক্রিনশট বিশ্লেষণ]
- ইউজার পেমেন্টের স্ক্রিনশট পাঠালে ছবি দেখে TrxID, টাকা পাঠানোর পরিমাণ এবং নম্বর সঠিক আছে কি না তা যাচাই করে জানাবে।

[বটের নিয়ম]
১. কেউ ফি বা অ্যাকাউন্ট চালু করার নিয়ম জানতে চাইলে বিকাশ/নগদ নম্বর এবং ১৯০ টাকা ফি-এর কথা স্পষ্ট করে বলবে।
২. গ্রাহক পেমেন্ট বা নিরাপত্তা নিয়ে চিন্তিত থাকলে তাকে আশ্বস্ত করবে।
৩. অ্যাপের বাইরের কোনো অপ্রাসঙ্গিক বিষয়ে কথা বলবে না।
৪. উত্তর সবসময় ২-৪ লাইনের মধ্যে সংক্ষেপে দেবে।
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("হ্যালো! আমি Coin City-র অফিশিয়াল কাস্টমার সাপোর্ট এআই এজেন্ট। অ্যাপ সম্পর্কিত কোনো প্রশ্ন বা সাহায্য লাগলে আমাকে লিখুন।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    user_id = user.id
    user_name = user.first_name
    user_text = update.message.text or ""

    contents = [user_text]

    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        contents = [
            types.Part.from_bytes(data=bytes(photo_bytes), mime_type="image/jpeg"),
            user_text or "এই ছবিটি বা স্ক্রিনশটটি দেখে আমাকে সাহায্য করুন।"
        ]

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2
            )
        )
        bot_reply = response.text

        await update.message.reply_text(bot_reply)

        if ADMIN_GROUP_ID != 0:
            if user_id not in user_topics:
                topic = await context.bot.create_forum_topic(
                    chat_id=ADMIN_GROUP_ID,
                    name=f"👤 {user_name} (ID: {user_id})"
                )
                user_topics[user_id] = topic.message_thread_id

            thread_id = user_topics[user_id]
            log_text = f"💬 **User:** {user_text or '[ছবি পাঠিয়েছেন]'}\n\n🤖 **AI Reply:** {bot_reply}"
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=log_text,
                message_thread_id=thread_id
            )

    except Exception as e:
        await update.message.reply_text("দুঃখিত, সাময়িক কারিগরি সমস্যার কারণে উত্তর দিতে দেরি হচ্ছে। কিছুক্ষণ পর আবার চেষ্টা করুন।")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    app.run_polling()


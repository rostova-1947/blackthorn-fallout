import os
import discord

TOKEN = os.getenv("DISCORD_TOKEN")
RP_EL_BOT_ID = os.getenv("RP_EL_BOT_ID")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Set it in Railway Variables.")
if not RP_EL_BOT_ID:
    raise RuntimeError("RP_EL_BOT_ID is missing. Set it in Railway Variables.")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    print(f"✅ Listening for RP-EL-BOT ID: {RP_EL_BOT_ID}")

@client.event
async def on_message(message: discord.Message):
    # Ignore itself
    if message.author.id == client.user.id:
        return

    # Debug: confirm we're receiving messages
    print("--- MESSAGE RECEIVED ---")
    print(f"Author: {message.author} | ID: {message.author.id}")
    print(f"Has embeds: {len(message.embeds)}")

    # Only listen to RP-EL-BOT
    if str(message.author.id) != str(RP_EL_BOT_ID):
        return

    print("🔥 DETECTED RP-EL-BOT MESSAGE")

    # RP-EL-BOT events are embeds
    if not message.embeds:
        print("⚠ RP-EL-BOT message had no embeds")
        return

    embed = message.embeds[0]
    print(f"Embed title: {embed.title}")

    # Trigger on any RP-EL event embeds (your titles look like: 'Event (Familial): ...')
    if embed.title and "Event" in embed.title:
        print("🔥 EVENT DETECTED - replying")
        await message.reply(
            "🔥 Fallout Bot detected an event. (Test successful)",
            mention_author=False
        )

client.run(TOKEN)

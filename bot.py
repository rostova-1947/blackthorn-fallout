import os
import discord

TOKEN = os.getenv("DISCORD_TOKEN")
RP_EL_BOT_ID = os.getenv("RP_EL_BOT_ID")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    # Ignore self
    if message.author == client.user:
        return

    # Only listen to RP-EL-BOT
    if str(message.author.id) != RP_EL_BOT_ID:
        return

    # Only care about embeds (rp-el-bot uses embeds)
    if not message.embeds:
        return

    embed = message.embeds[0]

    # Only respond to Event Rolls
    if embed.title and "Event Roll" in embed.title:
        await message.reply(
            "🔥 Fallout Bot detected an event. (Test successful)",
            mention_author=False
        )

client.run(TOKEN)

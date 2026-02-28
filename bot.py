import os
import re
import random
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

# ----------------------------
# Parsing
# ----------------------------

EVENT_TITLE_RE = re.compile(
    r"^.*Event\s*\((?P<rtype>[^)]+)\)\s*:\s*(?P<a>.+?)\s*↔\s*(?P<b>.+?)\s*$",
    re.IGNORECASE
)

def parse_rp_el_event_title(title: str):
    if not title:
        return None
    m = EVENT_TITLE_RE.match(title.strip())
    if not m:
        return None
    return (m.group("rtype").strip().lower(),
            m.group("a").strip(),
            m.group("b").strip())

def severity_from_rng(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.15:
        return "low"
    if roll < 0.70:
        return "medium"
    if roll < 0.92:
        return "high"
    return "critical"

def bellwether_chance(severity: str) -> float:
    return {"low": 0.10, "medium": 0.25, "high": 0.45, "critical": 0.65}[severity]

def barnes_chance(severity: str) -> float:
    return {"low": 0.08, "medium": 0.18, "high": 0.35, "critical": 0.55}[severity]

# ----------------------------
# Content tables
# ----------------------------

FALLOUT_TEMPLATES = {
    "familial": {
        "immediate": [
            "A silence sets in that feels intentional. People avoid names and avoid eye contact.",
            "Old roles snap back into place—caretaker, problem, fixer—whether anyone wants them or not.",
            "Someone says something small that lands like a blade. Nobody apologizes."
        ],
        "short": [
            "Work coordination breaks down. Chores get duplicated or skipped; the ranch starts to show it.",
            "A third party gets pulled in as a mediator, and resentments reroute toward them.",
            "One of them ‘proves a point’ with stubbornness—dangerous with animals, equipment, or weather."
        ],
        "long": [
            "This becomes a fault line: the next crisis will split along the same seam.",
            "Family loyalty turns into leverage. Favors get tallied. People remember who showed up and who didn’t.",
            "The conflict fossilizes into a pattern—predictable, repeatable, and therefore weaponizable."
        ],
        "echo": [
            "It returns at the kitchen table when everyone’s already tired.",
            "It resurfaces at the arena/clinic/barn—public enough to hurt, private enough to deny.",
            "It comes back at the creek line or fence line—where history lives in the dirt."
        ],
    },
    "platonic": {
        "immediate": [
            "A joke lands wrong. It’s subtle, but it changes the temperature.",
            "Someone acts ‘fine’ with a little too much effort.",
            "A boundary gets tested in a way that can be played off later."
        ],
        "short": [
            "The friendship becomes conditional: who’s useful, who’s loyal, who’s disposable.",
            "A rumor gains traction because neither of them shuts it down quickly enough.",
            "One of them starts keeping score—time, favors, money, secrets."
        ],
        "long": [
            "This either hardens into true loyalty or collapses under pressure—no middle ground.",
            "A future betrayal becomes easier because the trust already has a hairline fracture.",
            "Their circle picks sides in small ways until it’s impossible to pretend it isn’t happening."
        ],
        "echo": [
            "It reappears in a moment of need—when one expects help and doesn’t get it.",
            "It surfaces during a long drive home—too much time, nowhere to put the truth.",
            "It comes back when someone else mentions it offhand and both realize it’s ‘a thing’ now."
        ],
    },
    "romantic": {
        "immediate": [
            "Affection turns sharp at the edges—too intense, too fast, too defensive.",
            "One reaches, the other flinches. Both pretend it didn’t happen.",
            "Jealousy shows up as ‘concern’ and nobody believes it."
        ],
        "short": [
            "They start negotiating control: time, attention, who gets to be hurt first.",
            "An outside pressure (family, ex, money, the arena) pushes directly on them.",
            "A moment of tenderness gets interrupted, and the interruption becomes the point."
        ],
        "long": [
            "Love becomes a trigger: the closer they get, the more violently old wounds react.",
            "This becomes the fight they keep having, just with different props.",
            "If it survives, it changes them. If it doesn’t, it scars the whole community."
        ],
        "echo": [
            "It returns the next time someone says ‘we’re fine’ and both know it’s a lie.",
            "It comes back as a memory at the worst possible time.",
            "It resurfaces the moment one tries to leave."
        ],
    },
    "_default": {
        "immediate": [
            "The moment leaves residue. People keep moving, but something sticks.",
            "A choice gets made in anger or fear, and it can’t be unmade."
        ],
        "short": [
            "Small complications stack up: timing, tools, tempers, weather.",
            "Someone tries to control the narrative, and someone else resents it."
        ],
        "long": [
            "This becomes a known story—told differently depending on who’s speaking.",
            "The consequences land later, when nobody’s looking for them."
        ],
        "echo": [
            "It returns during the next crisis, louder than before.",
            "It comes back when the land ‘answers back’—animals, drought, fire, rot."
        ],
    },
}

RANCH_COMPLICATIONS = [
    "A gate is left unlatched. Somebody’s going to spend hours fixing it.",
    "A horse spooks at the wrong moment—no one gets hurt, but it could’ve been worse.",
    "Equipment acts up (fuel line, strap, latch). It’s minor… until it isn’t.",
    "A calf goes down unexpectedly. The timing is cruel.",
    "Feed supply runs short earlier than expected. Money starts to pinch.",
    "A dry wind picks up. Everything feels one spark away."
]

BARNES_PRESSURE = [
    "Barnes hears about it. Not official—just enough to clock the pattern.",
    "Barnes steps in with that calm voice that means ‘don’t make me do paperwork.’",
    "Barnes makes it clear: next time, he’s not asking twice.",
    "Barnes doesn’t intervene… which is worse. It means he’s watching."
]

BELLWETHER_WHISPERS = [
    "The tension lasts too long. It should’ve burned off—yet it clings to the room like smoke.",
    "A thought repeats that doesn’t feel like theirs: accuse, abandon, escalate.",
    "The worst interpretation becomes the easiest one to believe.",
    "Grief/anger feels amplified—like someone turned the volume knob without touching the stereo."
]

def generate_fallout(rtype: str, a: str, b: str, seed: int,
                     force_barnes: bool = False,
                     force_bellwether: bool = False,
                     severity_floor: str | None = None) -> dict:
    rng = random.Random(seed)

    severity = severity_from_rng(rng)
    if severity_floor:
        order = ["low", "medium", "high", "critical"]
        if order.index(severity) < order.index(severity_floor):
            severity = severity_floor

    tpl = FALLOUT_TEMPLATES.get(rtype, FALLOUT_TEMPLATES["_default"])
    immediate = rng.choice(tpl["immediate"])
    short = rng.choice(tpl["short"])
    long = rng.choice(tpl["long"])
    echo = rng.choice(tpl["echo"])

    ranch = rng.choice(RANCH_COMPLICATIONS) if rng.random() < 0.35 else None
    barnes = None
    bell = None

    if force_barnes or (rng.random() < barnes_chance(severity)):
        barnes = rng.choice(BARNES_PRESSURE)

    if force_bellwether or (rng.random() < bellwether_chance(severity)):
        bell = rng.choice(BELLWETHER_WHISPERS)

    tags = ["blackthorn", rtype, severity]
    if ranch: tags.append("ranch")
    if barnes: tags.append("barnes")
    if bell: tags.append("bellwether")

    return {
        "severity": severity,
        "summary": f"Event ({rtype.title()}): {a} ↔ {b}",
        "immediate": immediate,
        "short": short,
        "long": long,
        "echo": echo,
        "ranch": ranch,
        "barnes": barnes,
        "bellwether": bell,
        "tags": tags,
        "seed": seed
    }

def fallout_embed(payload: dict) -> discord.Embed:
    emb = discord.Embed(
        title=f"⚠ Fallout ({payload['severity'].upper()})",
        description=payload["summary"]
    )
    emb.add_field(name="Immediate", value=payload["immediate"], inline=False)
    emb.add_field(name="Short-term", value=payload["short"], inline=False)
    emb.add_field(name="Long-term", value=payload["long"], inline=False)
    emb.add_field(name="Echo", value=payload["echo"], inline=False)

    if payload["ranch"]:
        emb.add_field(name="Ranch / Land", value=payload["ranch"], inline=False)
    if payload["barnes"]:
        emb.add_field(name="Sheriff Barnes", value=payload["barnes"], inline=False)
    if payload["bellwether"]:
        emb.add_field(name="Bellwether Interference", value=payload["bellwether"], inline=False)

    emb.set_footer(text=f"Tags: {', '.join(payload['tags'])} | Seed: {payload['seed']}")
    return emb

async def fetch_source_event(interaction: discord.Interaction):
    """
    The button message is a reply to the RP-EL event message.
    We use the reply reference to fetch the source.
    """
    ref = interaction.message.reference
    if not ref or not ref.message_id:
        return None

    # Usually same channel; if not, try fetching by channel_id
    channel = interaction.channel
    if ref.channel_id and hasattr(interaction.guild, "get_channel"):
        ch = interaction.guild.get_channel(ref.channel_id)
        if ch:
            channel = ch

    try:
        src_msg = await channel.fetch_message(ref.message_id)
    except Exception:
        return None

    if not src_msg.embeds:
        return None

    src_embed = src_msg.embeds[0]
    parsed = parse_rp_el_event_title(src_embed.title or "")
    if not parsed:
        return None

    rtype, a, b = parsed
    seed = int(src_msg.id) % (2**31 - 1)
    return {"rtype": rtype, "a": a, "b": b, "seed": seed, "src_id": src_msg.id}

# ----------------------------
# Persistent buttons (work after restarts)
# ----------------------------

class FalloutToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔥 Generate Fallout",
        style=discord.ButtonStyle.danger,
        custom_id="bt_fallout"
    )
    async def btn_fallout(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("I can't find the source RP-EL event for this button.", ephemeral=True)
            return

        payload = generate_fallout(ctx["rtype"], ctx["a"], ctx["b"], ctx["seed"])
        await interaction.response.send_message(embed=fallout_embed(payload))

    @discord.ui.button(
        label="⚖ Barnes Response",
        style=discord.ButtonStyle.secondary,
        custom_id="bt_barnes"
    )
    async def btn_barnes(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("I can't find the source RP-EL event for this button.", ephemeral=True)
            return

        rng = random.Random(ctx["seed"] + 101)
        emb = discord.Embed(
            title="⚖ Sheriff Barnes",
            description=f"Event ({ctx['rtype'].title()}): {ctx['a']} ↔ {ctx['b']}"
        )
        emb.add_field(name="Pressure", value=rng.choice(BARNES_PRESSURE), inline=False)
        await interaction.response.send_message(embed=emb)

    @discord.ui.button(
        label="🕯 Bellwether Pulse",
        style=discord.ButtonStyle.secondary,
        custom_id="bt_bellwether"
    )
    async def btn_bellwether(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("I can't find the source RP-EL event for this button.", ephemeral=True)
            return

        rng = random.Random(ctx["seed"] + 202)
        emb = discord.Embed(
            title="🕯 Bellwether Pulse",
            description=f"Event ({ctx['rtype'].title()}): {ctx['a']} ↔ {ctx['b']}"
        )
        emb.add_field(name="Interference", value=rng.choice(BELLWETHER_WHISPERS), inline=False)
        await interaction.response.send_message(embed=emb)

    @discord.ui.button(
        label="🎲 Escalate",
        style=discord.ButtonStyle.primary,
        custom_id="bt_escalate"
    )
    async def btn_escalate(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("I can't find the source RP-EL event for this button.", ephemeral=True)
            return

        # Escalate: enforce high severity + force bellwether + slightly shifted seed
        payload = generate_fallout(
            ctx["rtype"], ctx["a"], ctx["b"],
            seed=ctx["seed"] + 999,
            force_bellwether=True,
            severity_floor="high"
        )
        emb = fallout_embed(payload)
        emb.title = f"🚨 Escalated Fallout ({payload['severity'].upper()})"
        await interaction.response.send_message(embed=emb)

# ----------------------------
# Discord handlers
# ----------------------------

@client.event
async def on_ready():
    # Register persistent view so buttons still work after restarts
    client.add_view(FalloutToolsView())
    print(f"✅ Logged in as {client.user}")
    print(f"✅ Listening for RP-EL-BOT ID: {RP_EL_BOT_ID}")

@client.event
async def on_message(message: discord.Message):
    if message.author.id == client.user.id:
        return

    # Only listen to RP-EL-BOT
    if str(message.author.id) != str(RP_EL_BOT_ID):
        return

    if not message.embeds:
        return

    embed = message.embeds[0]
    parsed = parse_rp_el_event_title(embed.title or "")
    if not parsed:
        return

    rtype, a, b = parsed

    # Instead of auto-posting fallout, post button toolbox under the event
    await message.reply(
        content=f"🧰 **Fallout Tools Ready** — Event ({rtype.title()}): **{a} ↔ {b}**\n"
                f"Use buttons to generate fallout / Barnes / Bellwethers / escalation.",
        view=FalloutToolsView(),
        mention_author=False
    )

client.run(TOKEN)

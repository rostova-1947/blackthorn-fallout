import os
import re
import random
import discord

# =========================
# ENV VARS (Railway Variables)
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
RP_EL_BOT_ID = os.getenv("RP_EL_BOT_ID")
BELLWETHER_OVERRIDE_CHANCE = float(os.getenv("BELLWETHER_OVERRIDE_CHANCE", "0.10"))  # e.g. 0.05

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing. Set it in Railway Variables.")
if not RP_EL_BOT_ID:
    raise RuntimeError("RP_EL_BOT_ID is missing. Set it in Railway Variables.")

# =========================
# DISCORD CLIENT
# =========================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# =========================
# FALLBACK TITLE PARSER (if fields missing)
# =========================
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

# =========================
# EMBED FIELD READERS (PRIMARY)
# =========================
def get_embed_field(embed: discord.Embed, field_name: str) -> str | None:
    if not embed or not embed.fields:
        return None
    target = field_name.strip().lower()
    for f in embed.fields:
        if (f.name or "").strip().lower() == target:
            return (f.value or "").strip()
    return None

def parse_tags_field(tags_value: str | None) -> list[str]:
    if not tags_value:
        return []
    parts = [p.strip().lower() for p in tags_value.split(",")]
    return [p for p in parts if p and p != "—" and p != "-"]

def clamp_prob(p: float) -> float:
    return max(0.0, min(0.95, p))

def rng_from_message_id(message_id: int) -> random.Random:
    seed = int(message_id) % (2**31 - 1)
    return random.Random(seed)

ALLOWED_INTENSITIES = {"high", "critical"}

def normalize_intensity(x: str | None) -> str | None:
    if not x:
        return None
    x = x.strip().lower()
    if x in {"low", "med", "medium", "high", "critical"}:
        return "med" if x == "medium" else x
    return None

def normalize_polarity(x: str | None) -> str | None:
    if not x:
        return None
    x = x.strip().lower()
    if x in {"positive", "negative", "mixed"}:
        return x
    return None

def normalize_rtype(x: str | None) -> str:
    if not x:
        return "_default"
    x = x.strip().lower()
    if x in {"romantic", "platonic", "familial"}:
        return x
    return "_default"

# =========================
# TAG BIAS (simple + expandable)
# =========================
def tag_bias(tags: list[str]) -> dict:
    tags_set = set(tags)
    bias = {
        "bellwether_bonus": 0.0,
        "barnes_bonus": 0.0,
        "ranch_bonus": 0.0,
    }

    # Bellwether-flavored tags
    if {"grief", "rage", "hate", "paranoia", "curse", "bellwether", "ominous"}.intersection(tags_set):
        bias["bellwether_bonus"] += 0.15

    # Law/trouble tags
    if {"law", "sheriff", "fight", "violence", "gun", "bar", "dui", "crime", "assault"}.intersection(tags_set):
        bias["barnes_bonus"] += 0.15

    # Ranch/land tags
    if {"ranch", "arena", "livestock", "fire", "wildfire", "drought", "blight", "storm"}.intersection(tags_set):
        bias["ranch_bonus"] += 0.15

    return bias

# =========================
# CONTENT TABLES
# =========================
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
    "A dry wind picks up. Everything feels one spark away.",
    "Livestock get spooked at dusk—fences rattle, hooves churn, and someone ends up in the dirt.",
    "A strange blight shows up in the pasture: patchy, fast, wrong.",
    "A wildfire warning hits the scanner. It’s not close—until it is.",
]

BARNES_PRESSURE = [
    "Barnes hears about it. Not official—just enough to clock the pattern.",
    "Barnes steps in with that calm voice that means ‘don’t make me do paperwork.’",
    "Barnes makes it clear: next time, he’s not asking twice.",
    "Barnes doesn’t intervene… which is worse. It means he’s watching.",
    "Barnes asks a question that sounds casual. It isn’t.",
]

BELLWETHER_WHISPERS = [
    "The tension lasts too long. It should’ve burned off—yet it clings to the room like smoke.",
    "A thought repeats that doesn’t feel like theirs: accuse, abandon, escalate.",
    "The worst interpretation becomes the easiest one to believe.",
    "Grief/anger feels amplified—like someone turned the volume knob without touching the stereo.",
    "Animals go quiet. The air feels ‘listening.’",
]

def severity_from_rng(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.15:
        return "low"
    if r < 0.70:
        return "medium"
    if r < 0.92:
        return "high"
    return "critical"

def bellwether_chance(severity: str) -> float:
    return {"low": 0.10, "medium": 0.25, "high": 0.45, "critical": 0.65}[severity]

def barnes_chance(severity: str) -> float:
    return {"low": 0.08, "medium": 0.18, "high": 0.35, "critical": 0.55}[severity]

def generate_fallout(
    rtype: str,
    a: str,
    b: str,
    seed: int,
    tags: list[str],
    force_barnes: bool = False,
    force_bellwether: bool = False,
    severity_floor: str | None = None
) -> dict:
    rng = random.Random(seed)
    bias = tag_bias(tags)

    severity = severity_from_rng(rng)
    if severity_floor:
        order = ["low", "medium", "high", "critical"]
        if order.index(severity) < order.index(severity_floor):
            severity = severity_floor

    tpl = FALLOUT_TEMPLATES.get(rtype, FALLOUT_TEMPLATES["_default"])

    payload = {
        "severity": severity,
        "summary": f"Event ({rtype.title()}): {a} ↔ {b}",
        "immediate": rng.choice(tpl["immediate"]),
        "short": rng.choice(tpl["short"]),
        "long": rng.choice(tpl["long"]),
        "echo": rng.choice(tpl["echo"]),
        "ranch": None,
        "barnes": None,
        "bellwether": None,
        "tags": ["blackthorn", rtype, severity] + (tags or []),
        "seed": seed,
    }

    # Ranch chance (biased by tags)
    if rng.random() < clamp_prob(0.35 + bias["ranch_bonus"]):
        payload["ranch"] = rng.choice(RANCH_COMPLICATIONS)

    # Barnes chance (biased by tags)
    if force_barnes or (rng.random() < clamp_prob(barnes_chance(severity) + bias["barnes_bonus"])):
        payload["barnes"] = rng.choice(BARNES_PRESSURE)

    # Bellwether chance (biased by tags)
    if force_bellwether or (rng.random() < clamp_prob(bellwether_chance(severity) + bias["bellwether_bonus"])):
        payload["bellwether"] = rng.choice(BELLWETHER_WHISPERS)

    return payload

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

    # show tags (trim if huge)
    tags = payload.get("tags") or []
    tag_str = ", ".join(tags[:25]) + (" …" if len(tags) > 25 else "")
    emb.set_footer(text=f"Tags: {tag_str} | Seed: {payload['seed']}")
    return emb

# =========================
# SOURCE EVENT FETCH (button message is a reply to RP-EL event)
# =========================
async def fetch_source_event(interaction: discord.Interaction):
    ref = interaction.message.reference
    if not ref or not ref.message_id:
        return None

    channel = interaction.channel
    if ref.channel_id and interaction.guild:
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

    # PRIMARY: read structured fields from Core bot
    pair_val = get_embed_field(src_embed, "Pair")
    type_val = get_embed_field(src_embed, "Type")
    intensity_val = normalize_intensity(get_embed_field(src_embed, "Intensity"))
    polarity_val = normalize_polarity(get_embed_field(src_embed, "Polarity"))
    tags = parse_tags_field(get_embed_field(src_embed, "Tags"))

    # derive a/b from Pair if present
    a = b = None
    if pair_val and "↔" in pair_val:
        parts = [p.strip() for p in pair_val.split("↔", 1)]
        if len(parts) == 2:
            a, b = parts[0], parts[1]

    rtype = normalize_rtype(type_val)

    # FALLBACK: parse title if missing
    if not a or not b:
        parsed = parse_rp_el_event_title(src_embed.title or "")
        if parsed:
            rtype2, a2, b2 = parsed
            rtype = normalize_rtype(rtype2) if not type_val else rtype
            a = a or a2
            b = b or b2

    if not a or not b:
        return None

    seed = int(src_msg.id) % (2**31 - 1)

    return {
        "rtype": rtype,
        "a": a,
        "b": b,
        "seed": seed,
        "src_id": src_msg.id,
        "intensity": intensity_val,
        "polarity": polarity_val,
        "tags": tags,
    }

# =========================
# PERSISTENT BUTTONS
# =========================
class FalloutToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔥 Generate Fallout", style=discord.ButtonStyle.danger, custom_id="bt_fallout")
    async def btn_fallout(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("Can't find the source RP-EL event for this button.", ephemeral=True)
            return

        payload = generate_fallout(ctx["rtype"], ctx["a"], ctx["b"], ctx["seed"], tags=ctx["tags"])
        await interaction.response.send_message(embed=fallout_embed(payload))

    @discord.ui.button(label="⚖ Barnes Response", style=discord.ButtonStyle.secondary, custom_id="bt_barnes")
    async def btn_barnes(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("Can't find the source RP-EL event for this button.", ephemeral=True)
            return

        rng = random.Random(ctx["seed"] + 101)
        emb = discord.Embed(
            title="⚖ Sheriff Barnes",
            description=f"Event ({ctx['rtype'].title()}): {ctx['a']} ↔ {ctx['b']}"
        )
        emb.add_field(name="Pressure", value=rng.choice(BARNES_PRESSURE), inline=False)
        await interaction.response.send_message(embed=emb)

    @discord.ui.button(label="🕯 Bellwether Pulse", style=discord.ButtonStyle.secondary, custom_id="bt_bellwether")
    async def btn_bellwether(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("Can't find the source RP-EL event for this button.", ephemeral=True)
            return

        rng = random.Random(ctx["seed"] + 202)
        emb = discord.Embed(
            title="🕯 Bellwether Pulse",
            description=f"Event ({ctx['rtype'].title()}): {ctx['a']} ↔ {ctx['b']}"
        )
        emb.add_field(name="Interference", value=rng.choice(BELLWETHER_WHISPERS), inline=False)
        await interaction.response.send_message(embed=emb)

    @discord.ui.button(label="🎲 Escalate", style=discord.ButtonStyle.primary, custom_id="bt_escalate")
    async def btn_escalate(self, interaction: discord.Interaction, button: discord.ui.Button):
        ctx = await fetch_source_event(interaction)
        if not ctx:
            await interaction.response.send_message("Can't find the source RP-EL event for this button.", ephemeral=True)
            return

        payload = generate_fallout(
            ctx["rtype"], ctx["a"], ctx["b"],
            seed=ctx["seed"] + 999,
            tags=ctx["tags"],
            force_bellwether=True,
            severity_floor="high",
        )
        emb = fallout_embed(payload)
        emb.title = f"🚨 Escalated Fallout ({payload['severity'].upper()})"
        await interaction.response.send_message(embed=emb)

# =========================
# DISCORD EVENTS
# =========================
@client.event
async def on_ready():
    client.add_view(FalloutToolsView())  # persistent buttons across restarts
    print(f"✅ Logged in as {client.user}")
    print(f"✅ Listening for RP-EL-BOT ID: {RP_EL_BOT_ID}")
    print(f"✅ Bellwether override chance: {BELLWETHER_OVERRIDE_CHANCE}")

@client.event
async def on_message(message: discord.Message):
    # Ignore self
    if message.author.id == client.user.id:
        return

    # Only listen to RP-EL-BOT
    if str(message.author.id) != str(RP_EL_BOT_ID):
        return

    # Must have embeds
    if not message.embeds:
        return

    embed = message.embeds[0]

    # Prefer structured fields from Core bot
    pair_val = get_embed_field(embed, "Pair")
    type_val = get_embed_field(embed, "Type")
    intensity = normalize_intensity(get_embed_field(embed, "Intensity"))
    polarity = normalize_polarity(get_embed_field(embed, "Polarity"))
    tags = parse_tags_field(get_embed_field(embed, "Tags"))

    # Fallback parse (if needed)
    a = b = None
    if pair_val and "↔" in pair_val:
        parts = [p.strip() for p in pair_val.split("↔", 1)]
        if len(parts) == 2:
            a, b = parts[0], parts[1]
    if not a or not b:
        parsed = parse_rp_el_event_title(embed.title or "")
        if parsed:
            _, a2, b2 = parsed
            a = a or a2
            b = b or b2

    if not a or not b:
        return

    rtype = normalize_rtype(type_val)

    # Deterministic override based on the RP-EL message id
    rng = rng_from_message_id(message.id)
    bias = tag_bias(tags)
    override_chance = clamp_prob(BELLWETHER_OVERRIDE_CHANCE + bias["bellwether_bonus"])
    bellwether_override = (rng.random() < override_chance)

    # Gate: only show toolbox for HIGH/CRITICAL, unless override triggers
    if intensity not in ALLOWED_INTENSITIES and not bellwether_override:
        return

    # Toolbox message content
    intensity_show = intensity or "unknown"
    tag_line = f"**Tags:** {', '.join(tags)}" if tags else "**Tags:** —"

    if bellwether_override and intensity not in ALLOWED_INTENSITIES:
        header = "🧰 **Fallout Tools Ready** — 🕯 **Bellwether Override**"
    else:
        header = "🧰 **Fallout Tools Ready**"

    await message.reply(
        content=(
            f"{header}\n"
            f"Event ({rtype.title()}): **{a} ↔ {b}** (Intensity: **{intensity_show}**)\n"
            f"{tag_line}\n"
            f"Use buttons to generate Fallout / Barnes / Bellwether / Escalate."
        ),
        view=FalloutToolsView(),
        mention_author=False
    )

client.run(TOKEN)

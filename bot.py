import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import json
import os

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "roles.json"

# === Données dynamiques chargées/sauvegardées ===
data = {
    "message_id": None,
    "buttons": {}  # emoji: {role_id: int, exclusive: bool}
}


def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


class RoleButtonView(View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for emoji, info in data["buttons"].items():
            role = self.guild.get_role(info["role_id"])
            if not role:
                continue

            button = Button(label=role.name, emoji=emoji, style=discord.ButtonStyle.primary)

            async def callback(interaction: discord.Interaction, r=role, exclusive=info["exclusive"]):
                member = interaction.user
                if exclusive:
                    removed = []
                    for btn in data["buttons"].values():
                        if btn["exclusive"]:
                            other = self.guild.get_role(btn["role_id"])
                            if other and other in member.roles:
                                await member.remove_roles(other)
                                removed.append(other.name)

                    await member.add_roles(r)
                    msg = f"✅ Rôle `{r.name}` ajouté."
                    if removed:
                        msg += f" ❌ Rôles retirés : {', '.join(removed)}"
                    await interaction.response.send_message(msg, ephemeral=True)

                else:
                    if r in member.roles:
                        await member.remove_roles(r)
                        await interaction.response.send_message(f"❌ Rôle `{r.name}` retiré.", ephemeral=True)
                    else:
                        await member.add_roles(r)
                        await interaction.response.send_message(f"✅ Rôle `{r.name}` ajouté.", ephemeral=True)

            button.callback = callback
            self.add_item(button)


@bot.event
async def on_ready():
    load_data()
    await tree.sync()
    print(f"✅ Connecté en tant que {bot.user}")


@tree.command(name="initroles", description="Créer un embed pour la gestion des rôles")
@app_commands.checks.has_permissions(administrator=True)
async def initroles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Choisis ton rôle",
        description="Clique sur un bouton pour obtenir ou retirer un rôle.",
        color=discord.Color.blurple()
    )

    view = RoleButtonView(interaction.guild)
    message = await interaction.channel.send(embed=embed, view=view)

    data["message_id"] = message.id
    save_data()

    await interaction.response.send_message("✅ Embed créé avec succès.", ephemeral=True)


@tree.command(name="addrolebutton", description="Ajoute un bouton de rôle avec emoji")
@app_commands.describe(emoji="Emoji du bouton", role="Rôle à lier", exclusif="Ce rôle est-il exclusif ?")
@app_commands.checks.has_permissions(administrator=True)
async def addrolebutton(interaction: discord.Interaction, emoji: str, role: discord.Role, exclusif: bool = False):
    if emoji in data["buttons"]:
        await interaction.response.send_message("❌ Cet emoji est déjà utilisé.", ephemeral=True)
        return

    data["buttons"][emoji] = {
        "role_id": role.id,
        "exclusive": exclusif
    }
    save_data()

    try:
        message = await interaction.channel.fetch_message(data["message_id"])
        view = RoleButtonView(interaction.guild)
        await message.edit(view=view)
        await interaction.response.send_message(f"✅ Bouton pour `{role.name}` ajouté.", ephemeral=True)
    except:
        await interaction.response.send_message("⚠️ Message non trouvé. Utilise `/initroles` d'abord.", ephemeral=True)


@tree.command(name="removerolebutton", description="Supprimer un bouton de rôle")
@app_commands.describe(emoji="Emoji du bouton à retirer")
@app_commands.checks.has_permissions(administrator=True)
async def removerolebutton(interaction: discord.Interaction, emoji: str):
    if emoji not in data["buttons"]:
        await interaction.response.send_message("❌ Aucun bouton associé à cet emoji.", ephemeral=True)
        return

    del data["buttons"][emoji]
    save_data()

    try:
        message = await interaction.channel.fetch_message(data["message_id"])
        view = RoleButtonView(interaction.guild)
        await message.edit(view=view)
        await interaction.response.send_message(f"🗑️ Bouton `{emoji}` supprimé.", ephemeral=True)
    except:
        await interaction.response.send_message("⚠️ Message non trouvé. Utilise `/initroles` si nécessaire.", ephemeral=True)


bot.run("MTM1ODYxMTEwNDk3MjE0ODgxNg.Gan2H5.c2M8spjfwKaVZEp94BAODPjDKq_h3MwwJCmkV0")


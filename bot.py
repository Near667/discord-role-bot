import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# Bot initialization
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # For slash commands

ROLES_FILE = "roles.json"

# Load role data from JSON file
def load_data():
    if not os.path.exists(ROLES_FILE) or os.path.getsize(ROLES_FILE) == 0:
        with open(ROLES_FILE, "w") as f:
            json.dump({}, f)
    with open(ROLES_FILE, "r") as f:
        return json.load(f)

# Save role data to JSON file
def save_data(data):
    if not isinstance(data, dict):
        data = {}
    with open(ROLES_FILE, "w") as f:
        json.dump(data, f, indent=4)


# View that holds all role buttons
class RoleButtonView(discord.ui.View):
    def __init__(self, roles_dict, unique_roles=None):
        super().__init__(timeout=None)
        self.unique_roles = unique_roles or []

        for role_id, label in roles_dict.items():
            self.add_item(RoleButton(role_id, label, self.unique_roles))

# A single role toggle button
class RoleButton(discord.ui.Button):
    def __init__(self, role_id, label, unique_roles):
        super().__init__(label=label, custom_id=str(role_id), style=discord.ButtonStyle.primary)
        self.role_id = int(role_id)
        self.unique_roles = unique_roles

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        role = guild.get_role(self.role_id)

        if role is None:
            await interaction.response.send_message("⚠️ This role no longer exists.", ephemeral=True)
            return

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"❌ Removed role **{role.name}**.", ephemeral=True)
        else:
            if role.id in self.unique_roles:
                others_to_remove = [r for r in member.roles if r.id in self.unique_roles and r != role]
                if others_to_remove:
                    await member.remove_roles(*others_to_remove)
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Added role **{role.name}**.", ephemeral=True)

# Event: When the bot is ready
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

# Slash command: Add a role button
@tree.command(name="addrolebutton", description="Add a button to assign a role")
@app_commands.describe(role="Role to assign", label="Button label", unique="Limit to one selectable role?")
async def add_role_button(interaction: discord.Interaction, role: discord.Role, label: str, unique: bool = False):
    data = load_data()
    guild_id = str(interaction.guild_id)

    if guild_id not in data:
        data[guild_id] = {"roles": {}, "unique": []}

    data[guild_id]["roles"][str(role.id)] = label

    if unique and role.id not in data[guild_id]["unique"]:
        data[guild_id]["unique"].append(role.id)

    save_data(data)
    await interaction.response.send_message(f"✅ Role button for **{role.name}** added.")

# Slash command: Remove a role button
@tree.command(name="removerolebutton", description="Remove a role button")
@app_commands.describe(role="Role to remove")
async def remove_role_button(interaction: discord.Interaction, role: discord.Role):
    data = load_data()
    guild_id = str(interaction.guild_id)

    if guild_id in data and str(role.id) in data[guild_id]["roles"]:
        del data[guild_id]["roles"][str(role.id)]
        if role.id in data[guild_id]["unique"]:
            data[guild_id]["unique"].remove(role.id)
        save_data(data)
        await interaction.response.send_message(f"🗑️ Removed button for role **{role.name}**.")
    else:
        await interaction.response.send_message("❌ No button found for that role.")

# Slash command: Send the role selection message
@tree.command(name="sendrolebuttons", description="Send the message with all role buttons")
async def send_role_buttons(interaction: discord.Interaction):
    data = load_data()
    guild_id = str(interaction.guild_id)

    if guild_id not in data or not data[guild_id]["roles"]:
        await interaction.response.send_message("⚠️ No role buttons have been configured.", ephemeral=True)
        return

    embed = discord.Embed(title="Choose your role 🎭", color=discord.Color.blurple())
    for role_id, label in data[guild_id]["roles"].items():
        embed.add_field(name=label, value=f"<@&{role_id}>", inline=True)

    view = RoleButtonView(data[guild_id]["roles"], unique_roles=data[guild_id].get("unique", []))

    # ✅ ENVOI DIRECT via l’interaction (1 seule réponse)
    await interaction.response.send_message(embed=embed, view=view)


bot.run(os.getenv("DISCORD_TOKEN"))


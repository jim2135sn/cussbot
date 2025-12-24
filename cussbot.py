import discord
from discord import app_commands
import json
import random
import os
import time

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

cuss_words = []
responses = []

COUNTS_FILE = "counts.json"
USERS_FILE = "users.json"
SERVER_CONFIG_FILE = "server_config.json"

counts = {
    "global_total": 0,
    "server_totals": {},
    "global_users": {},
    "server_users": {}
}

users = {}

server_config = {}

user_cooldowns = {}
COOLDOWN_TRIGGER_COUNT = 3
COOLDOWN_TRIGGER_WINDOW = 3
COOLDOWN_DURATION = 10

def load_counts():
    global counts
    try:
        with open(COUNTS_FILE, 'r') as f:
            loaded = json.load(f)
            counts.update(loaded)
    except FileNotFoundError:
        pass

def save_counts():
    with open(COUNTS_FILE, 'w') as f:
        json.dump(counts, f, indent=2)

def load_users():
    global users
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    except FileNotFoundError:
        users = {}

def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_server_config():
    global server_config
    try:
        with open(SERVER_CONFIG_FILE, 'r') as f:
            server_config = json.load(f)
    except FileNotFoundError:
        server_config = {}

def save_server_config():
    with open(SERVER_CONFIG_FILE, 'w') as f:
        json.dump(server_config, f, indent=2)

def get_server_settings(server_id: str) -> dict:
    if server_id not in server_config:
        server_config[server_id] = {
            "response_channel": None,
            "responses_enabled": True
        }
    return server_config[server_id]

def check_cooldown(user_id: str) -> bool:
    current_time = time.time()
    
    if user_id not in user_cooldowns:
        user_cooldowns[user_id] = {"times": [], "cooldown_until": 0}
    
    cooldown_data = user_cooldowns[user_id]
    
    if current_time < cooldown_data["cooldown_until"]:
        return True
    
    cooldown_data["times"] = [t for t in cooldown_data["times"] if current_time - t < COOLDOWN_TRIGGER_WINDOW]
    
    cooldown_data["times"].append(current_time)
    
    if len(cooldown_data["times"]) >= COOLDOWN_TRIGGER_COUNT:
        cooldown_data["cooldown_until"] = current_time + COOLDOWN_DURATION
        cooldown_data["times"] = []
        return True
    
    return False

def add_user_cuss(user_id: str, username: str, server_id: str):
    if user_id not in users:
        users[user_id] = {
            "name": username,
            "total": 0,
            "servers": {}
        }
    
    users[user_id]["name"] = username
    users[user_id]["total"] += 1
    
    if server_id not in users[user_id]["servers"]:
        users[user_id]["servers"][server_id] = 0
    users[user_id]["servers"][server_id] += 1
    
    save_users()

def add_cuss(server_id: str, user_id: str, username: str):
    counts["global_total"] += 1
    
    if server_id not in counts["server_totals"]:
        counts["server_totals"][server_id] = 0
    counts["server_totals"][server_id] += 1
    
    if user_id not in counts["global_users"]:
        counts["global_users"][user_id] = {"name": username, "count": 0}
    counts["global_users"][user_id]["count"] += 1
    counts["global_users"][user_id]["name"] = username
    
    if server_id not in counts["server_users"]:
        counts["server_users"][server_id] = {}
    if user_id not in counts["server_users"][server_id]:
        counts["server_users"][server_id][user_id] = {"name": username, "count": 0}
    counts["server_users"][server_id][user_id]["count"] += 1
    counts["server_users"][server_id][user_id]["name"] = username
    
    save_counts()
    
    add_user_cuss(user_id, username, server_id)

def check_for_cuss(message_content: str) -> bool:
    content_lower = message_content.lower()
    for word in cuss_words:
        if word.lower() in content_lower:
            return True
    return False

def get_random_response() -> str:
    if responses:
        return random.choice(responses)
    return "Watch your language!"

def get_top_users(user_dict: dict, limit: int = 10) -> list:
    sorted_users = sorted(user_dict.items(), key=lambda x: x[1]["count"], reverse=True)
    return sorted_users[:limit]

BOT_OWNER_ID = 971232904296402944

@client.event
async def on_ready():
    global cuss_words, responses
    
    print(f'Logged in as {client.user}!')
    
    cuss_words = load_json("words.json")
    responses = load_json("responses.json")
    load_counts()
    load_users()
    load_server_config()
    
    print(f'Loaded {len(cuss_words)} cuss words')
    print(f'Loaded {len(responses)} responses')
    print(f'Loaded {len(users)} users')
    print(f'Global cuss count: {counts["global_total"]}')
    
    print('Syncing slash commands...')
    await tree.sync()
    print('Slash commands synced!')
    print('Cussbot is ready!')

@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content == "!?&restart" and message.author.id == BOT_OWNER_ID:
        await message.channel.send("Rebooting...")
        print(f"\n[REBOOT] Reboot requested by {message.author}")
        await client.close()
        return
    
    if message.guild and check_for_cuss(message.content):
        server_id = str(message.guild.id)
        user_id = str(message.author.id)
        username = message.author.display_name
        
        add_cuss(server_id, user_id, username)
        
        settings = get_server_settings(server_id)
        
        if not settings["responses_enabled"]:
            return
        
        if check_cooldown(user_id):
            return
        
        response = get_random_response()
        
        if settings["response_channel"]:
            channel = client.get_channel(int(settings["response_channel"]))
            if channel:
                await channel.send(f"{message.author.mention}: {response}")
        else:
            await message.reply(response)

@tree.command(name="cussconfig", description="Configure cussbot settings for this server (Admin only)")
@app_commands.describe(
    action="What to configure",
    channel="Channel for responses (for set_channel)",
    enabled="Enable or disable responses (for toggle_responses)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Set response channel", value="set_channel"),
    app_commands.Choice(name="Use same channel (default)", value="same_channel"),
    app_commands.Choice(name="Enable responses", value="enable"),
    app_commands.Choice(name="Disable responses", value="disable"),
    app_commands.Choice(name="View settings", value="status"),
])
async def cussconfig(
    interaction: discord.Interaction,
    action: str,
    channel: discord.TextChannel = None
):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permission to use this command.", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    settings = get_server_settings(server_id)
    
    if action == "set_channel":
        if not channel:
            await interaction.response.send_message("Please specify a channel.", ephemeral=True)
            return
        settings["response_channel"] = str(channel.id)
        save_server_config()
        await interaction.response.send_message(f"Responses will now be sent to {channel.mention}", ephemeral=True)
    
    elif action == "same_channel":
        settings["response_channel"] = None
        save_server_config()
        await interaction.response.send_message("Responses will now be sent in the same channel as the cusser.", ephemeral=True)
    
    elif action == "enable":
        settings["responses_enabled"] = True
        save_server_config()
        await interaction.response.send_message("Responses are now enabled.", ephemeral=True)
    
    elif action == "disable":
        settings["responses_enabled"] = False
        save_server_config()
        await interaction.response.send_message("Responses are now disabled. Cusses will still be recorded.", ephemeral=True)
    
    elif action == "status":
        channel_setting = f"<#{settings['response_channel']}>" if settings["response_channel"] else "Same as cusser"
        responses_setting = "Enabled" if settings["responses_enabled"] else "Disabled"
        
        embed = discord.Embed(title="Cussbot Settings")
        embed.add_field(name="Response Channel", value=channel_setting, inline=True)
        embed.add_field(name="Responses", value=responses_setting, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="serverboard", description="Top 10 cussers in this server")
async def serverboard(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    server_users = counts["server_users"].get(server_id, {})
    
    top_users = get_top_users(server_users, 10)
    
    if not top_users:
        await interaction.response.send_message("No cusses recorded in this server yet!", ephemeral=True)
        return
    
    embed = discord.Embed(title=f"Top 10 Cussers - {interaction.guild.name}")
    
    leaderboard = ""
    for i, (user_id, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard += f"{medal} **{data['name']}** - {data['count']} cusses\n"
    
    embed.description = leaderboard
    await interaction.response.send_message(embed=embed)

@tree.command(name="globalboard", description="Top 10 cussers globally")
async def globalboard(interaction: discord.Interaction):
    top_users = get_top_users(counts["global_users"], 10)
    
    if not top_users:
        await interaction.response.send_message("No cusses recorded yet!", ephemeral=True)
        return
    
    embed = discord.Embed(title="Top 10 Global Cussers")
    
    leaderboard = ""
    for i, (user_id, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard += f"{medal} **{data['name']}** - {data['count']} cusses\n"
    
    embed.description = leaderboard
    await interaction.response.send_message(embed=embed)

@tree.command(name="cusstotal", description="Total cuss counts for this server and globally")
async def cusstotal(interaction: discord.Interaction):
    global_total = counts["global_total"]
    
    server_total = 0
    if interaction.guild:
        server_id = str(interaction.guild.id)
        server_total = counts["server_totals"].get(server_id, 0)
    
    embed = discord.Embed(title="Cuss Counter Totals")
    
    if interaction.guild:
        embed.add_field(name="This Server", value=f"**{server_total}** cusses", inline=True)
    
    embed.add_field(name="Global", value=f"**{global_total}** cusses", inline=True)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="restart", description="Restart the bot (Owner only)")
async def restart(interaction: discord.Interaction):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message("Rebooting bot...", ephemeral=True)
    print(f"\n[REBOOT] Reboot requested by {interaction.user}")
    await client.close()

if __name__ == "__main__":
    try:
        with open("token.txt", "r") as f:
            TOKEN = f.read().strip()
        
        if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
            print("Please add your Discord bot token to token.txt!")
            exit(1)
        
        print("Token loaded successfully!")
        print("Starting Cussbot...")
        client.run(TOKEN)
        
    except FileNotFoundError:
        print("token.txt not found!")
        print("Create a token.txt file with your bot token.")
        exit(1)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

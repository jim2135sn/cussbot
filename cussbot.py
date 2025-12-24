import discord
from discord import app_commands
import json
import random
import os

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found!")
        return []

cuss_words = []
responses = []

COUNTS_FILE = "counts.json"
counts = {
    "global_total": 0,
    "server_totals": {},
    "global_users": {},
    "server_users": {}
}

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
    
    print(f'Loaded {len(cuss_words)} cuss words')
    print(f'Loaded {len(responses)} responses')
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
        
        response = get_random_response()
        await message.reply(response)

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

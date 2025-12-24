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
    "global": 0,
    "servers": {}
}

def load_counts():
    global counts
    try:
        with open(COUNTS_FILE, 'r') as f:
            counts = json.load(f)
    except FileNotFoundError:
        pass

def save_counts():
    with open(COUNTS_FILE, 'w') as f:
        json.dump(counts, f)

def add_cuss(server_id: str):
    """Add a cuss to both global and server counter"""
    counts["global"] += 1
    if server_id not in counts["servers"]:
        counts["servers"][server_id] = 0
    counts["servers"][server_id] += 1
    save_counts()

def check_for_cuss(message_content: str) -> bool:
    """Check if message contains any cuss word"""
    content_lower = message_content.lower()
    for word in cuss_words:
        if word.lower() in content_lower:
            return True
    return False

def get_random_response() -> str:
    """Get a random response"""
    if responses:
        return random.choice(responses)
    return "Watch your language!"

# my id hehe
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
    print(f'Global cuss count: {counts["global"]}')

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
    
    if check_for_cuss(message.content):
        server_id = str(message.guild.id) if message.guild else "dm"
        add_cuss(server_id)
        
        response = get_random_response()
        await message.reply(response)

@tree.command(name="cussstats", description="See the cuss counter stats")
async def cussstats(interaction: discord.Interaction):
    server_id = str(interaction.guild.id) if interaction.guild else "dm"
    server_count = counts["servers"].get(server_id, 0)
    global_count = counts["global"]
    
    embed = discord.Embed(title="Cuss Counter Stats")
    embed.add_field(name="This Server", value=str(server_count), inline=True)
    embed.add_field(name="Global", value=str(global_count), inline=True)
    
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
        
        if not TOKEN or TOKEN == "replacethiseventually":
            print("u forgor your token numnut")
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

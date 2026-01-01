import discord
from discord import app_commands
import json
import random
import os
import time
import re
import difflib

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

AVAILABLE_TAGS = ["general", "sexual", "lgbtq", "racial", "religious", "shock"]

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
            "responses_enabled": True,
            "delete_messages": False,
            "delete_severity": 3,
            "scoreboard_enabled": True,
            "close_match_detection": False,
            "filtered_tags": []
        }
    settings = server_config[server_id]
    if "delete_messages" not in settings:
        settings["delete_messages"] = False
    if "delete_severity" not in settings:
        settings["delete_severity"] = 3
    if "scoreboard_enabled" not in settings:
        settings["scoreboard_enabled"] = True
    if "close_match_detection" not in settings:
        settings["close_match_detection"] = False
    if "filtered_tags" not in settings:
        settings["filtered_tags"] = []
    return settings

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

def pattern_to_regex(pattern: str) -> str:
    escaped = ""
    for char in pattern:
        if char == '*':
            escaped += ".*"
        elif char in r'\^$.|?+()[]{}':
            escaped += '\\' + char
        else:
            escaped += char
    return escaped

def check_exception(word: str, exceptions: list) -> bool:
    word_lower = word.lower()
    for exc in exceptions:
        exc_pattern = pattern_to_regex(exc.lower())
        if re.fullmatch(exc_pattern, word_lower):
            return True
    return False

def check_for_cuss(message_content: str, settings: dict) -> dict:
    if not isinstance(message_content, str):
        return {"matched": False}
    content_lower = message_content.lower()
    words_in_message = re.findall(r'\b[\w\'-]+\b', content_lower)
    
    filtered_tags = settings.get("filtered_tags", [])
    close_match = settings.get("close_match_detection", False)
    
    for word_entry in cuss_words:
        if not isinstance(word_entry, dict):
            continue
        word_id = word_entry.get("id", "")
        match_raw = word_entry.get("match", "")
        if not isinstance(match_raw, str):
            continue
        match_patterns = match_raw.split("|")
        tags = word_entry.get("tags", [])
        severity = word_entry.get("severity", 1)
        exceptions = word_entry.get("exceptions", [])
        
        if filtered_tags and not any(tag in filtered_tags for tag in tags):
            continue
        
        for pattern in match_patterns:
            pattern = pattern.strip()
            if not pattern:
                continue
            
            if '*' in pattern:
                regex_pattern = pattern_to_regex(pattern)
                for msg_word in words_in_message:
                    if re.fullmatch(regex_pattern, msg_word):
                        if not check_exception(msg_word, exceptions):
                            return {"matched": True, "severity": severity, "tags": tags, "id": word_id, "word": msg_word}
                if re.search(regex_pattern, content_lower):
                    matched_text = re.search(regex_pattern, content_lower).group()
                    if not check_exception(matched_text, exceptions):
                        return {"matched": True, "severity": severity, "tags": tags, "id": word_id, "word": matched_text}
            else:
                if ' ' in pattern:
                    if pattern in content_lower:
                        if not check_exception(pattern, exceptions):
                            return {"matched": True, "severity": severity, "tags": tags, "id": word_id, "word": pattern}
                else:
                    for msg_word in words_in_message:
                        if msg_word == pattern:
                            if not check_exception(msg_word, exceptions):
                                return {"matched": True, "severity": severity, "tags": tags, "id": word_id, "word": msg_word}
        
        if close_match:
            for pattern in match_patterns:
                pattern = pattern.strip()
                if not pattern or '*' in pattern or ' ' in pattern:
                    continue
                for msg_word in words_in_message:
                    similarity = difflib.SequenceMatcher(None, msg_word, pattern).ratio()
                    if similarity >= 0.8 and msg_word != pattern:
                        if not check_exception(msg_word, exceptions):
                            return {"matched": True, "severity": severity, "tags": tags, "id": word_id, "word": msg_word, "close_match": True}
    
    return {"matched": False}

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
    
    if message.guild:
        server_id = str(message.guild.id)
        user_id = str(message.author.id)
        username = message.author.display_name
        
        settings = get_server_settings(server_id)
        
        result = check_for_cuss(message.content, settings)
        
        if result["matched"]:
            severity = result["severity"]
            
            if settings["scoreboard_enabled"]:
                add_cuss(server_id, user_id, username)
            
            if settings["delete_messages"] and severity >= settings["delete_severity"]:
                try:
                    await message.delete()
                except discord.errors.Forbidden:
                    pass
            
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
                try:
                    await message.reply(response)
                except discord.errors.NotFound:
                    pass

@tree.command(name="cusshelp", description="Show help for all Cussbot commands")
async def cusshelp(interaction: discord.Interaction):
    embed = discord.Embed(title="Cussbot Help", description="All available commands")
    
    embed.add_field(
        name="/cusshelp",
        value="Shows this help message",
        inline=False
    )
    embed.add_field(
        name="/serverboard",
        value="Show top 10 cussers in this server",
        inline=False
    )
    embed.add_field(
        name="/globalboard",
        value="Show top 10 cussers globally",
        inline=False
    )
    embed.add_field(
        name="/cusstotal",
        value="Show total cuss counts for this server and globally",
        inline=False
    )
    embed.add_field(
        name="/cussconfig (Admin)",
        value="Configure response channel and enable/disable responses",
        inline=False
    )
    embed.add_field(
        name="/cussdelete (Admin)",
        value="Toggle message deletion and set severity threshold (1-4)",
        inline=False
    )
    embed.add_field(
        name="/cussscoreboard (Admin)",
        value="Toggle scoreboard tracking for this server",
        inline=False
    )
    embed.add_field(
        name="/cussmatch (Admin)",
        value="Toggle close match detection for misspellings",
        inline=False
    )
    embed.add_field(
        name="/cusstags (Admin)",
        value="Configure which tags to filter (general, sexual, lgbtq, racial, religious, shock)",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="cussdelete", description="Configure message deletion for swears (Admin only)")
@app_commands.describe(
    action="Enable, disable, or view status",
    severity="Minimum severity to delete (1=Low, 2=Medium, 3=High, 4=Extreme)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Enable deletion", value="enable"),
    app_commands.Choice(name="Disable deletion", value="disable"),
    app_commands.Choice(name="View status", value="status"),
])
@app_commands.choices(severity=[
    app_commands.Choice(name="1 - Low (bloody, ass, boob)", value=1),
    app_commands.Choice(name="2 - Medium (anal, bullshit, apeshit)", value=2),
    app_commands.Choice(name="3 - High (bitch, bastard, slurs)", value=3),
    app_commands.Choice(name="4 - Extreme (2girls1cup, 1man1jar, barely legal)", value=4),
])
async def cussdelete(
    interaction: discord.Interaction,
    action: str,
    severity: int = None
):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permission to use this command.", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    settings = get_server_settings(server_id)
    
    if action == "enable":
        settings["delete_messages"] = True
        if severity is not None:
            settings["delete_severity"] = severity
        save_server_config()
        await interaction.response.send_message(f"Message deletion enabled. Severity threshold: {settings['delete_severity']}", ephemeral=True)
    
    elif action == "disable":
        settings["delete_messages"] = False
        save_server_config()
        await interaction.response.send_message("Message deletion disabled.", ephemeral=True)
    
    elif action == "status":
        status = "Enabled" if settings["delete_messages"] else "Disabled"
        embed = discord.Embed(title="Message Deletion Settings")
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Severity Threshold", value=str(settings["delete_severity"]), inline=True)
        embed.add_field(
            name="Severity Guide",
            value="1 = Low (bloody, ass)\n2 = Medium (bullshit)\n3 = High (bitch, slurs)\n4 = Extreme (shock)",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="cussscoreboard", description="Toggle scoreboard tracking (Admin only)")
@app_commands.describe(action="Enable or disable scoreboard tracking")
@app_commands.choices(action=[
    app_commands.Choice(name="Enable scoreboard", value="enable"),
    app_commands.Choice(name="Disable scoreboard", value="disable"),
    app_commands.Choice(name="View status", value="status"),
])
async def cussscoreboard(interaction: discord.Interaction, action: str):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permission to use this command.", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    settings = get_server_settings(server_id)
    
    if action == "enable":
        settings["scoreboard_enabled"] = True
        save_server_config()
        await interaction.response.send_message("Scoreboard tracking enabled. Cusses will be recorded.", ephemeral=True)
    
    elif action == "disable":
        settings["scoreboard_enabled"] = False
        save_server_config()
        await interaction.response.send_message("Scoreboard tracking disabled. Cusses will not be recorded.", ephemeral=True)
    
    elif action == "status":
        status = "Enabled" if settings["scoreboard_enabled"] else "Disabled"
        await interaction.response.send_message(f"Scoreboard tracking: {status}", ephemeral=True)

@tree.command(name="cussmatch", description="Toggle close match detection (Admin only)")
@app_commands.describe(action="Enable or disable detection of misspellings and close matches")
@app_commands.choices(action=[
    app_commands.Choice(name="Enable close match detection", value="enable"),
    app_commands.Choice(name="Disable close match detection", value="disable"),
    app_commands.Choice(name="View status", value="status"),
])
async def cussmatch(interaction: discord.Interaction, action: str):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permission to use this command.", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    settings = get_server_settings(server_id)
    
    if action == "enable":
        settings["close_match_detection"] = True
        save_server_config()
        await interaction.response.send_message("Close match detection enabled. Misspellings will be detected.", ephemeral=True)
    
    elif action == "disable":
        settings["close_match_detection"] = False
        save_server_config()
        await interaction.response.send_message("Close match detection disabled.", ephemeral=True)
    
    elif action == "status":
        status = "Enabled" if settings["close_match_detection"] else "Disabled"
        await interaction.response.send_message(f"Close match detection: {status}", ephemeral=True)

@tree.command(name="cusstags", description="Configure which tags to filter (Admin only)")
@app_commands.describe(
    action="What to do with tags",
    tag="Tag to add or remove"
)
@app_commands.choices(action=[
    app_commands.Choice(name="Add tag to filter", value="add"),
    app_commands.Choice(name="Remove tag from filter", value="remove"),
    app_commands.Choice(name="Clear all (filter everything)", value="clear"),
    app_commands.Choice(name="View current tags", value="status"),
])
@app_commands.choices(tag=[
    app_commands.Choice(name="general - General swear words", value="general"),
    app_commands.Choice(name="sexual - Sexual content", value="sexual"),
    app_commands.Choice(name="lgbtq - LGBTQ slurs", value="lgbtq"),
    app_commands.Choice(name="racial - Racial slurs", value="racial"),
    app_commands.Choice(name="religious - Religious terms", value="religious"),
    app_commands.Choice(name="shock - Shock content", value="shock"),
])
async def cusstags(
    interaction: discord.Interaction,
    action: str,
    tag: str = None
):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in servers!", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need administrator permission to use this command.", ephemeral=True)
        return
    
    server_id = str(interaction.guild.id)
    settings = get_server_settings(server_id)
    
    if action == "add":
        if not tag:
            await interaction.response.send_message("Please specify a tag to add.", ephemeral=True)
            return
        if tag not in settings["filtered_tags"]:
            settings["filtered_tags"].append(tag)
            save_server_config()
        await interaction.response.send_message(f"Now filtering: {', '.join(settings['filtered_tags']) if settings['filtered_tags'] else 'All tags (default)'}", ephemeral=True)
    
    elif action == "remove":
        if not tag:
            await interaction.response.send_message("Please specify a tag to remove.", ephemeral=True)
            return
        if tag in settings["filtered_tags"]:
            settings["filtered_tags"].remove(tag)
            save_server_config()
        await interaction.response.send_message(f"Now filtering: {', '.join(settings['filtered_tags']) if settings['filtered_tags'] else 'All tags (default)'}", ephemeral=True)
    
    elif action == "clear":
        settings["filtered_tags"] = []
        save_server_config()
        await interaction.response.send_message("Tag filter cleared. Now filtering all tags (default behavior).", ephemeral=True)
    
    elif action == "status":
        if settings["filtered_tags"]:
            tags_list = ", ".join(settings["filtered_tags"])
            await interaction.response.send_message(f"Currently filtering only: {tags_list}\n\nAvailable tags: general, sexual, lgbtq, racial, religious, shock", ephemeral=True)
        else:
            await interaction.response.send_message("Currently filtering: All tags (default)\n\nAvailable tags: general, sexual, lgbtq, racial, religious, shock", ephemeral=True)

@tree.command(name="cussconfig", description="Configure cussbot settings for this server (Admin only)")
@app_commands.describe(
    action="What to configure",
    channel="Channel for responses (for set_channel)"
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
        delete_setting = "Enabled" if settings["delete_messages"] else "Disabled"
        scoreboard_setting = "Enabled" if settings["scoreboard_enabled"] else "Disabled"
        close_match_setting = "Enabled" if settings["close_match_detection"] else "Disabled"
        tags_setting = ", ".join(settings["filtered_tags"]) if settings["filtered_tags"] else "All"
        
        embed = discord.Embed(title="Cussbot Settings")
        embed.add_field(name="Response Channel", value=channel_setting, inline=True)
        embed.add_field(name="Responses", value=responses_setting, inline=True)
        embed.add_field(name="Delete Messages", value=f"{delete_setting} (severity {settings['delete_severity']}+)", inline=True)
        embed.add_field(name="Scoreboard", value=scoreboard_setting, inline=True)
        embed.add_field(name="Close Match", value=close_match_setting, inline=True)
        embed.add_field(name="Filtered Tags", value=tags_setting, inline=True)
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
        leaderboard += f"{i}. **{data['name']}** - {data['count']} cusses\n"
    
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
        leaderboard += f"{i}. **{data['name']}** - {data['count']} cusses\n"
    
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

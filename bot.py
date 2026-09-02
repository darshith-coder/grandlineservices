import discord
from discord.ext import commands
import json
import datetime
import os
from flask import Flask
import threading

# =============================================
# BOT CONFIGURATION
# =============================================
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found!")
    exit(1)

intents = discord.Intents.default()  # We are using default intents now; no need for "all" for slash commands
bot = commands.Bot(command_prefix='!', intents=intents)

# =============================================
# FLASK SERVER (KEEPS RENDER ALIVE)
# =============================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# =============================================
# VOUCH SYSTEM (Keep your VouchSystem class here)
# =============================================
class VouchSystem:
    def __init__(self):
        self.vouches = {}
        self.users = {}
        self.load_data()
    
    def load_data(self):
        try:
            with open('vouches.json', 'r') as f:
                data = json.load(f)
                self.vouches = data.get('vouches', {})
                self.users = data.get('users', {})
        except FileNotFoundError:
            self.vouches = {}
            self.users = {}
            self.save_data()
    
    def save_data(self):
        with open('vouches.json', 'w') as f:
            json.dump({'vouches': self.vouches, 'users': self.users}, f, indent=4)
    
    def add_vouch(self, target_user_id, vouched_by_id, service, quality, professionalism, communication, comment):
        vouch_data = {
            'target_user_id': str(target_user_id),
            'vouched_by_id': str(vouched_by_id),
            'service': service,
            'ratings': {'quality': quality, 'professionalism': professionalism, 'communication': communication},
            'comment': comment,
            'timestamp': datetime.datetime.now().isoformat(),
            'average_rating': round((quality + professionalism + communication) / 3, 1)
        }
        
        if str(target_user_id) not in self.vouches:
            self.vouches[str(target_user_id)] = []
        
        self.vouches[str(target_user_id)].append(vouch_data)
        self.update_user_stats(target_user_id)
        self.save_data()
        return vouch_data
    
    def update_user_stats(self, user_id):
        user_vouches = self.vouches.get(str(user_id), [])
        if user_vouches:
            total_ratings = sum(v['average_rating'] for v in user_vouches)
            avg_rating = total_ratings / len(user_vouches)
            self.users[str(user_id)] = {'total_vouches': len(user_vouches), 'average_rating': round(avg_rating, 1), 'last_vouch': user_vouches[-1]['timestamp']}
        else:
            self.users[str(user_id)] = {'total_vouches': 0, 'average_rating': 0.0, 'last_vouch': None}
    
    def get_user_stats(self, user_id):
        return self.users.get(str(user_id), {'total_vouches': 0, 'average_rating': 0.0, 'last_vouch': None})
    
    def get_vouches(self, user_id, limit=10):
        return self.vouches.get(str(user_id), [])[-limit:][::-1]

vouch_system = VouchSystem()

# =============================================
# BOT EVENTS
# =============================================
@bot.event
async def on_ready():
    print(f"✅ Bot is online!")
    print(f"🌊 Bot Name: {bot.user.name}")
    print(f"📊 Guilds: {len(bot.guilds)}")
    
    # CRITICAL: Sync Slash Commands
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# =============================================
# SLASH COMMANDS (These work 100% without Message Intent)
# =============================================

# 1. ADD ROLE COMMAND
@bot.tree.command(name="addrole", description="Add a role to a member")
async def add_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if interaction.user.top_role <= role:
        await interaction.response.send_message("❌ You cannot give a role that is equal to or higher than your own!", ephemeral=True)
        return
    
    if interaction.guild.me.top_role <= role:
        await interaction.response.send_message("❌ I cannot assign that role because it is higher than my own!", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Successfully added {role.mention} to {member.mention}!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I do not have permission to manage roles. Please check my permissions!", ephemeral=True)

# 2. VOUCH COMMAND (Slash)
@bot.tree.command(name="vouch", description="Vouch for a user")
async def vouch_slash(interaction: discord.Interaction, member: discord.Member, service: str, quality: int, professionalism: int, communication: int, comment: str):
    if interaction.user.id == member.id:
        await interaction.response.send_message("🏴‍☠️ You cannot vouch for yourself!", ephemeral=True)
        return
    
    if not all(1 <= rating <= 5 for rating in [quality, professionalism, communication]):
        await interaction.response.send_message("📊 Ratings must be between 1 and 5!", ephemeral=True)
        return

    try:
        vouch_data = vouch_system.add_vouch(member.id, interaction.user.id, service, quality, professionalism, communication, comment)
        
        embed = discord.Embed(title="🏴‍☠️ Grand Line Vouch", description=f"**{interaction.user.display_name}** vouched for **{member.display_name}**", color=discord.Color.gold())
        embed.add_field(name="📊 Service", value=service, inline=True)
        embed.add_field(name="⭐ Average Rating", value=f"{vouch_data['average_rating']}/5.0", inline=True)
        embed.add_field(name="📈 Ratings", value=f"Quality: {quality}/5\nProfessionalism: {professionalism}/5\nCommunication: {communication}/5", inline=False)
        embed.add_field(name="💭 Review", value=f"*\"{comment}\"*", inline=False)
        embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
        embed.timestamp = datetime.datetime.now()
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message("🌊 Failed to register vouch. Please try again!", ephemeral=True)
        print(f"Vouch error: {e}")

# 3. PROFILE COMMAND (Slash)
@bot.tree.command(name="profile", description="View a member's vouch profile")
async def profile_slash(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    stats = vouch_system.get_user_stats(target.id)
    vouches = vouch_system.get_vouches(target.id, limit=3)
    
    embed = discord.Embed(title=f"🏴‍☠️ {target.display_name}'s Grand Line Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="📊 Statistics", value=f"**Total Vouches:** {stats['total_vouches']}\n**Average Rating:** {stats['average_rating']}/5.0 ⭐", inline=False)
    
    if vouches:
        recent = "\n".join([f"• **{v['service']}** - {v['average_rating']}⭐ by <@{v['vouched_by_id']}>" for v in vouches[:3]])
        embed.add_field(name="📝 Recent Vouches", value=recent, inline=False)
    else:
        embed.add_field(name="📝 Recent Vouches", value="*No vouches yet*", inline=False)
    
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await interaction.response.send_message(embed=embed)

# =============================================
# RUN THE BOT
# =============================================
if __name__ == "__main__":
    def run_bot():
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("❌ ERROR: Invalid Discord token!")
        except Exception as e:
            print(f"❌ ERROR: {e}")

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    print("🚀 Starting Flask server for Render port check...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

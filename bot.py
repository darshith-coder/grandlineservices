import discord
from discord.ext import commands
import json
import datetime
import random
import os
from typing import Optional

# =============================================
# BOT CONFIGURATION FOR RENDER
# =============================================

# Get token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables!")
    print("⚠️ Please add DISCORD_TOKEN in Render Environment Variables")
    exit(1)

# Get channel IDs from environment (optional)
VOUCH_CHANNEL_ID = int(os.getenv('VOUCH_CHANNEL', 0))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL', 0))

print(f"🤖 Starting Grand Line Services Bot...")
print(f"📌 Bot Token: {'*' * 10}✅")
print(f"📌 Vouch Channel ID: {VOUCH_CHANNEL_ID if VOUCH_CHANNEL_ID else 'Not set'}")
print(f"📌 Log Channel ID: {LOG_CHANNEL_ID if LOG_CHANNEL_ID else 'Not set'}")

# Bot intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# =============================================
# VOUCH SYSTEM
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
        vouch_id = f"{target_user_id}_{int(datetime.datetime.now().timestamp())}"
        
        vouch_data = {
            'vouch_id': vouch_id,
            'target_user_id': str(target_user_id),
            'vouched_by_id': str(vouched_by_id),
            'service': service,
            'ratings': {
                'quality': quality,
                'professionalism': professionalism,
                'communication': communication
            },
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
            self.users[str(user_id)] = {
                'total_vouches': len(user_vouches),
                'average_rating': round(avg_rating, 1),
                'last_vouch': user_vouches[-1]['timestamp']
            }
        else:
            self.users[str(user_id)] = {
                'total_vouches': 0,
                'average_rating': 0.0,
                'last_vouch': None
            }
    
    def get_user_stats(self, user_id):
        return self.users.get(str(user_id), {
            'total_vouches': 0,
            'average_rating': 0.0,
            'last_vouch': None
        })
    
    def get_vouches(self, user_id, limit=10):
        user_vouches = self.vouches.get(str(user_id), [])
        return user_vouches[-limit:][::-1]

vouch_system = VouchSystem()

# =============================================
# BOT EVENTS
# =============================================

@bot.event
async def on_ready():
    print(f"✅ Bot is online!")
    print(f"🌊 Bot Name: {bot.user.name}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"📊 Guilds: {len(bot.guilds)}")
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="the Grand Line | !help"
    ))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🌊 You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("🌊 Missing arguments! Use `!help` for proper format.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("🌊 Invalid argument! Use `!help` for proper format.")
    else:
        await ctx.send(f"🌊 An error occurred! {str(error)}")
        print(f"Error: {error}")

# =============================================
# COMMANDS
# =============================================

@bot.command(name='vouch', aliases=['v'])
async def vouch_command(ctx, member: discord.Member, service: str, quality: int, professionalism: int, communication: int, *, comment: str):
    """Vouch for someone - !vouch @user service quality prof comm comment"""
    
    if ctx.author.id == member.id:
        await ctx.send("🏴‍☠️ You cannot vouch for yourself, Captain!")
        return
    
    if not all(1 <= rating <= 5 for rating in [quality, professionalism, communication]):
        await ctx.send("📊 Ratings must be between 1 and 5!")
        return
    
    try:
        vouch_data = vouch_system.add_vouch(
            member.id, ctx.author.id, service, quality, professionalism, communication, comment
        )
        
        # Create beautiful embed
        embed = discord.Embed(
            title="🏴‍☠️ Grand Line Vouch",
            description=f"**{ctx.author.display_name}** vouched for **{member.display_name}**",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📊 Service",
            value=service,
            inline=True
        )
        embed.add_field(
            name="⭐ Average Rating",
            value=f"{vouch_data['average_rating']}/5.0",
            inline=True
        )
        embed.add_field(
            name="📈 Ratings",
            value=(
                f"Quality: {quality}/5\n"
                f"Professionalism: {professionalism}/5\n"
                f"Communication: {communication}/5"
            ),
            inline=False
        )
        embed.add_field(
            name="💭 Review",
            value=f"*\"{comment}\"*",
            inline=False
        )
        embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
        # Check milestone
        stats = vouch_system.get_user_stats(member.id)
        if stats['total_vouches'] in [1, 5, 10, 25, 50, 100]:
            milestone_embed = discord.Embed(
                title="🎉 Milestone Achieved!",
                description=f"{member.mention} has received {stats['total_vouches']} vouches on the Grand Line!",
                color=discord.Color.purple()
            )
            await ctx.send(embed=milestone_embed)
        
    except Exception as e:
        await ctx.send("🌊 Failed to register vouch. Please try again!")
        print(f"Vouch error: {e}")

@bot.command(name='profile', aliases=['p'])
async def profile_command(ctx, member: Optional[discord.Member] = None):
    """View a member's vouch profile"""
    target = member or ctx.author
    stats = vouch_system.get_user_stats(target.id)
    vouches = vouch_system.get_vouches(target.id, limit=3)
    
    embed = discord.Embed(
        title=f"🏴‍☠️ {target.display_name}'s Grand Line Profile",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(
        name="📊 Statistics",
        value=(
            f"**Total Vouches:** {stats['total_vouches']}\n"
            f"**Average Rating:** {stats['average_rating']}/5.0 ⭐"
        ),
        inline=False
    )
    
    if vouches:
        recent = "\n".join([
            f"• **{v['service']}** - {v['average_rating']}⭐ by <@{v['vouched_by_id']}>"
            for v in vouches[:3]
        ])
        embed.add_field(name="📝 Recent Vouches", value=recent, inline=False)
    else:
        embed.add_field(name="📝 Recent Vouches", value="*No vouches yet*", inline=False)
    
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await ctx.send(embed=embed)

@bot.command(name='vouches', aliases=['vlist', 'vl'])
async def vouches_command(ctx, member: Optional[discord.Member] = None, limit: int = 5):
    """List recent vouches for a member"""
    target = member or ctx.author
    vouches = vouch_system.get_vouches(target.id, limit=min(limit, 20))
    
    if not vouches:
        await ctx.send(f"🌊 {target.mention} has no vouches yet!")
        return
    
    embed = discord.Embed(
        title=f"📋 {target.display_name}'s Vouch History",
        color=discord.Color.purple()
    )
    
    for i, vouch in enumerate(vouches[:5], 1):
        vouch_time = datetime.datetime.fromisoformat(vouch['timestamp']).strftime("%Y-%m-%d")
        embed.add_field(
            name=f"#{i} - {vouch['service']} ({vouch['average_rating']}⭐)",
            value=(
                f"**By:** <@{vouch['vouched_by_id']}>\n"
                f"**Ratings:** Q:{vouch['ratings']['quality']} P:{vouch['ratings']['professionalism']} C:{vouch['ratings']['communication']}\n"
                f"**Comment:** {vouch['comment'][:100]}{'...' if len(vouch['comment']) > 100 else ''}\n"
                f"**Date:** {vouch_time}"
            ),
            inline=False
        )
    
    embed.set_footer(text=f"Showing {len(vouches[:5])} vouches | Grand Line Services")
    await ctx.send(embed=embed)

@bot.command(name='stats')
async def stats_command(ctx):
    """View server-wide vouch statistics"""
    total_vouches = sum(len(v) for v in vouch_system.vouches.values())
    total_members = len(vouch_system.users)
    
    top_users = sorted(
        vouch_system.users.items(),
        key=lambda x: x[1]['total_vouches'],
        reverse=True
    )[:5]
    
    embed = discord.Embed(
        title="📊 Grand Line Server Statistics",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📈 Overall Stats",
        value=(
            f"**Total Vouches:** {total_vouches}\n"
            f"**Members Vouched:** {total_members}\n"
            f"**Average Rating:** {round(sum(u['average_rating'] for u in vouch_system.users.values()) / max(1, len(vouch_system.users)), 1)}/5.0"
        ),
        inline=False
    )
    
    if top_users:
        top_list = "\n".join([
            f"**{i+1}.** <@{user_id}> - {data['total_vouches']} vouches (⭐{data['average_rating']})"
            for i, (user_id, data) in enumerate(top_users)
        ])
        embed.add_field(name="🏆 Top Vouched Members", value=top_list, inline=False)
    
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await ctx.send(embed=embed)

@bot.command(name='top', aliases=['leaderboard', 'lb'])
async def top_command(ctx):
    """Show the top vouched members"""
    top_users = sorted(
        vouch_system.users.items(),
        key=lambda x: x[1]['total_vouches'],
        reverse=True
    )[:10]
    
    if not top_users:
        await ctx.send("🌊 No vouches found on the Grand Line yet!")
        return
    
    embed = discord.Embed(
        title="🏆 Grand Line Vouch Leaderboard",
        color=discord.Color.gold()
    )
    
    leaderboard = ""
    for i, (user_id, data) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
        leaderboard += f"{medal} <@{user_id}> - **{data['total_vouches']}** vouches (⭐{data['average_rating']})\n"
    
    embed.add_field(name="Top Members", value=leaderboard, inline=False)
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await ctx.send(embed=embed)

@bot.command(name='help', aliases=['commands', 'h'])
async def help_command(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🏴‍☠️ Grand Line Services - Vouch Bot",
        description="*Your trusted companion for vouching on the Grand Line!*",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="⚓ Commands",
        value=(
            "`!vouch @user service quality prof comm comment` - **Vouch for someone**\n"
            "`!profile @user` - **View someone's vouch profile**\n"
            "`!vouches @user` - **See recent vouches**\n"
            "`!stats` - **View server statistics**\n"
            "`!top` - **Top vouched members**\n"
            "`!help` - **Show this message**"
        ),
        inline=False
    )
    embed.add_field(
        name="📝 Example",
        value="`!vouch @Luffy Delivery 5 4 5 \"Super fast service!\"`",
        inline=False
    )
    embed.add_field(
        name="👑 Credits",
        value="**Developed by Darshith Dev**\n*Grand Line Services™*",
        inline=False
    )
    embed.set_footer(text="🌊 Even the illiterate can navigate these waters!")
    await ctx.send(embed=embed)

# =============================================
# RUN THE BOT
# =============================================

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
        print("⚠️ Please check your DISCORD_TOKEN environment variable")
    except Exception as e:
        print(f"❌ ERROR: {e}")

import discord
from discord.ext import commands
import json
import datetime
import random
import asyncio
from typing import Optional

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Vouch data storage
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
    
    def save_data(self):
        with open('vouches.json', 'w') as f:
            json.dump({'vouches': self.vouches, 'users': self.users}, f, indent=4)
    
    def add_vouch(self, target_user_id, vouched_by_id, service, quality, professionalism, communication, comment):
        vouch_id = f"{target_user_id}_{datetime.datetime.now().timestamp()}"
        
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
        return user_vouches[-limit:][::-1]  # Return most recent first

vouch_system = VouchSystem()

# Bot events
@bot.event
async def on_ready():
    print(f"🤖 Grand Line Services Bot is online!")
    print(f"🌊 Bot Name: {bot.user.name}")
    print(f"⚓ Running on Discord")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="the Grand Line | !help"
    ))

# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🌊 **Grand Line Error:** You don't have permission to use this command, sailor!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("🌊 **Grand Line Error:** Missing arguments! Use `!help` to see proper command format.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("🌊 **Grand Line Error:** Invalid argument provided! Check your input and try again.")
    else:
        await ctx.send(f"🌊 **Grand Line Error:** An unexpected error occurred! Report this to Darshith Dev.")
        print(f"Error: {error}")

# Help command - AI-like response
@bot.command(name='help', aliases=['commands', 'h'])
async def help_command(ctx):
    embed = discord.Embed(
        title="🏴‍☠️ Grand Line Services - Vouch Bot",
        description="*" + "Your trusted companion for vouching on the Grand Line!*",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="⚓ Basic Commands (Easy to Use!)",
        value=(
            "`!vouch @user service quality professionalism communication comment` - **Vouch for someone**\n"
            "`!profile @user` - **View someone's vouch profile**\n"
            "`!vouches @user` - **See recent vouches for someone**\n"
            "`!stats` - **View server vouch statistics**\n"
            "`!top` - **Top vouched members on Grand Line**\n"
            "`!help` - **Show this message**"
        ),
        inline=False
    )
    embed.add_field(
        name="📝 Vouch Example",
        value=(
            "`!vouch @Luffy ``delivery`` 5 4 5 ``Was super fast and reliable!``\n"
            "Ratings are from 1-5 (5 being the best)"
        ),
        inline=False
    )
    embed.add_field(
        name="👑 Credits",
        value="**Developed by Darshith Dev**\n*Grand Line Services™*",
        inline=False
    )
    embed.set_footer(text="🌊 Even the illiterate can navigate these waters!")
    await ctx.send(embed=embed)

# Vouch command - AI-like responses
@bot.command(name='vouch', aliases=['v'])
async def vouch_command(ctx, member: discord.Member, service: str, quality: int, professionalism: int, communication: int, *, comment: str):
    """Vouch for a member - !vouch @user service quality prof comm comment"""
    
    # Check if the user is vouching for themselves
    if ctx.author.id == member.id:
        await ctx.send("🏴‍☠️ **Grand Line Error:** You cannot vouch for yourself, Captain!")
        return
    
    # Validate ratings
    if not all(1 <= rating <= 5 for rating in [quality, professionalism, communication]):
        await ctx.send("📊 **Grand Line Error:** Ratings must be between 1 and 5!")
        return
    
    try:
        # Add the vouch
        vouch_data = vouch_system.add_vouch(
            member.id, ctx.author.id, service, quality, professionalism, communication, comment
        )
        
        # AI-like response with personality
        responses = [
            f"⚓ **Vouch Registered!** {ctx.author.mention} has vouched for {member.mention}!\n"
            f"📊 **Service:** {service}\n"
            f"⭐ **Average Rating:** {vouch_data['average_rating']}/5.0\n"
            f"💬 *\"{comment}\"*\n\n"
            f"*The Grand Line acknowledges this transaction!*",
            
            f"🏴‍☠️ **Vouch Confirmed!** Another satisfied crew member!\n"
            f"**Target:** {member.mention}\n"
            f"**Service:** {service}\n"
            f"**Rating:** {vouch_data['average_rating']}⭐\n"
            f"**Review:** {comment}\n\n"
            f"*May the winds of the Grand Line favor you!*",
            
            f"🌊 **Vouch Recorded!** {ctx.author.mention} trusts {member.mention}!\n"
            f"📈 **Quality:** {quality}/5 | **Professionalism:** {professionalism}/5 | **Communication:** {communication}/5\n"
            f"📝 **Feedback:** {comment}\n\n"
            f"*Your reputation on the Grand Line grows!*"
        ]
        
        await ctx.send(random.choice(responses))
        
        # Check for milestone achievements
        stats = vouch_system.get_user_stats(member.id)
        if stats['total_vouches'] in [1, 5, 10, 25, 50, 100]:
            await ctx.send(f"🎉 **Milestone Achieved!** {member.mention} has received {stats['total_vouches']} vouches on the Grand Line!")
            
    except Exception as e:
        await ctx.send("🌊 **Grand Line Error:** Failed to register vouch. Please try again, sailor!")

# Profile command
@bot.command(name='profile', aliases=['p'])
async def profile_command(ctx, member: Optional[discord.Member] = None):
    """View a member's vouch profile"""
    target = member or ctx.author
    stats = vouch_system.get_user_stats(target.id)
    vouches = vouch_system.get_vouches(target.id, limit=5)
    
    embed = discord.Embed(
        title=f"🏴‍☠️ {target.display_name}'s Grand Line Profile",
        color=discord.Color.blue()
    )
    
    # User info
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(
        name="📊 Statistics",
        value=(
            f"**Total Vouches:** {stats['total_vouches']}\n"
            f"**Average Rating:** {stats['average_rating']}/5.0 ⭐\n"
            f"**Last Vouch:** {stats['last_vouch'] or 'Never'}"
        ),
        inline=False
    )
    
    # Recent vouches
    if vouches:
        recent = "\n".join([
            f"• **{v['service']}** - {v['average_rating']}⭐ by <@{v['vouched_by_id']}>"
            for v in vouches[:3]
        ])
        embed.add_field(name="📝 Recent Vouches", value=recent, inline=False)
    else:
        embed.add_field(name="📝 Recent Vouches", value="*No vouches yet on the Grand Line*", inline=False)
    
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await ctx.send(embed=embed)

# Vouches list command
@bot.command(name='vouches', aliases=['vlist', 'vl'])
async def vouches_command(ctx, member: Optional[discord.Member] = None, limit: int = 10):
    """List recent vouches for a member"""
    target = member or ctx.author
    vouches = vouch_system.get_vouches(target.id, limit=min(limit, 20))
    
    if not vouches:
        await ctx.send(f"🌊 {target.mention} has no vouches on the Grand Line yet!")
        return
    
    embed = discord.Embed(
        title=f"📋 {target.display_name}'s Vouch History",
        color=discord.Color.purple()
    )
    
    for i, vouch in enumerate(vouches[:10], 1):
        vouch_time = datetime.datetime.fromisoformat(vouch['timestamp']).strftime("%Y-%m-%d")
        embed.add_field(
            name=f"#{i} - {vouch['service']} ({vouch['average_rating']}⭐)",
            value=(
                f"**By:** <@{vouch['vouched_by_id']}>\n"
                f"**Ratings:** Q:{vouch['ratings']['quality']} P:{vouch['ratings']['professionalism']} C:{vouch['ratings']['communication']}\n"
                f"**Comment:** {vouch['comment'][:50]}...\n"
                f"**Date:** {vouch_time}"
            ),
            inline=False
        )
    
    embed.set_footer(text=f"Showing {len(vouches[:10])} of {len(vouches)} vouches | Grand Line Services")
    await ctx.send(embed=embed)

# Server statistics
@bot.command(name='stats', aliases=['serverstats'])
async def stats_command(ctx):
    """View server-wide vouch statistics"""
    total_vouches = sum(len(v) for v in vouch_system.vouches.values())
    total_members = len(vouch_system.users)
    
    # Calculate top users
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
            f"**{i+1}.** <@{user_id}> - {data['total_vouches']} vouches ({data['average_rating']}⭐)"
            for i, (user_id, data) in enumerate(top_users)
        ])
        embed.add_field(name="🏆 Top Vouched Members", value=top_list, inline=False)
    
    embed.set_footer(text="Grand Line Services | Developed by Darshith Dev")
    await ctx.send(embed=embed)

# Top members command
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

# Remove vouch (admin only)
@bot.command(name='removevouch', aliases=['rv'])
@commands.has_permissions(administrator=True)
async def remove_vouch(ctx, member: discord.Member, vouch_number: int):
    """Remove a specific vouch (Admin only)"""
    user_vouches = vouch_system.vouches.get(str(member.id), [])
    
    if vouch_number < 1 or vouch_number > len(user_vouches):
        await ctx.send("🌊 Invalid vouch number!")
        return
    
    removed_vouch = user_vouches.pop(vouch_number - 1)
    vouch_system.update_user_stats(member.id)
    vouch_system.save_data()
    
    await ctx.send(f"✅ Vouch #{vouch_number} for {member.mention} removed successfully!")

# Add reaction for easy vouching
@bot.command(name='easyvouch', aliases=['ev'])
async def easy_vouch(ctx, member: discord.Member):
    """Simple vouch with rating reactions"""
    embed = discord.Embed(
        title=f"⭐ Vouch for {member.display_name}",
        description="React with the appropriate rating:\n"
                   "1️⃣ - Poor\n2️⃣ - Fair\n3️⃣ - Good\n4️⃣ - Great\n5️⃣ - Excellent",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=embed)
    
    # Add reaction options
    for emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']:
        await msg.add_reaction(emoji)

# Error handling for permission
@remove_vouch.error
async def remove_vouch_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🌊 **Access Denied:** Only Grand Line Captains (Admins) can use this command!")

# Run the bot
if __name__ == "__main__":
    # Replace with your bot token
    bot.run('YOUR_BOT_TOKEN_HERE')

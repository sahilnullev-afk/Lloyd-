import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# --- INTERACTIVE DROPDOWN MENU ---
class VcCommandSelect(discord.ui.Select):
    def __init__(self, bot, target_user=None):
        self.bot = bot
        self.target_user = target_user
        options = [
            discord.SelectOption(label="24h Top VC Members", value="vc_top", description="Pichle 24 hours ke top 20 VC active members", emoji="🎙️"),
            discord.SelectOption(label="Weekly Top VC Members", value="vcw_top", description="Pichle 7 days ke top VC active members", emoji="👑"),
            discord.SelectOption(label="User 24h VC Stats", value="vc_user", description="Selected user ki 24h channel breakdown", emoji="📊"),
            discord.SelectOption(label="User Weekly VC Combined", value="vcw_user", description="User ke 24h + 7 Days total VC stats", emoji="📈"),
            discord.SelectOption(label="VC Tracker Help Guide", value="vc_help", description="All VC tracking commands info", emoji="❓")
        ]
        super().__init__(placeholder="⚡ Select VC Command to Execute...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cog = self.bot.get_cog("VcTracker")
        if not cog:
            await interaction.followup.send("❌ Error: VcTracker Cog active nahi hai!", ephemeral=True)
            return

        user = self.target_user or interaction.user
        val = self.values[0]

        if val == "vc_top":
            embed, view = await cog.get_vc_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vcw_top":
            embed, view = await cog.get_vcw_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vc_user":
            embed, view = await cog.get_vc_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vcw_user":
            embed, view = await cog.get_vcw_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "vc_help":
            embed, view = await cog.get_vc_help_data(interaction.user)
            await interaction.followup.send(embed=embed, view=view)


# --- PAGINATION & DROPDOWN COMBINED VIEW ---
class VcTopPaginationView(discord.ui.View):
    def __init__(self, bot, author, rows, guild, format_func):
        super().__init__(timeout=180)
        self.bot = bot
        self.author = author
        self.rows = rows
        self.guild = guild
        self.format_func = format_func
        self.current_page = 1
        
        self.add_item(VcCommandSelect(bot))
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_page == 1)
        self.next_btn.disabled = (self.current_page == 2 or len(self.rows) <= 10)

    def create_embed(self):
        embed = discord.Embed(
            title="🎙️ Top 20 Voice Active Members (Last 24 Hours)",
            description="*(Pichle 24 ghante ke top voice active users)*\n",
            color=discord.Color.red()
        )

        if self.current_page == 1:
            page_rows = self.rows[:10]
            start_rank = 1
            rank_title = "📍 Rank 1 - 10"
        else:
            page_rows = self.rows[10:20]
            start_rank = 11
            rank_title = "📍 Rank 11 - 20"

        lines = []
        for idx, item in enumerate(page_rows, start_rank):
            user_id = item["_id"]
            total_sec = item["total_duration"]
            member = self.guild.get_member(user_id)
            name = member.display_name if member else f"User `{user_id}`"
            formatted_time = self.format_func(total_sec)
            lines.append(f"**{idx}.** `{name[:15]}`: **{formatted_time}**")

        page_text = "\n".join(lines) if lines else "No Data"
        embed.add_field(name=rank_title, value=page_text, inline=False)
        embed.set_footer(text=f"Page {self.current_page}/2 • Requested by {self.author.display_name}", icon_url=self.author.display_avatar.url)

        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Yeh action aapke liye nahi hai!", ephemeral=True)
        
        self.current_page = 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ Yeh action aapke liye nahi hai!", ephemeral=True)
        
        self.current_page = 2
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


class VcDropdownView(discord.ui.View):
    def __init__(self, bot, author, target_user=None):
        super().__init__(timeout=180)
        self.add_item(VcCommandSelect(bot, target_user))


# --- MAIN COG CLASS ---
class VcTracker(commands.Cog):
    """Voice tracker. Daily stats use India (Asia/Kolkata) calendar days."""

    IST = timezone(timedelta(hours=5, minutes=30))

    def __init__(self, bot):
        self.bot = bot
        # (guild_id, user_id) -> (channel_id, join_time_utc)
        self.active_sessions = {}

    @property
    def collection(self):
        # Use the same Lloyd database created by App.py.
        db = getattr(self.bot, "async_db", None)
        if db is not None:
            return db["vc_logs"]
        return None

    def format_seconds(self, seconds):
        seconds = int(seconds or 0)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        if minutes > 0:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    @classmethod
    def ist_day_bounds(cls, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        local = now.astimezone(cls.IST)
        start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), start_local.date().isoformat()

    async def _save_session(self, guild_id, user_id, channel_id, start, end):
        """Save a VC session split at IST midnight so daily time resets exactly at 12 AM IST."""
        if self.collection is None or end <= start:
            return

        cursor = start
        while cursor < end:
            local_cursor = cursor.astimezone(self.IST)
            next_midnight_local = local_cursor.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            segment_end = min(end, next_midnight_local.astimezone(timezone.utc))
            duration = int((segment_end - cursor).total_seconds())
            if duration > 0:
                await self.collection.insert_one({
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "duration_seconds": duration,
                    "timestamp": segment_end,
                    "start_time": cursor,
                    "end_time": segment_end,
                    "date_ist": local_cursor.date().isoformat(),
                })
            cursor = segment_end

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild or self.collection is None:
            return

        now = datetime.now(timezone.utc)
        key = (member.guild.id, member.id)

        if before.channel is None and after.channel is not None:
            self.active_sessions[key] = (after.channel.id, now)

        elif before.channel is not None and after.channel is None:
            session = self.active_sessions.pop(key, None)
            if session:
                ch_id, join_time = session
                try:
                    await self._save_session(member.guild.id, member.id, ch_id, join_time, now)
                except Exception as e:
                    print(f"[VcTracker] MongoDB save error: {e}")

        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            session = self.active_sessions.pop(key, None)
            if session:
                ch_id, join_time = session
                try:
                    await self._save_session(member.guild.id, member.id, ch_id, join_time, now)
                except Exception as e:
                    print(f"[VcTracker] MongoDB save error: {e}")
            self.active_sessions[key] = (after.channel.id, now)

    @commands.Cog.listener("on_ready")
    async def on_ready_restore_voice(self):
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot or not member.voice or not member.voice.channel:
                    continue
                self.active_sessions.setdefault(
                    (guild.id, member.id),
                    (member.voice.channel.id, now)
                )

    async def _daily_rows(self, guild, user_id=None):
        if self.collection is None:
            return []
        start_utc, end_utc, date_ist = self.ist_day_bounds()
        match = {"guild_id": guild.id, "date_ist": date_ist}
        if user_id is not None:
            match["user_id"] = user_id

        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 20}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=20)

        # Legacy records created before date_ist existed.
        legacy_match = {
            "guild_id": guild.id,
            "date_ist": {"$exists": False},
            "timestamp": {"$gte": start_utc, "$lt": end_utc},
        }
        if user_id is not None:
            legacy_match["user_id"] = user_id
        legacy_pipeline = [
            {"$match": legacy_match},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}}
        ]
        legacy_rows = await self.collection.aggregate(legacy_pipeline).to_list(length=20)

        totals = {int(r["_id"]): int(r.get("total_duration", 0)) for r in rows}
        for r in legacy_rows:
            uid = int(r["_id"])
            totals[uid] = totals.get(uid, 0) + int(r.get("total_duration", 0))

        # Add currently active sessions. This also makes !vc top show time immediately.
        now = datetime.now(timezone.utc)
        for (gid, uid), (channel_id, join_time) in self.active_sessions.items():
            if gid != guild.id or (user_id is not None and uid != user_id):
                continue
            overlap_start = max(join_time, start_utc)
            overlap_end = min(now, end_utc)
            if overlap_end > overlap_start:
                totals[uid] = totals.get(uid, 0) + int((overlap_end - overlap_start).total_seconds())

        result = [{"_id": uid, "total_duration": sec} for uid, sec in totals.items()]
        result.sort(key=lambda x: x["total_duration"], reverse=True)
        return result[:20]

    async def get_vc_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!", color=discord.Color.red()), None

        rows = await self._daily_rows(guild)
        if not rows:
            embed = discord.Embed(
                title="🎙️ Top 20 Voice Active Members (Today)",
                description="⚠️ Aaj 12:00 AM IST ke baad koi Voice Activity record nahi mila.",
                color=discord.Color.red()
            )
            return embed, VcDropdownView(self.bot, author)

        view = VcTopPaginationView(self.bot, author, rows, guild, self.format_seconds)
        embed = view.create_embed()
        embed.title = "🎙️ Top 20 Voice Active Members (Today)"
        embed.description = "*(Aaj ka VC time — India time 12:00 AM se reset)*\n"
        return embed, view

    async def get_vcw_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!", color=discord.Color.red()), None

        time_7d_ago = datetime.now(timezone.utc) - timedelta(days=7)
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 10}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=10)

        # Add active time from the last 7 days (normally only today's active session matters).
        now = datetime.now(timezone.utc)
        for (gid, uid), (_, join_time) in self.active_sessions.items():
            if gid != guild.id:
                continue
            overlap_start = max(join_time, time_7d_ago)
            if now > overlap_start:
                found = next((r for r in rows if int(r["_id"]) == uid), None)
                extra = int((now - overlap_start).total_seconds())
                if found:
                    found["total_duration"] += extra
                else:
                    rows.append({"_id": uid, "total_duration": extra})
        rows.sort(key=lambda x: x["total_duration"], reverse=True)
        rows = rows[:10]

        embed = discord.Embed(title="👑 Top VC Active Members (Weekly / 7 Days)", color=discord.Color.red())
        if not rows:
            embed.description = "⚠️ Is week koi Voice activity record nahi mila."
        else:
            lines = []
            for idx, item in enumerate(rows, 1):
                member = guild.get_member(item["_id"])
                name = member.mention if member else f"User `{item['_id']}`"
                lines.append(f"**#{idx}** {name} — ⏱️ **{self.format_seconds(item['total_duration'])}**")
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
        return embed, VcDropdownView(self.bot, author)

    async def get_vc_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!", color=discord.Color.red()), None

        start_utc, end_utc, date_ist = self.ist_day_bounds()
        pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "date_ist": date_ist}},
            {"$group": {"_id": "$channel_id", "total_sec": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_sec": -1}}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=None)

        legacy_pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "date_ist": {"$exists": False}, "timestamp": {"$gte": start_utc, "$lt": end_utc}}},
            {"$group": {"_id": "$channel_id", "total_sec": {"$sum": "$duration_seconds"}}}
        ]
        legacy = await self.collection.aggregate(legacy_pipeline).to_list(length=None)
        by_channel = {int(r["_id"]): int(r["total_sec"]) for r in rows}
        for r in legacy:
            cid = int(r["_id"])
            by_channel[cid] = by_channel.get(cid, 0) + int(r["total_sec"])

        # Current active session overlap with today.
        now = datetime.now(timezone.utc)
        active = self.active_sessions.get((guild.id, target_user.id))
        if active:
            ch_id, join_time = active
            overlap_start = max(join_time, start_utc)
            overlap_end = min(now, end_utc)
            if overlap_end > overlap_start:
                by_channel[ch_id] = by_channel.get(ch_id, 0) + int((overlap_end - overlap_start).total_seconds())

        embed = discord.Embed(title=f"📊 Today's VC Activity — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        total = sum(by_channel.values())
        if not by_channel:
            embed.description = "⚠️ Aaj 12:00 AM IST ke baad is user ne VC use nahi kiya hai."
        else:
            embed.description = "**Voice Channel Breakdown:**\n" + "\n".join(
                f"• {guild.get_channel(cid).mention if guild.get_channel(cid) else '#deleted-vc'}: **{self.format_seconds(sec)}**"
                for cid, sec in sorted(by_channel.items(), key=lambda x: x[1], reverse=True)
            )
        embed.add_field(name="⏱️ Today's VC Time", value=f"**{self.format_seconds(total)}**", inline=False)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vcw_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!", color=discord.Color.red()), None

        now = datetime.now(timezone.utc)
        start_7d = now - timedelta(days=7)
        pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": start_7d}}},
            {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}
        ]
        res = await self.collection.aggregate(pipeline).to_list(length=1)
        total = int(res[0]["total"]) if res else 0

        active = self.active_sessions.get((guild.id, target_user.id))
        if active:
            total += max(0, int((now - active[1]).total_seconds()))

        embed = discord.Embed(title=f"📈 Overview VC Stats — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        daily_rows = await self._daily_rows(guild, target_user.id)
        daily_total = daily_rows[0]["total_duration"] if daily_rows else 0
        embed.add_field(name="🇮🇳 Today (IST)", value=f"**{self.format_seconds(daily_total)}**", inline=True)
        embed.add_field(name="📅 Last 7 Days", value=f"**{self.format_seconds(total)}**", inline=True)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vc_help_data(self, author):
        embed = discord.Embed(title="❓ Voice Tracking System — Commands Guide", description="Commands typing se ya neeche diye gaye dropdown menu se directly run karein:", color=discord.Color.red())
        embed.add_field(name="🔹 !vc top", value="Aaj ka Top 20 VC — India time 12:00 AM par daily reset.", inline=False)
        embed.add_field(name="🔹 !vc @user", value="Aaj ka member VC time aur channel breakdown.", inline=False)
        embed.add_field(name="🔹 !vcw top", value="Pichle 7 Days ka Top VC leaderboard.", inline=False)
        embed.add_field(name="🔹 !vcw @user", value="Aaj + pichle 7 days ka VC summary.", inline=False)
        embed.add_field(name="🔹 !vc help", value="Ye VC Help Menu display karega.", inline=False)
        embed.set_footer(text="⚡ Select commands from the dropdown menu below!")
        return embed, VcDropdownView(self.bot, author)

    @commands.hybrid_group(name="vc", invoke_without_command=True)
    async def vc_group(self, ctx, member: discord.Member = None):
        try:
            target = member or ctx.author
            embed, view = await self.get_vc_user_data(ctx.guild, target)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vc error: {e}")
            await ctx.send("❌ VC tracker error. Check MongoDB connection.")

    @vc_group.command(name="top")
    async def vc_top(self, ctx):
        try:
            embed, view = await self.get_vc_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vc top error: {e}")
            await ctx.send("❌ VC tracker error. Check MongoDB connection.")

    @vc_group.command(name="help")
    async def vc_help_cmd(self, ctx):
        embed, view = await self.get_vc_help_data(ctx.author)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_group(name="vcw", invoke_without_command=True)
    async def vcw_group(self, ctx, member: discord.Member = None):
        try:
            target = member or ctx.author
            embed, view = await self.get_vcw_user_data(ctx.guild, target)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vcw error: {e}")
            await ctx.send("❌ VC tracker error. Check MongoDB connection.")

    @vcw_group.command(name="top")
    async def vcw_top(self, ctx):
        try:
            embed, view = await self.get_vcw_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vcw top error: {e}")
            await ctx.send("❌ VC tracker error. Check MongoDB connection.")


async def setup(bot):
    await bot.add_cog(VcTracker(bot))

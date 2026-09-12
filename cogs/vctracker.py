import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
            title="🎙️ Top 20 Voice Active Members (Today - IST)",
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
IST = ZoneInfo("Asia/Kolkata")


class VcTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # key = (guild_id, user_id), value = (channel_id, join_time_utc)
        self.active_sessions = {}

    @property
    def collection(self):
        if getattr(self.bot, "async_db", None) is not None:
            return self.bot.async_db["vc_logs"]
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

    def day_bounds_ist(self, days_ago=0):
        local_start = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
        local_end = local_start + timedelta(days=1)
        return local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)

    def day_start_ist(self):
        return self.day_bounds_ist(0)[0]

    def daily_match(self, guild_id, user_id=None):
        start, end = self.day_bounds_ist(0)
        base = {"guild_id": guild_id}
        if user_id is not None:
            base["user_id"] = user_id
        return {"$and": [base, {"$or": [
            {"date_ist": datetime.now(IST).date().isoformat()},
            {"timestamp": {"$gte": start, "$lt": end}},
        ]}]}

    async def save_session(self, guild_id, user_id, channel_id, start, end):
        if self.collection is None or end <= start:
            return
        cursor = start
        while cursor < end:
            local_cursor = cursor.astimezone(IST)
            next_midnight_local = local_cursor.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            segment_end = min(end, next_midnight_local.astimezone(timezone.utc))
            seconds = int((segment_end - cursor).total_seconds())
            if seconds > 0:
                await self.collection.insert_one({
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "duration_seconds": seconds,
                    "timestamp": segment_end,
                    "date_ist": cursor.astimezone(IST).date().isoformat(),
                })
            cursor = segment_end

    async def active_seconds(self, guild_id, user_id, start, end):
        session = self.active_sessions.get((guild_id, user_id))
        if not session:
            return 0
        _, joined = session
        now = datetime.now(timezone.utc)
        overlap_start = max(joined, start)
        overlap_end = min(now, end)
        return max(0, int((overlap_end - overlap_start).total_seconds()))

    @commands.Cog.listener("on_ready")
    async def restore_active_sessions(self):
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            for member in guild.members:
                if not member.bot and member.voice and member.voice.channel:
                    self.active_sessions[(guild.id, member.id)] = (member.voice.channel.id, now)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or self.collection is None:
            return
        now = datetime.now(timezone.utc)
        key = (member.guild.id, member.id)

        if before.channel is None and after.channel is not None:
            self.active_sessions[key] = (after.channel.id, now)
            return

        if before.channel is not None and after.channel is None:
            session = self.active_sessions.pop(key, None)
            if session:
                channel_id, joined = session
                try:
                    await self.save_session(member.guild.id, member.id, channel_id, joined, now)
                except Exception as e:
                    print(f"[VC Tracker MongoDB Error] {e}")
            return

        if before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            session = self.active_sessions.pop(key, None)
            if session:
                channel_id, joined = session
                try:
                    await self.save_session(member.guild.id, member.id, channel_id, joined, now)
                except Exception as e:
                    print(f"[VC Tracker MongoDB Error] {e}")
            self.active_sessions[key] = (after.channel.id, now)

    async def aggregate(self, pipeline, limit=None):
        if self.collection is None:
            return []
        rows = await self.collection.aggregate(pipeline).to_list(length=limit)
        return rows

    async def get_vc_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="❌ MongoDB connection error! Check MONGO_URI in Render.", color=discord.Color.red()), VcDropdownView(self.bot, author)
        start, end = self.day_bounds_ist(0)
        try:
            rows = await self.aggregate([
                {"$match": self.daily_match(guild.id)},
                {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
                {"$sort": {"total_duration": -1}},
                {"$limit": 20}
            ], 20)
            # Include time for members currently in VC.
            for row in rows:
                row["total_duration"] += await self.active_seconds(guild.id, row["_id"], start, end)
            present = {row["_id"] for row in rows}
            for (g_id, u_id) in self.active_sessions:
                if g_id == guild.id and u_id not in present:
                    sec = await self.active_seconds(guild.id, u_id, start, end)
                    if sec > 0:
                        rows.append({"_id": u_id, "total_duration": sec})
            rows.sort(key=lambda x: x["total_duration"], reverse=True)
            rows = rows[:20]
        except Exception as e:
            print(f"[VC Tracker MongoDB Error] {e}")
            return discord.Embed(title="Error", description="❌ MongoDB query failed. Check Render logs for `[VC Tracker MongoDB Error]`.", color=discord.Color.red()), VcDropdownView(self.bot, author)
        if not rows:
            return discord.Embed(title="🎙️ Top 20 Voice Active Members (Today)", description="⚠️ Aaj 12:00 AM IST ke baad koi Voice Activity record nahi mila.", color=discord.Color.red()), VcDropdownView(self.bot, author)
        view = VcTopPaginationView(self.bot, author, rows, guild, self.format_seconds)
        return view.create_embed(), view

    async def get_vcw_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="❌ MongoDB connection error! Check MONGO_URI in Render.", color=discord.Color.red()), VcDropdownView(self.bot, author)
        start = self.day_start_ist() - timedelta(days=6)
        try:
            rows = await self.aggregate([
                {"$match": {"guild_id": guild.id, "timestamp": {"$gte": start}}},
                {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
                {"$sort": {"total_duration": -1}},
                {"$limit": 10}
            ], 10)
        except Exception as e:
            print(f"[VC Tracker MongoDB Error] {e}")
            return discord.Embed(title="Error", description="❌ MongoDB query failed. Check Render logs.", color=discord.Color.red()), VcDropdownView(self.bot, author)
        embed = discord.Embed(title="👑 Top VC Active Members (Last 7 Days)", color=discord.Color.red())
        if not rows:
            embed.description = "⚠️ Last 7 days me koi Voice activity record nahi mila."
        else:
            embed.description = "\n".join(f"**#{i}** {guild.get_member(x['_id']).mention if guild.get_member(x['_id']) else f'User `{x["_id"]}`'} — ⏱️ **{self.format_seconds(x['total_duration'])}**" for i, x in enumerate(rows, 1))
        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
        return embed, VcDropdownView(self.bot, author)

    async def get_vc_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="❌ MongoDB connection error! Check MONGO_URI in Render.", color=discord.Color.red()), VcDropdownView(self.bot, target_user, target_user)
        start, end = self.day_bounds_ist(0)
        try:
            rows = await self.aggregate([
                {"$match": self.daily_match(guild.id, target_user.id)},
                {"$group": {"_id": "$channel_id", "total_sec": {"$sum": "$duration_seconds"}}},
                {"$sort": {"total_sec": -1}}
            ], 1000)
            active = await self.active_seconds(guild.id, target_user.id, start, end)
            session = self.active_sessions.get((guild.id, target_user.id))
            if active > 0 and session:
                channel_id = session[0]
                existing = next((x for x in rows if x["_id"] == channel_id), None)
                if existing:
                    existing["total_sec"] += active
                else:
                    rows.append({"_id": channel_id, "total_sec": active})
            rows.sort(key=lambda x: x["total_sec"], reverse=True)
        except Exception as e:
            print(f"[VC Tracker MongoDB Error] {e}")
            return discord.Embed(title="Error", description="❌ MongoDB query failed. Check Render logs.", color=discord.Color.red()), VcDropdownView(self.bot, target_user, target_user)
        embed = discord.Embed(title=f"📊 Today's VC Activity — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        total = sum(x["total_sec"] for x in rows)
        if not rows:
            embed.description = "⚠️ Aaj 12:00 AM IST ke baad is user ne VC use nahi kiya hai."
        else:
            embed.description = "**Voice Channel Breakdown:**\n" + "\n".join(f"• {guild.get_channel(x['_id']).mention if guild.get_channel(x['_id']) else '#deleted-vc'}: **{self.format_seconds(x['total_sec'])}**" for x in rows)
        embed.add_field(name="⏱️ Today's VC Time", value=f"**{self.format_seconds(total)}**", inline=False)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vcw_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="❌ MongoDB connection error! Check MONGO_URI in Render.", color=discord.Color.red()), VcDropdownView(self.bot, target_user, target_user)
        start_day = self.day_start_ist()
        start_7d = start_day - timedelta(days=6)
        try:
            rows_day = await self.aggregate([{"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": start_day}}}, {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}], 1)
            rows_7d = await self.aggregate([{"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": start_7d}}}, {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}], 1)
            sec_day = (rows_day[0]["total"] if rows_day else 0) + await self.active_seconds(guild.id, target_user.id, start_day, start_day + timedelta(days=1))
            sec_7d = (rows_7d[0]["total"] if rows_7d else 0) + await self.active_seconds(guild.id, target_user.id, start_7d, datetime.now(timezone.utc))
        except Exception as e:
            print(f"[VC Tracker MongoDB Error] {e}")
            return discord.Embed(title="Error", description="❌ MongoDB query failed. Check Render logs.", color=discord.Color.red()), VcDropdownView(self.bot, target_user, target_user)
        embed = discord.Embed(title=f"📈 Overview VC Stats — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="🇮🇳 Today", value=f"**{self.format_seconds(sec_day)}**", inline=True)
        embed.add_field(name="📅 Last 7 Days", value=f"**{self.format_seconds(sec_7d)}**", inline=True)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vc_help_data(self, author):
        embed = discord.Embed(title="❓ Voice Tracking System — Commands Guide", description="Commands typing se ya neeche diye gaye dropdown menu se directly run karein:", color=discord.Color.red())
        embed.add_field(name="🔹 !vc top", value="Aaj 12:00 AM IST se Top 20 Active VC Members (Page 1: 1-10 | Page 2: 11-20).", inline=False)
        embed.add_field(name="🔹 !vc @user", value="Targeted member ki aaj ki channel-wise VC Time breakdown.", inline=False)
        embed.add_field(name="🔹 !vcw top", value="Pichle 7 Days ke Top VC Users ki Leaderboard.", inline=False)
        embed.add_field(name="🔹 !vcw @user", value="Member ka Today aur 7 Days total VC time summary.", inline=False)
        embed.add_field(name="🔹 !vc help", value="Ye VC Help Menu display karega.", inline=False)
        embed.set_footer(text="⚡ Select commands from the dropdown menu below!")
        return embed, VcDropdownView(self.bot, author)

    @commands.hybrid_group(name="vc", invoke_without_command=True)
    async def vc_group(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed, view = await self.get_vc_user_data(ctx.guild, target)
        await ctx.send(embed=embed, view=view)

    @vc_group.command(name="top")
    async def vc_top(self, ctx):
        embed, view = await self.get_vc_top_data(ctx.guild, ctx.author)
        await ctx.send(embed=embed, view=view)

    @vc_group.command(name="help")
    async def vc_help_cmd(self, ctx):
        embed, view = await self.get_vc_help_data(ctx.author)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_group(name="vcw", invoke_without_command=True)
    async def vcw_group(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed, view = await self.get_vcw_user_data(ctx.guild, target)
        await ctx.send(embed=embed, view=view)

    @vcw_group.command(name="top")
    async def vcw_top(self, ctx):
        embed, view = await self.get_vcw_top_data(ctx.guild, ctx.author)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(VcTracker(bot))
            

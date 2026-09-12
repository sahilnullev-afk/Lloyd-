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
    def __init__(self, bot):
        self.bot = bot
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
        elif minutes > 0:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or self.collection is None:
            return

        now = datetime.now(timezone.utc)

        # VC Join
        if before.channel is None and after.channel is not None:
            self.active_sessions[member.id] = (after.channel.id, now)

        # VC Leave
        elif before.channel is not None and after.channel is None:
            session = self.active_sessions.pop(member.id, None)
            if session:
                ch_id, join_time = session
                duration = int((now - join_time).total_seconds())
                if duration > 0:
                    await self.collection.insert_one({
                        "guild_id": member.guild.id,
                        "channel_id": ch_id,
                        "user_id": member.id,
                        "duration_seconds": duration,
                        "timestamp": now
                    })

        # Channel Switch
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            session = self.active_sessions.pop(member.id, None)
            if session:
                ch_id, join_time = session
                duration = int((now - join_time).total_seconds())
                if duration > 0:
                    await self.collection.insert_one({
                        "guild_id": member.guild.id,
                        "channel_id": ch_id,
                        "user_id": member.id,
                        "duration_seconds": duration,
                        "timestamp": now
                    })
            self.active_sessions[member.id] = (after.channel.id, now)

    @commands.Cog.listener()
    async def on_ready_restore_voice(self):
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot or not member.voice or not member.voice.channel:
                    continue
                self.active_sessions.setdefault(member.id, (member.voice.channel.id, now))

    async def get_vc_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 20}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=20)

        # Include currently active VC sessions too, so !vc / !vc top shows time
        # immediately instead of waiting for the member to leave VC.
        active = {}
        now = datetime.now(timezone.utc)
        for user_id, (channel_id, join_time) in self.active_sessions.items():
            member = guild.get_member(user_id)
            if member and member.voice and member.voice.channel:
                active[user_id] = int((now - join_time).total_seconds())
        totals = {int(r["_id"]): int(r["total_duration"]) for r in rows}
        for uid, seconds in active.items():
            totals[uid] = totals.get(uid, 0) + seconds
        if active:
            rows = [{"_id": uid, "total_duration": sec} for uid, sec in totals.items()]
            rows.sort(key=lambda x: x["total_duration"], reverse=True)
            rows = rows[:20]

        if not rows:
            embed = discord.Embed(
                title="🎙️ Top 20 Voice Active Members (Last 24 Hours)",
                description="⚠️ Pichle 24 ghante me koi Voice Activity record nahi mila.",
                color=discord.Color.red()
            )
            return embed, VcDropdownView(self.bot, author)

        view = VcTopPaginationView(self.bot, author, rows, guild, self.format_seconds)
        embed = view.create_embed()
        return embed, view

    async def get_vcw_top_data(self, guild, author):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_7d_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": "$user_id", "total_duration": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_duration": -1}},
            {"$limit": 10}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=20)

        embed = discord.Embed(title="👑 Top VC Active Members (Weekly / 7 Days)", color=discord.Color.red())

        if not rows:
            embed.description = "⚠️ Is week koi Voice activity record nahi mila."
        else:
            description_lines = []
            for idx, item in enumerate(rows, 1):
                user_id = item["_id"]
                total_sec = item["total_duration"]
                member = guild.get_member(user_id)
                name = member.mention if member else f"User `{user_id}`"
                formatted_time = self.format_seconds(total_sec)
                description_lines.append(f"**#{idx}** {name} — ⏱️ **{formatted_time}**")
            embed.description = "\n".join(description_lines)

        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
        return embed, VcDropdownView(self.bot, author)

    async def get_vc_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        time_24h_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": "$channel_id", "total_sec": {"$sum": "$duration_seconds"}}},
            {"$sort": {"total_sec": -1}}
        ]
        rows = await self.collection.aggregate(pipeline).to_list(length=20)

        embed = discord.Embed(
            title=f"📊 24h VC Activity Breakdown — {target_user.display_name}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        total_24h_sec = sum(item["total_sec"] for item in rows)
        
        if not rows:
            embed.description = "⚠️ Pichle 24 ghante me is user ne VC use nahi kiya hai."
        else:
            channel_breakdown = []
            for item in rows:
                ch_id = item["_id"]
                total_sec = item["total_sec"]
                ch = guild.get_channel(ch_id)
                ch_name = ch.mention if ch else f"#deleted-vc"
                channel_breakdown.append(f"• {ch_name}: **{self.format_seconds(total_sec)}**")

            embed.description = "**Voice Channel Breakdown:**\n" + "\n".join(channel_breakdown)

        embed.add_field(name="⏱️ Total 24h VC Time", value=f"**{self.format_seconds(total_24h_sec)}**", inline=False)
        embed.set_footer(text=f"User ID: {target_user.id}")

        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vcw_user_data(self, guild, target_user):
        if self.collection is None:
            return discord.Embed(title="Error", description="Database connection error!"), None

        now = datetime.now(timezone.utc)
        time_24h_ago = now - timedelta(hours=24)
        time_7d_ago = now - timedelta(days=7)

        # 24h Total
        pipeline_24h = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_24h_ago}}},
            {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}
        ]
        res_24h = await self.collection.aggregate(pipeline_24h).to_list(length=1)
        sec_24h = res_24h[0]["total"] if res_24h else 0

        # 7d Total
        pipeline_7d = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": None, "total": {"$sum": "$duration_seconds"}}}
        ]
        res_7d = await self.collection.aggregate(pipeline_7d).to_list(length=1)
        sec_7d = res_7d[0]["total"] if res_7d else 0

        embed = discord.Embed(
            title=f"📈 Overview VC Stats — {target_user.display_name}",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="⏰ Last 24 Hours", value=f"**{self.format_seconds(sec_24h)}**", inline=True)
        embed.add_field(name="📅 Last 7 Days (Weekly)", value=f"**{self.format_seconds(sec_7d)}**", inline=True)
        embed.set_footer(text=f"User ID: {target_user.id}")

        return embed, VcDropdownView(self.bot, target_user, target_user)

    async def get_vc_help_data(self, author):
        embed = discord.Embed(
            title="❓ Voice Tracking System — Commands Guide",
            description="Commands typing se ya neeche diye gaye dropdown menu se directly run karein:",
            color=discord.Color.red()
        )
        embed.add_field(name="🔹 !vc top", value="Pichle 24 Hours ke Top 20 Active VC Members (Page 1: 1-10 | Page 2: 11-20).", inline=False)
        embed.add_field(name="🔹 !vc @user", value="Targeted member ki 24h Channel-wise VC Time breakdown.", inline=False)
        embed.add_field(name="🔹 !vcw top", value="Pichle 7 Days (Weekly) ke Top VC Users ki Leaderboard.", inline=False)
        embed.add_field(name="🔹 !vcw @user", value="Member ka 24h aur 7 Days (Weekly) total VC time summary.", inline=False)
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
            await ctx.send("❌ Voice tracker error. Check MongoDB connection.")

    @vc_group.command(name="top")
    async def vc_top(self, ctx):
        try:
            embed, view = await self.get_vc_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vc top error: {e}")
            await ctx.send("❌ Voice tracker error. Check MongoDB connection.")

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
            await ctx.send("❌ Voice tracker error. Check MongoDB connection.")

    @vcw_group.command(name="top")
    async def vcw_top(self, ctx):
        try:
            embed, view = await self.get_vcw_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[VcTracker] !vcw top error: {e}")
            await ctx.send("❌ Voice tracker error. Check MongoDB connection.")


async def setup(bot):
    await bot.add_cog(VcTracker(bot))
            

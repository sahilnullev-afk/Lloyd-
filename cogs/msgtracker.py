import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# --- INTERACTIVE DROPDOWN MENU ---
class MsgCommandSelect(discord.ui.Select):
    def __init__(self, bot, target_user=None):
        self.bot = bot
        self.target_user = target_user
        options = [
            discord.SelectOption(label="24h Top Members", value="msg_top", description="Pichle 24 hours ke top 20 members", emoji="🏆"),
            discord.SelectOption(label="Weekly Top Members", value="msgw_top", description="Pichle 7 days ke top members", emoji="⭐"),
            discord.SelectOption(label="User 24h Stats", value="msg_user", description="Selected user ki 24h channel breakdown", emoji="📊"),
            discord.SelectOption(label="User Weekly Combined", value="msgw_user", description="User ke 24h + 7 Days total stats", emoji="📈"),
            discord.SelectOption(label="Message Help Guide", value="msg_help", description="All message tracking commands info", emoji="❓")
        ]
        super().__init__(placeholder="⚡ Select Command to Execute...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cog = self.bot.get_cog("MsgTracker")
        if not cog:
            await interaction.followup.send("❌ Error: MsgTracker Cog active nahi hai!", ephemeral=True)
            return

        user = self.target_user or interaction.user
        val = self.values[0]

        if val == "msg_top":
            embed, view = await cog.get_msg_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "msgw_top":
            embed, view = await cog.get_msgw_top_data(interaction.guild, interaction.user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "msg_user":
            embed, view = await cog.get_msg_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "msgw_user":
            embed, view = await cog.get_msgw_user_data(interaction.guild, user)
            await interaction.followup.send(embed=embed, view=view)
        elif val == "msg_help":
            embed, view = await cog.get_msg_help_data(interaction.user)
            await interaction.followup.send(embed=embed, view=view)


# --- PAGINATION & DROPDOWN COMBINED VIEW ---
class MsgTopPaginationView(discord.ui.View):
    def __init__(self, bot, author, rows, guild):
        super().__init__(timeout=180)
        self.bot = bot
        self.author = author
        self.rows = rows
        self.guild = guild
        self.current_page = 1
        
        self.add_item(MsgCommandSelect(bot))
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_page == 1)
        self.next_btn.disabled = (self.current_page == 2 or len(self.rows) <= 10)

    def create_embed(self):
        embed = discord.Embed(
            title="TOP 10 CHAT MEMBERS",
            color=discord.Color.red()
        )

        if self.current_page == 1:
            page_rows = self.rows[:10]
            start_rank = 1
        else:
            page_rows = self.rows[10:20]
            start_rank = 11

        lines = []
        for idx, item in enumerate(page_rows, start_rank):
            user_id = item["_id"]
            count = item["msg_count"]
            member = self.guild.get_member(user_id)
            name = member.display_name if member else f"User `{user_id}`"
            lines.append(f"**{idx}.** `{name[:15]}`: **{count}** msgs")

        page_text = "\n".join(lines) if lines else "No Data"
        embed.description = page_text
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


class MsgDropdownView(discord.ui.View):
    def __init__(self, bot, author, target_user=None):
        super().__init__(timeout=180)
        self.add_item(MsgCommandSelect(bot, target_user))


# --- MAIN COG CLASS ---
class MsgTracker(commands.Cog):
    """Message tracker. Daily stats use India (Asia/Kolkata) calendar days."""

    IST = timezone(timedelta(hours=5, minutes=30))

    def __init__(self, bot):
        self.bot = bot

    @property
    def msg_col(self):
        db = getattr(self.bot, "async_db", None)
        if db is not None:
            return db["message_logs"]
        return None

    @classmethod
    def ist_day_bounds(cls, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        local = now.astimezone(cls.IST)
        start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), start_local.date().isoformat()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or self.msg_col is None:
            return
        try:
            now = datetime.now(timezone.utc)
            await self.msg_col.insert_one({
                "guild_id": message.guild.id,
                "channel_id": message.channel.id,
                "user_id": message.author.id,
                "timestamp": now,
                "date_ist": now.astimezone(self.IST).date().isoformat(),
            })
        except Exception as e:
            print(f"[MsgTracker] MongoDB save error: {e}")

    async def get_msg_top_data(self, guild, author):
        if self.msg_col is None:
            embed = discord.Embed(title="Error", description="❌ Database connection error!", color=discord.Color.red())
            return embed, MsgDropdownView(self.bot, author)

        start_utc, end_utc, date_ist = self.ist_day_bounds()
        pipeline = [
            {"$match": {"guild_id": guild.id, "date_ist": date_ist}},
            {"$group": {"_id": "$user_id", "msg_count": {"$sum": 1}}},
            {"$sort": {"msg_count": -1}},
            {"$limit": 20}
        ]
        rows = await self.msg_col.aggregate(pipeline).to_list(length=20)

        # Include old records that do not have date_ist.
        legacy_pipeline = [
            {"$match": {"guild_id": guild.id, "date_ist": {"$exists": False}, "timestamp": {"$gte": start_utc, "$lt": end_utc}}},
            {"$group": {"_id": "$user_id", "msg_count": {"$sum": 1}}}
        ]
        legacy = await self.msg_col.aggregate(legacy_pipeline).to_list(length=20)
        totals = {int(r["_id"]): int(r["msg_count"]) for r in rows}
        for r in legacy:
            uid = int(r["_id"])
            totals[uid] = totals.get(uid, 0) + int(r["msg_count"])
        rows = [{"_id": uid, "msg_count": count} for uid, count in totals.items()]
        rows.sort(key=lambda x: x["msg_count"], reverse=True)
        rows = rows[:20]

        if not rows:
            embed = discord.Embed(title="TOP 10 CHAT MEMBERS", description="⚠️ Aaj 12:00 AM IST ke baad koi message data available nahi hai.", color=discord.Color.red())
            return embed, MsgDropdownView(self.bot, author)
        view = MsgTopPaginationView(self.bot, author, rows, guild)
        embed = view.create_embed()
        embed.title = "TOP 10 CHAT MEMBERS — TODAY (IST)"
        return embed, view

    async def get_msgw_top_data(self, guild, author):
        if self.msg_col is None:
            embed = discord.Embed(title="Error", description="❌ Database connection error!", color=discord.Color.red())
            return embed, MsgDropdownView(self.bot, author)

        time_7d_ago = datetime.now(timezone.utc) - timedelta(days=7)
        pipeline = [
            {"$match": {"guild_id": guild.id, "timestamp": {"$gte": time_7d_ago}}},
            {"$group": {"_id": "$user_id", "msg_count": {"$sum": 1}}},
            {"$sort": {"msg_count": -1}},
            {"$limit": 10}
        ]
        rows = await self.msg_col.aggregate(pipeline).to_list(length=10)
        embed = discord.Embed(title="⭐ Top Members Leaderboard (Weekly / 7 Days)", color=discord.Color.red())
        if not rows:
            embed.description = "⚠️ Is week koi message record nahi mila."
        else:
            lines = []
            for idx, item in enumerate(rows, 1):
                member = guild.get_member(item["_id"])
                name = member.mention if member else f"User `{item['_id']}`"
                lines.append(f"**#{idx}** {name} — **{item['msg_count']}** Messages")
            embed.description = "\n".join(lines)
        embed.set_footer(text=f"Requested by {author.display_name}", icon_url=author.display_avatar.url)
        return embed, MsgDropdownView(self.bot, author)

    async def get_msg_user_data(self, guild, target_user):
        if self.msg_col is None:
            embed = discord.Embed(title="Error", description="❌ Database connection error!", color=discord.Color.red())
            return embed, MsgDropdownView(self.bot, target_user, target_user)

        start_utc, end_utc, date_ist = self.ist_day_bounds()
        pipeline = [
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "date_ist": date_ist}},
            {"$group": {"_id": "$channel_id", "msg_count": {"$sum": 1}}},
            {"$sort": {"msg_count": -1}}
        ]
        rows = await self.msg_col.aggregate(pipeline).to_list(length=None)
        legacy = await self.msg_col.aggregate([
            {"$match": {"guild_id": guild.id, "user_id": target_user.id, "date_ist": {"$exists": False}, "timestamp": {"$gte": start_utc, "$lt": end_utc}}},
            {"$group": {"_id": "$channel_id", "msg_count": {"$sum": 1}}}
        ]).to_list(length=None)
        counts = {int(r["_id"]): int(r["msg_count"]) for r in rows}
        for r in legacy:
            cid = int(r["_id"])
            counts[cid] = counts.get(cid, 0) + int(r["msg_count"])

        embed = discord.Embed(title=f"📊 Today's Message Breakdown — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        total = sum(counts.values())
        if not counts:
            embed.description = "⚠️ Aaj 12:00 AM IST ke baad is user ne ek bhi message nahi bheja hai."
        else:
            embed.description = "**Channel Activity List:**\n" + "\n".join(
                f"• {guild.get_channel(cid).mention if guild.get_channel(cid) else '#deleted-channel'}: **{count}** msgs"
                for cid, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
            )
        embed.add_field(name="📈 Today's Messages", value=f"**{total}** Messages", inline=False)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, MsgDropdownView(self.bot, target_user, target_user)

    async def get_msgw_user_data(self, guild, target_user):
        if self.msg_col is None:
            embed = discord.Embed(title="Error", description="❌ Database connection error!", color=discord.Color.red())
            return embed, MsgDropdownView(self.bot, target_user, target_user)
        start_utc, end_utc, _ = self.ist_day_bounds()
        count_today = await self.msg_col.count_documents({"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": start_utc, "$lt": end_utc}})
        count_7d = await self.msg_col.count_documents({"guild_id": guild.id, "user_id": target_user.id, "timestamp": {"$gte": datetime.now(timezone.utc)-timedelta(days=7)}})
        embed = discord.Embed(title=f"📈 Overview Stats — {target_user.display_name}", color=discord.Color.red())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="🇮🇳 Today (IST)", value=f"**{count_today}** Messages", inline=True)
        embed.add_field(name="📅 Last 7 Days", value=f"**{count_7d}** Messages", inline=True)
        embed.set_footer(text=f"User ID: {target_user.id}")
        return embed, MsgDropdownView(self.bot, target_user, target_user)

    async def get_msg_help_data(self, author):
        embed = discord.Embed(title="❓ Message Tracking System — Commands Guide", description="Aap neeche likhi commands type karke ya dropdown menu se select karke use kar sakte hain:", color=discord.Color.red())
        embed.add_field(name="🔹 !msg top", value="Aaj ka Top 20 — India time 12:00 AM par daily reset.", inline=False)
        embed.add_field(name="🔹 !msg @user", value="Aaj ka member message breakdown.", inline=False)
        embed.add_field(name="🔹 !msgw top", value="Pichle 7 Days ka Top Message leaderboard.", inline=False)
        embed.add_field(name="🔹 !msgw @user", value="Aaj + pichle 7 days ka message summary.", inline=False)
        embed.add_field(name="🔹 !msg help", value="Ye Help Menu UI display karega.", inline=False)
        embed.set_footer(text="⚡ Select commands from the dropdown menu below!")
        return embed, MsgDropdownView(self.bot, author)

    @commands.hybrid_group(name="msg", invoke_without_command=True)
    async def msg_group(self, ctx, member: discord.Member = None):
        try:
            target = member or ctx.author
            embed, view = await self.get_msg_user_data(ctx.guild, target)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[MsgTracker] !msg error: {e}")
            await ctx.send("❌ Message tracker error. Check MongoDB connection.")

    @msg_group.command(name="top")
    async def msg_top(self, ctx):
        try:
            embed, view = await self.get_msg_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[MsgTracker] !msg top error: {e}")
            await ctx.send("❌ Message tracker error. Check MongoDB connection.")

    @msg_group.command(name="help")
    async def msg_help_cmd(self, ctx):
        embed, view = await self.get_msg_help_data(ctx.author)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_group(name="msgw", invoke_without_command=True)
    async def msgw_group(self, ctx, member: discord.Member = None):
        try:
            target = member or ctx.author
            embed, view = await self.get_msgw_user_data(ctx.guild, target)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"[MsgTracker] !msgw error: {e}")
            await ctx.send("❌ Message tracker error. Check MongoDB connection.")

    @msgw_group.command(name="top")
    async def msgw_top(self, ctx):
        try:
            embed, view = await self.get_msgw_top_data(ctx.guild, ctx.author)
            await ctx.send(embed=embed, view=view)

        except Exception as e:
            print(f"[MsgTracker] !msgw top error: {e}")
            await ctx.send("❌ Message tracker error. Check MongoDB connection.")


async def setup(bot):
    await bot.add_cog(MsgTracker(bot))

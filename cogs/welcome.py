import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

DEFAULT_WELCOME_IMAGE = (
    "https://cdn.discordapp.com/attachments/1541151143516835861/1547296509157179422/"
    "4483361f3241f14b269a4dc168756d41.jpg?ex=6aa2e7ab&is=6aa1962b&"
    "hm=e3ebdc47e29641192c31035f02e25a3ef7941e74fc8a2314012ce9a3cc6cbfbe&"
)

DEFAULT_WELCOME_TEXT = "**Welcome to your {server}\nmake chill fun play\ngossips hangout vc ect**"


def human_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - dt).total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts[:3])


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invite_cache = {}

    @property
    def welcome_col(self):
        # Same async MongoDB database supplied by App.py.
        if getattr(self.bot, "async_db", None) is not None:
            return self.bot.async_db["welcome_settings"]
        return None

    async def get_settings(self, guild_id: int):
        if self.welcome_col is None:
            return None
        return await self.welcome_col.find_one({"guild_id": guild_id})

    async def save(self, guild_id: int, **values):
        if self.welcome_col is None:
            return False
        values["guild_id"] = guild_id
        await self.welcome_col.update_one(
            {"guild_id": guild_id}, {"$set": values}, upsert=True
        )
        return True

    def help_embed(self):
        embed = discord.Embed(
            title="🎉 Welcome System",
            description=(
                "Use the commands below to setup and manage your welcome system.\n\n"
                "`!welcome setup #channel` — Set welcome channel.\n"
                "`!welcome confirm` — Setup welcome in the current channel.\n"
                "`!welcome disable` — Remove welcome setup.\n"
                "`!welcome image <link>` — Change welcome image. You can also attach an image.\n"
                "`!welcome memberscount on/off` — Show server member count.\n"
                "`!welcome account on/off` — Show the new member's account age.\n"
                "`!welcome text <text>` — Change welcome text.\n"
                "`!welcome logs #channel` — Setup professional welcome logs.\n"
                "`!welcome log disable` — Remove welcome logs.\n\n"
                "**If you use a wrong format, use `!welcome` again to see the correct commands.**"
            ),
            color=discord.Color.red(),
        )
        return embed

    @commands.hybrid_group(name="welcome", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        await ctx.send(embed=self.help_embed())

    @welcome.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_cmd(self, ctx, channel: discord.TextChannel):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, channel_id=channel.id, enabled=True)
        await ctx.send(f"✅ Welcome system set to {channel.mention}.")

    @welcome.command(name="confirm")
    @commands.has_permissions(administrator=True)
    async def confirm_cmd(self, ctx):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, channel_id=ctx.channel.id, enabled=True)
        await ctx.send(f"✅ Welcome system confirmed in {ctx.channel.mention}.")

    @welcome.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def disable_cmd(self, ctx):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        result = await self.welcome_col.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"enabled": False}},
        )
        if result.matched_count:
            await ctx.send("🗑️ Welcome system disabled. Your settings are kept in MongoDB.")
        else:
            await ctx.send("⚠️ No welcome setup found.")

    @welcome.command(name="image")
    @commands.has_permissions(administrator=True)
    async def image_cmd(
        self,
        ctx,
        url: Optional[str] = None,
        attachment: Optional[discord.Attachment] = None,
    ):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        image_url = attachment.url if attachment else url
        if not image_url:
            return await ctx.send(
                "❌ Image missing! Use `!welcome image <image link>` or attach an image."
            )
        await self.save(ctx.guild.id, image_url=image_url)
        await ctx.send("✅ Welcome image updated successfully.")

    @welcome.command(name="memberscount")
    @commands.has_permissions(administrator=True)
    async def memberscount_cmd(self, ctx, mode: str):
        mode = mode.lower()
        if mode not in ("on", "off"):
            return await ctx.send("❌ Wrong option. Use: `!welcome memberscount on` or `off`.")
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, memberscount=(mode == "on"))
        await ctx.send(f"✅ Welcome member count: **{mode.upper()}**")

    @welcome.command(name="account")
    @commands.has_permissions(administrator=True)
    async def account_cmd(self, ctx, mode: str):
        mode = mode.lower()
        if mode not in ("on", "off"):
            return await ctx.send("❌ Wrong option. Use: `!welcome account on` or `off`.")
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, account_age=(mode == "on"))
        await ctx.send(f"✅ Account age in welcome: **{mode.upper()}**")

    @welcome.command(name="text")
    @commands.has_permissions(administrator=True)
    async def text_cmd(self, ctx, *, text: str):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, description=text)
        await ctx.send("✅ Welcome text updated successfully.")

    @welcome.command(name="logs")
    @commands.has_permissions(administrator=True)
    async def logs_cmd(self, ctx, channel: discord.TextChannel):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, log_channel_id=channel.id, logs_enabled=True)
        await ctx.send(f"✅ Welcome logs set to {channel.mention}.")

    @welcome.group(name="log", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def log_group(self, ctx):
        await ctx.send("Use `!welcome log disable` to remove the welcome log setup.")

    @log_group.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def log_disable_cmd(self, ctx):
        if self.welcome_col is None:
            return await ctx.send("❌ MongoDB connection error! Check your MONGO_URI.")
        await self.save(ctx.guild.id, logs_enabled=False)
        await ctx.send("🗑️ Welcome log setup disabled.")

    async def find_inviter(self, guild: discord.Guild):
        """Find the invite whose use count increased. Requires Manage Server/View Audit Log as applicable."""
        try:
            invites = await guild.invites()
        except Exception:
            return None

        old = self.invite_cache.get(guild.id, {})
        new = {inv.code: inv.uses or 0 for inv in invites}
        self.invite_cache[guild.id] = new

        for inv in invites:
            previous = old.get(inv.code, 0)
            current = inv.uses or 0
            if current > previous:
                return inv.inviter
        return None

    async def cache_guild_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
            self.invite_cache[guild.id] = {i.code: (i.uses or 0) for i in invites}
        except Exception:
            self.invite_cache[guild.id] = {}

    async def send_welcome_embed(self, member: discord.Member, channel, data, inviter=None):
        server_name = member.guild.name or "your"
        raw_desc = data.get("description") or DEFAULT_WELCOME_TEXT
        formatted_desc = (
            raw_desc.replace("{user}", member.mention)
            .replace("{server}", server_name)
            .replace("{count}", str(member.guild.member_count or 0))
        )

        embed = discord.Embed(
            title="",
            description=f"# 🎉 WELCOME 🎉 #\n\n{formatted_desc}",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        image_url = data.get("image_url") or DEFAULT_WELCOME_IMAGE
        if image_url:
            embed.set_image(url=image_url)

        if data.get("memberscount"):
            embed.add_field(name="👥 Members", value=f"{member.guild.member_count:,}", inline=True)
        if data.get("account_age"):
            embed.add_field(
                name="📅 Account Created",
                value=f"{discord.utils.format_dt(member.created_at, 'R')}\n{human_time(member.created_at)} ago",
                inline=True,
            )

        await channel.send(content=member.mention, embed=embed)

    async def send_log(self, member: discord.Member, log_channel, inviter=None):
        user = member
        try:
            fetched = await self.bot.fetch_user(member.id)
            banner_url = fetched.banner.url if fetched.banner else None
        except Exception:
            banner_url = None

        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"{member.mention} joined **{member.guild.name}**.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Username", value=f"{user}\\n`{user.id}`", inline=False)
        embed.add_field(
            name="📅 Account Created",
            value=f"{discord.utils.format_dt(user.created_at, 'F')}\\n**{human_time(user.created_at)} ago**",
            inline=False,
        )
        embed.add_field(
            name="🔗 Invited By",
            value=inviter.mention if inviter else "Unknown / invite tracking unavailable",
            inline=True,
        )
        embed.add_field(name="👥 Server Members", value=f"{member.guild.member_count:,}", inline=True)
        if banner_url:
            embed.set_image(url=banner_url)
        else:
            embed.add_field(name="🖼️ Profile Banner", value="No profile banner", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.welcome_col is None:
            return
        data = await self.get_settings(member.guild.id)
        if not data or not data.get("enabled", True):
            return

        inviter = await self.find_inviter(member.guild)

        channel_id = data.get("channel_id")
        channel = member.guild.get_channel(int(channel_id)) if channel_id else None
        if channel:
            try:
                await self.send_welcome_embed(member, channel, data, inviter)
            except Exception as e:
                print(f"[Welcome] Send Error: {e}")

        if data.get("logs_enabled") and data.get("log_channel_id"):
            log_channel = member.guild.get_channel(int(data["log_channel_id"]))
            if log_channel:
                try:
                    await self.send_log(member, log_channel, inviter)
                except Exception as e:
                    print(f"[Welcome Logs] Send Error: {e}")

    async def cog_command_error(self, ctx, error):
        error = getattr(error, "original", error)
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("❌ You need **Administrator** permission to use welcome commands.")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                "❌ Something is missing. Use `!welcome` to see all correct commands and examples."
            )
        if isinstance(error, commands.BadArgument):
            return await ctx.send(
                "❌ Invalid argument. Make sure you tag a real channel, e.g. `!welcome setup #welcome`.\n"
                "Use `!welcome` for all command details."
            )
        print(f"[Welcome Command Error] {error}")


async def setup(bot):
    await bot.add_cog(Welcome(bot))

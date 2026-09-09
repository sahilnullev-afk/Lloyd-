import discord
from discord.ext import commands
import config

RED = discord.Color.red()
GAME_IMAGE_URL = "https://cdn.discordapp.com/attachments/1541151143516835861/1547296509157179422/4483361f3241f14b269a4dc168756d41.jpg?ex=6aa2e7ab&is=6aa1962b&hm=e3ebdc47e29641192c31035f02e25a3ef7941e74fc8a2314012ce9a3cc6cbfbe&"

PUBLIC_PAGES = [
    ("Home", "**Javer Bot Help**\n\nUse the dropdown below to jump to any page.\n\n**Pages**\n`2` Moderation\n`3` Protection\n`4` Logging & Trackers\n`5` Voice\n`6` Music\n`7` Roles & Cards\n`8` Welcome & Automation\n`9` Utility\n`10` Fun & Games\n`11` Character Game\n`12` Imposter\n`13` Premium\n\nAll commands use the bot prefix configured in your server. Example: `!help`"),
    ("Moderation", "**Moderation Commands**\n\n`!kick @user` — Kick a member.\n`!ban @user` — Ban a member.\n`!clear <amount>` — Delete messages. Alias: `!purge`\n`!change nick @user <name>` — Change a member nickname.\n`!mute @user` — Server-mute a member.\n`!def @user` — Server-deafen a member.\n`!move @user <channel>` — Move a member to a voice channel.\n`!roleg @user <role>` — Give a role to a member.\n`!serverinfo` — Show server information. Alias: `!si`\n\n**Note:** `!spam` and `!spamstop` are owner/private commands and are intentionally hidden from public help."),
    ("Protection", "**Anti-Nuke Protection**\n\n`!antinuke` / `!nuke` — Open Anti-Nuke controls.\n`!antinuke spam` — Configure spam protection.\n`!antinuke spamdel` — Remove spam protection.\n`!antinuke url action` — Configure URL action.\n`!antinuke urldel` — Remove URL protection.\n`!antinuke ban` — Configure ban protection.\n`!antinuke bandel` — Remove ban protection.\n`!antinuke app` — Configure app/bot protection.\n`!antinuke whitelist @user` — Whitelist a user. Alias: `!antinuke wl`\n`!antinuke unwhitelist @user` — Remove whitelist. Alias: `!antinuke unwl`\n`!whitelistuser @user` — Anti-Nuke user whitelist control.\n`!antinuke logs` — Configure protection logs.\n`!antinuke logsdel` — Remove protection logs.\n`!antinuke list` — View protection settings.\n`!antinuke resetall` — Reset Anti-Nuke settings.\n\nMost protection controls require Administrator permission."),
    ("Logging & Trackers", "**Logging**\n`!log` — Open logging controls.\n`!log setup` — Configure moderation/event logs.\n\n**Message Tracker**\n`!msg` — Open message tracker.\n`!msg top` — Show message leaderboard.\n`!msg help` — Message tracker help.\n`!msgw` — Weekly message tracker.\n`!msgw top` — Show weekly leaderboard.\n\n**Voice Tracker**\n`!vc` — Open voice tracker.\n`!vc top` — Show voice leaderboard.\n`!vc help` — Voice tracker help.\n`!vcw` — Weekly voice tracker.\n`!vcw top` — Show weekly leaderboard."),
    ("Voice", "**Voice Helper**\n\n`!vcall` — Voice call helper.\n`!pull @user` — Pull a member to your voice channel.\n`!vcm` — Open voice moderation controls.\n`!vcm help` — Show voice moderation help. Alias: `!vcm h`\n`!vcm drag @user` — Move a member.\n`!vcm mute @user` — Server-mute a member.\n`!vcm unmute @user` — Unmute a member.\n`!vcm def @user` — Server-deafen a member. Alias: `!vcm deaf`\n`!vcm undef @user` — Undeafen a member. Alias: `!vcm undeaf`\n`!vcm kick @user` — Disconnect a member from voice."),
    ("Music", "**Music Commands**\n\n`!play <song/url>` / `!p` — Play music.\n`!join` — Join your voice channel.\n`!leave` — Leave the voice channel.\n`!stop` — Stop playback.\n`!queue` — View the music queue.\n`!vol <1-200>` — Change volume.\n\n`!join`, `!leave`, `!stop`, `!queue`, and `!vol` are reserved for the music system and can be added when those commands are implemented."),
    ("Roles & Cards", "**Role Manager**\n\n`!role` — Open role manager.\n`!role help` — Role manager help.\n`!role menu` — Open the role menu.\n`!role add` — Add a role.\n`!role remove` — Remove a role.\n`!role perms` — View role permissions.\n`!role members` — View role members.\n`!role delete` — Delete a role.\n`!role plan create` — Create a role plan.\n`!role plan add` — Add to a role plan.\n`!role plan details` — View plan details.\n`!role plan list` — List role plans.\n`!role plan delete` — Delete a role plan.\n`!role paste` — Paste a saved role setup.\n`!role all` — Manage all roles.\n`!role humans` — Manage human roles.\n`!role bots` — Manage bot roles.\n`!role removeall` — Remove managed roles.\n`!role autorole human` — Configure human autorole.\n`!role autorole bot` — Configure bot autorole.\n\n**Profile Cards**\n`!card` — Open card/profile controls.\n`!card role male` — Set/select male card role.\n`!card role female` — Set/select female card role."),
    ("Welcome & Automation", "**Welcome System**\n\n`!welcome` — Open welcome settings.\n`!welcome setup` — Configure the welcome channel.\n`!welcome msg` — Set the welcome message.\n`!welcome image` — Configure the welcome image.\n`!welcome reset` — Reset welcome settings.\n`!welcome test` — Test the welcome message.\n\n**AutoSend**\n`!autosend` — Open AutoSend.\n`!autosend help` — AutoSend help.\n`!autosendoff` — Disable AutoSend.\n\n**AutoResponse**\n`!autoresponse` / `!autoadd` — Add/manage auto responses.\n`!autorec` / `!autoreaction` — Add an auto reaction.\n`!autorecdel` — Delete an auto reaction.\n`!autodel` — Delete an auto response.\n`!autolist` — List auto responses."),
    ("Utility", "**Utility Commands**\n\n`!av @user` / `!avatar` / `!pfp` — Show a user's avatar.\n`!banner @user` — Show a user's banner.\n`!serverpfp` — Manage the bot's server profile picture.\n`!servernick` — Manage the bot's server nickname.\n`!serverb` / `!serverbanner` — Manage the bot's server banner.\n\nSome server customization features may require Premium access."),
    ("Fun & Games", "**Fun**\n\n`!roast @user` — Roast a member.\n`!flirt @user` — Fun flirt command.\n`!motivation` — Get a motivational message.\n\n**Games**\n`!xo` — Play Tic-Tac-Toe.\n`!kingdom` — Start the Kingdom game.\n\n**GIF Actions**\n`!slap @user` — Slap GIF.\n`!kiss @user` — Kiss GIF.\n`!hug @user` — Hug GIF.\n`!punch @user` — Punch GIF.\n`!boss @user` — Boss GIF.\n\nUse these commands responsibly and keep interactions friendly."),
    ("Character Game", "**Character / RPG System**\n\n`!c` — Open the Character Game.\n`!c profile` / `!c p` — View your profile.\n`!c lvl` / `!c l` — View your level.\n`!c edit` / `!c e` — Edit your character.\n`!c edit name` / `!c edit n` — Edit character name.\n`!c edit image` / `!c edit i` — Edit character image.\n`!c hunt` / `!c h` — Hunt for rewards.\n`!c huntauto` / `!c ha` — Auto-hunt.\n`!c battle` / `!c b` — Start a battle.\n`!c battle all` / `!c battle a` — Battle all.\n`!c raid` — Open raid controls.\n`!c raid spawn` — Raid setup.\n`!c raid start` — Start a raid.\n`!c team` — Team controls.\n`!c team create` — Create a team.\n`!c team room` — Team room controls.\n`!c shop` — Open the shop.\n`!c buy` — Buy an item.\n`!c top` / `!c t` — View the leaderboard."),
    ("Imposter", "**Imposter Game**\n\n`!imposter` — Start an Imposter game.\n`!next` — Continue to the next round/player.\n`!impoend` — End the current Imposter game.\n`!impohelp` — Show Imposter game help."),
    ("Premium", "**Premium**\n\nPremium unlocks additional bot features and permissions.\n\n**Important:** Premium is required for a custom bot server PFP. The link to get Premium is available in the bot bio.\n\nTo get Premium, join the server using the link in the bot bio.\n\nPremium management commands are private and are not shown in public help."),
]

OWNER_PAGES = [
    ("Owner Home", "**Bot Owner Help**\n\nThis menu is visible only to the Bot Owner.\n\n**Owner Tools**\n`!pcreate` / `!pp` — Create a Premium plan.\n`!pcommand` — Add a command permission to a Premium plan.\n`!pgive user` — Give Premium to a user.\n`!pgive server` — Give Premium to a server.\n`!pgive su` — Give server/user Premium access.\n`!plist` — List Premium holders/plans.\n`!phelp` — Premium management help.\n\n**Private Moderation**\n`!spam` — Start the private spam tool.\n`!spamstop` — Stop the private spam tool.\n\n**Character Owner Tools**\n`!c ohelp` / `!c ownerhelp` / `!c owner` — Character owner menu.\n`!c ban server` — Ban RPG in a server.\n`!c unban server` — Unban RPG in a server.\n`!c pban @user` — Permanently ban a user from RPG.\n`!c punban @user` — Remove an RPG permanent ban."),
    ("Premium Admin", "**Premium Management**\n\n`!pcreate <plan>` / `!pp <plan>` — Create a Premium plan with the permission selector.\n`!pcommand <plan> <permission>` — Add a permission to an existing plan.\n`!pgive user @user <time> <plan>` — Give Premium to a user.\n`!pgive server <plan> [time]` — Give Premium to the current server.\n`!pgive su @user <plan> [time]` — Give server/user Premium access.\n`!plist` — View Premium data.\n`!phelp` — Open Premium system help."),
    ("Private Tools", "**Private Owner Tools**\n\n`!spam` — Private spam command.\n`!spamstop` — Stop the private spam process.\n\n**Character Game Owner Controls**\n`!c ohelp` / `!c ownerhelp` / `!c owner` — Owner menu.\n`!c ban server` — Disable RPG in the current server.\n`!c unban server` — Enable RPG in the current server.\n`!c pban @user` — Permanently ban a user from RPG.\n`!c punban @user` — Remove the RPG ban.\n\nThese commands should never be exposed through the normal `!help` menu."),
]


class PageSelect(discord.ui.Select):
    def __init__(self, view, pages):
        options = [discord.SelectOption(label=f"Page {i + 1} — {title}", value=str(i)) for i, (title, _) in enumerate(pages)]
        super().__init__(placeholder="Select a page...", min_values=1, max_values=1, options=options, row=1)
        self.help_view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.help_view.user_id:
            return await interaction.response.send_message("This help menu belongs to another user.", ephemeral=True)
        self.help_view.page = int(self.values[0])
        self.help_view.refresh()
        await interaction.response.edit_message(embed=self.help_view.embed(), view=self.help_view)


class HelpView(discord.ui.View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=180)
        self.user_id = ctx.author.id
        self.pages = pages
        self.page = 0
        self.select = PageSelect(self, pages)
        self.add_item(self.select)
        self.refresh()

    def embed(self):
        title, description = self.pages[self.page]
        embed = discord.Embed(title=title, description=description, color=RED)
        if title == "Character Game" and GAME_IMAGE_URL:
            embed.set_image(url=GAME_IMAGE_URL)
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)} • Javer Bot")
        return embed

    def refresh(self):
        self.select.options = [
            discord.SelectOption(label=f"Page {i + 1} — {title}", value=str(i), default=(i == self.page))
            for i, (title, _) in enumerate(self.pages)
        ]
        self.back.disabled = self.page == 0
        self.next.disabled = self.page == len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This help menu belongs to another user.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        self.refresh()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=2)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
        self.refresh()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help_command(self, ctx):
        view = HelpView(ctx, PUBLIC_PAGES)
        await ctx.send(embed=view.embed(), view=view)

    @commands.hybrid_command(name="ohelp")
    async def owner_help_command(self, ctx):
        owner_id = getattr(config, "OWNER_ID", None)
        if owner_id is None or ctx.author.id != int(owner_id):
            return await ctx.send("❌ **Access Denied!** This command is restricted to the Bot Owner.")
        view = HelpView(ctx, OWNER_PAGES)
        await ctx.send(embed=view.embed(), view=view)


async def setup(bot):
    await bot.add_cog(Help(bot))

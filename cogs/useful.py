import asyncio
import datetime
import json
import pathlib
import platform
import random
import re
import time
from collections import Counter

import aiohttp
import discord
import humanize
import psutil
from discord.ext import commands, menus

from utils.default import qembed


class ChuckContext(commands.Context):

    @property
    def secret(self):
        return 'my secret here'

    async def confirm(self, text: str = 'Are you sure you want to do this?'):
        message = await self.send(text)
        await message.add_reaction('✅')
        await message.add_reaction('❌')

        def terms(reaction, user):
            return user == self.author and str(reaction.emoji) == '✅' or user == self.author and str(
                reaction.emoji) == '❌'

        try:
            reaction, _ = await self.bot.wait_for('reaction_add',
                                                  timeout=15,
                                                  check=terms)
        except asyncio.TimeoutError:
            return False, message
        else:
            if reaction.emoji == '✅':
                return True, message
            if reaction.emoji == '❌':
                return False, message

    async def mystbin(self, data):
        data = bytes(data, 'utf-8')
        async with aiohttp.ClientSession() as cs:
            async with cs.post('https://mystb.in/documents', data=data) as r:
                res = await r.json()
                key = res["key"]
                return f"https://mystb.in/{key}"

    async def remove(self, *args, **kwargs):
        m = await self.send(*args, **kwargs)
        await m.add_reaction("❌")
        try:
            await self.bot.wait_for('reaction_add',
                                    timeout=120,
                                    check=lambda r, u: u.id == self.author.id and r.message.id == m.id and str(
                                        r.emoji) == str("❌"))
            await m.delete()
        except asyncio.TimeoutError:
            pass

    def embed(self, **kwargs):
        color = kwargs.pop("color", self.bot.embed_color)
        embed = discord.Embed(**kwargs, color=color)
        embed.timestamp = self.message.created_at
        embed.set_footer(text=f"Requested by {self.author}", icon_url=self.author.avatar_url)
        return embed

    def escape(self, text: str):
        mark = [
            '`',
            '_',
            '*'
        ]
        for item in mark:
            text = text.replace(item, f'\u200b{item}')
        return text

    # https://github.com/InterStella0/stella_bot/blob/master/utils/useful.py#L199-L205
    def plural(self, text, size):
        logic = size == 1
        target = (("(s)", ("s", "")), ("(is/are)", ("are", "is")))
        for x, y in target:
            text = text.replace(x, y[logic])
        return text


class TodoSource(menus.ListPageSource):
    def __init__(self, todos):
        discord_match = re.compile(r"https?:\/\/(?:(?:ptb|canary)\.)?discord(?:app)?\.com"
                                   r"\/channels\/[0-9]{15,19}"
                                   r"\/[0-9]{15,19}\/[0-9]{15,19}\/?")
        url_match = re.compile(r"http[s]?:\/\/(?:[a-zA-Z0-9.])+")
        tod=[]
        for todo in todos:
            text = todo['todo']
            if d_match := discord_match.match(text):
                text = text.replace(d_match[0], f"[`[jump link]`]({d_match[0]})")
            tod.append(f"`[[{todo['row_number']}]]({todo['jump_url']})` {text}")
        super().__init__(tod, per_page=10)

    async def format_page(self, menu, pages):
        return menu.ctx.embed(
            title=f"{menu.ctx.author.name}'s todo list | Page {menu.current_page + 1}/{self.get_max_pages()}",
            description="\n".join(pages),
        )


class TodoPages(menus.MenuPages):

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f', position=menus.Last(2))
    async def end_menu(self, _):
        self.message.delete()
        self.stop()


class Useful(commands.Cog, command_attrs=dict(hidden=False)):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['information', 'botinfo'],
                      help='Gets info about the bot')
    async def info(self, ctx):
        msg = await ctx.send('Getting bot information ...')
        average_members = sum([guild.member_count
                               for guild in self.bot.guilds]) / len(self.bot.guilds)
        cpu_usage = psutil.cpu_percent()
        cpu_freq = psutil.cpu_freq().current
        ram_usage = humanize.naturalsize(psutil.Process().memory_full_info().uss)
        hosting = platform.platform()

        p = pathlib.Path('./')
        ls = 0
        for f in p.rglob('*.py'):
            if str(f).startswith("venv"):
                continue
            with f.open() as of:
                for _ in of.readlines():
                    ls += 1

        emb = discord.Embed(description=self.bot.description, colour=self.bot.embed_color,
                            timestamp=ctx.message.created_at).set_footer(text=f"Requested by {ctx.author}",
                                                                         icon_url=ctx.author.avatar_url)
        emb.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        emb.add_field(name='Developer', value=f'```ppotatoo#9688 ({self.bot.author_id})```', inline=False)
        emb.add_field(name='Line Count', value=f'```{ls:,} lines```', inline=True)
        emb.add_field(name='Command Count', value=f'```{len(set(self.bot.walk_commands())) - 31} commands```',
                      inline=True)
        emb.add_field(name='Guild Count', value=f'```{str(len(self.bot.guilds))} guilds```', inline=True)
        emb.add_field(name='CPU Usage', value=f'```{cpu_usage:.2f}%```', inline=True)
        emb.add_field(name='CPU Frequency', value=f'```{cpu_freq} MHZ```', inline=True)
        emb.add_field(name='Memory Usage', value=f'```{ram_usage}```', inline=True)
        emb.add_field(name='Hosting', value=f'```{hosting}```', inline=False)
        emb.add_field(name='Member Count',
                      value=f'```{str(sum([guild.member_count for guild in self.bot.guilds]))} members```', inline=True)
        emb.add_field(name='Average Member Count', value=f'```{average_members:.0f} members per guild```')

        await msg.edit(content=None, embed=emb)

    @commands.command(name='ping', help='only for cool kids')
    async def ping(self, ctx):
        start = time.perf_counter()
        message = await ctx.send("Pinging ...")
        duration = (time.perf_counter() - start) * 1000
        poststart = time.perf_counter()
        await self.bot.db.fetch("SELECT 1")
        postduration = (time.perf_counter() - poststart) * 1000
        pong = discord.Embed(title='Ping', color=self.bot.embed_color, timestamp=ctx.message.created_at).set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar_url)
        pong.add_field(name='Typing Latency',
                       value=f'```python\n{round(duration)} ms```', inline=False)
        pong.add_field(
            name='Websocket Latency',
            value=f'```python\n{round(self.bot.latency * 1000)} ms```', inline=False)
        pong.add_field(name='SQL Latency',
                       value=f'```python\n{round(postduration)} ms```', inline=False)
        await message.edit(content=None, embed=pong)

    @commands.command(help='Shows how long the bot has been online for')
    async def uptime(self, ctx):
        uptime = humanize.precisedelta(self.bot.uptime - datetime.datetime.utcnow(), format='%0.0f')
        await ctx.send(embed=ctx.embed(description=f"I've been up for {uptime}"))

    @commands.command(aliases=['a', 'pfp'])
    async def avatar(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author
        ava = ctx.embed(title=f'{user.name}\'s avatar:')
        types = [
            f"[{type}]({str(user.avatar_url_as(format=type))})"
            for type in ["webp", "png", "jpeg", "jpg"]
        ]

        if user.is_avatar_animated():
            types.append(f"[gif]({str(user.avatar_url_as(format='gif'))})")
        ava.description = " | ".join(types)
        ava.set_image(url=user.avatar_url)
        await ctx.send(embed=ava)

    @commands.command(help='Searches PyPI for a Python Package')
    async def pypi(self, ctx, package: str):
        async with self.bot.session.get(f'https://pypi.org/pypi/{package}/json') as f:
            if not f or f.status != 200:
                return await ctx.send(embed=ctx.embed(description='Package not found.'))
            package = await f.json()
        data = package.get("info")
        embed = ctx.embed(title=f"{data.get('name')} {data['version'] or ''}",
                          url=data.get('project_url', 'None provided'),
                          description=data["summary"] or "None provided")
        embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/381963689470984203/814267252437942272/pypi.png')
        embed.add_field(name='Author Info:', value=f'**Author Name**: `{data["author"] or "None provided"}`\n'
                                                   f'**Author Email**: `{data["author_email"] or "None provided"}`')
        urls = data.get("project_urls", "None provided")
        embed.add_field(name='Package Info:',
                        value=f'**Documentation**: `{urls.get("Documentation", "None provided")}`\n'
                              f'**Homepage**: `{urls.get("Homepage", "None provided")}`\n'
                              f'**Keywords**: `{data["keywords"] or "None provided"}`\n'
                              f'**License**: `{data["license"] or "None provided"}`',
                        inline=False)
        await ctx.send(embed=embed)

    @commands.command(help='Checks if your message is toxic or not.')
    async def toxic(self, ctx, *, text):
        url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={self.bot.perspective}"

        headers = {'Content-Type': 'application/json', }

        data = f'{{comment: {{text: "{text}"}}, ' \
               'languages: ["en"], ' \
               'requestedAttributes: {TOXICITY:{}} }'

        res = await self.bot.session.post(url, headers=headers, data=data)
        js = await res.json()

        level = js["attributeScores"]["TOXICITY"]["summaryScore"]["value"] * 100
        await ctx.send(f"`{text}` is `{level:.2f}%` likely to be toxic.")

    @commands.command(help='Builds an embed from a dict. You can use https://eb.nadeko.bot/ to get one',
                      brief='Builds an embed', aliases=['make_embed', 'embed_builder'])
    async def embedbuilder(self, ctx, *, embed: json.loads):
        try:
            await ctx.send(embed=discord.Embed().from_dict(embed))
        except:
            await qembed(ctx, 'You clearly don\'t know what this is')

    @commands.command(help='Invites the bot to your server')
    async def invite(self, ctx):
        invite = ctx.embed(title='Invite me to your server:', description=self.bot.invite)
        invite.add_field(name='You can also join the support server:', value=self.bot.support_invite)
        await ctx.send(embed=invite)

    @commands.command(help='An invite link to the bot support server.')
    async def support(self, ctx):
        await ctx.send(embed=ctx.embed(title='Support server invite:', description='https://discord.gg/NTNgvHkjSp'))

    @commands.command(help='Sends the 5 most recent commits to the bot.')
    async def recent_commits(self, ctx):
        async with self.bot.session.get('https://api.github.com/repos/ppotatoo/Penguin/commits') as f:
            resp = await f.json()
        embed = ctx.embed(description="\n".join(
            f"[`{commit['sha'][:6]}`]({commit['html_url']}) {commit['commit']['message']}" for commit in resp[:5])
        )
        await ctx.send(embed=embed)

    @commands.command(help='Suggests a feature to the developers!')
    async def suggest(self, ctx, *, suggestion):
        support = self.bot.get_channel(818246475867488316)
        await support.send(embed=ctx.embed(title='New Suggestion:',
                                           description=f"```\n{ctx.escape(suggestion)}```\n[**JUMP URL**]({ctx.message.jump_url})"))
        await ctx.send(embed=ctx.embed(description='Your suggestion has been sent! '))

    @commands.command(help='Pretty-Prints some JSON')
    async def pprint(self, ctx, *, data: str):
        try:
            data = data.replace("'", '"')
            await ctx.send(f"```json\n{ctx.escape(json.dumps(json.loads(data), indent=4))}```")
        except json.JSONDecodeError:
            await ctx.send('Nice, you provided invalid JSON. Good work.')

    @commands.command(help='Chooses the best choice.')
    async def choose(self, ctx, choice_1, choice_2):
        choice = Counter(random.choice([choice_1, choice_2]) for _ in range(1500))
        answer = max(choice[choice_1], choice[choice_2])
        result = sorted(choice, key=lambda e: e == answer)
        await ctx.send(f'{result[0]} won with {answer} votes and {answer / 1500:.2f}% of the votes')

    @commands.group()
    async def todo(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help(str(ctx.command))

    @todo.command()
    async def list(self, ctx):
        sql = (
            "SELECT DISTINCT todo, sort_date, jump_url, "
            "ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos "
            "WHERE user_id = $1 ORDER BY sort_date"
        )
        todos = await self.bot.db.fetch(sql, ctx.author.id)


        pages = TodoPages(source=TodoSource(todos))

        await pages.start(ctx)

    @todo.command()
    async def add(self, ctx, *, task: str):
        sql = (
            "INSERT INTO TODOS (user_id, todo, sort_date, jump_url) "
            "VALUES ($1, $2, $3, $4)"
        )
        await self.bot.db.execute(sql, ctx.author.id, task, datetime.datetime.utcnow(), ctx.message.jump_url)
        await ctx.send(embed=ctx.embed(title="Inserted into your todo list...", description=task))

    @todo.command()
    async def remove(self, ctx, numbers: commands.Greedy[int]):
        sql = (
            "SELECT DISTINCT todo, sort_date, "
            "ROW_NUMBER () OVER (ORDER BY sort_date) FROM todos "
            "WHERE user_id = $1 ORDER BY sort_date"
        )
        todos = await self.bot.db.fetch(sql, ctx.author.id)
        for number in numbers:
            if number > len(todos):
                return await ctx.send("You can't delete a task you don't have.")
        delete = (
            "DELETE FROM todos "
            "WHERE user_id = $1 AND todo = ANY ($2)"
        )
        to_delete = [todos[num - 1]["todo"] for num in numbers]
        await self.bot.db.execute(delete, ctx.author.id, tuple(to_delete))

        desc = "\n".join(f"`{todos[num - 1]['row_number']}` - {todos[num - 1]['todo']}" for num in numbers)
        task = ctx.plural('task(s)', len(numbers))
        embed = ctx.embed(title=f"Removed {humanize.apnumber(len(numbers))} {task}:",
                          description=desc)
        await ctx.send(embed=embed)


class AAAAAA(commands.Cog):
    def init(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def asdfasdfasdfasdfasdfasdfadsfasdf(self, ctx):
        await ctx.send(1 + 2)


def setup(bot):
    bot.add_cog(Useful(bot))
    bot.add_cog(AAAAAA(bot))

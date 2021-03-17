import discord
from discord.ext import commands
from cogs.polaroid_manipulation import get_image_url
import typing


class Images(commands.Cog):
    """Some fun image commands."""
    def __init__(self, bot):
        self.bot = bot

    async def do_alex_image(self, ctx, method, args: list = [], kwargs: dict = {}):
        alex = getattr(self.bot.alex, method)
        m = await alex(*args, **kwargs)
        file = discord.File(await m.read(), filename=f"{method}.png")
        embed = ctx.embed()
        embed.set_image(url=f"attachment://{method}.png")
        await ctx.send(embed=embed, file=file)

    @commands.command()
    async def amiajoke(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        """Creates a "Am I a joke?" meme."""
        await self.do_alex_image(ctx, method="amiajoke", args=[await get_image_url(ctx, image)])

    @commands.command()
    async def animeface(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        async with self.bot.session.get("https://nekobot.xyz/api/imagegen?type=animeface&image=%s" % await get_image_url(ctx, image)) as resp:
            data = await resp.json()
        await ctx.send(data)
    

def setup(bot):
    bot.add_cog(Images(bot))
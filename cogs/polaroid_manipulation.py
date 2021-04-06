"""
Copyright (C) 2021 ppotatoo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import re
import typing
from io import BytesIO

import discord
import polaroid
from discord.ext import commands
from jishaku.functools import executor_function


async def get_image_object(ctx, image):
    if ctx.message.attachments:
        img = await ctx.message.attachments[0].read()

    elif isinstance(image, discord.PartialEmoji):
        img = await image.url.read()

    elif isinstance(image, (discord.Member, discord.User)):
        img = await image.avatar_url_as(format="png").read()

    elif image is None:
        img = await ctx.author.avatar_url_as(format="png").read()
    else:
        url = str(image).strip("<>")
        if re.match(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", url):
            async with ctx.bot.session.get(url) as resp:
                if resp.headers["Content-type"].startswith("image"):
                    img = await resp.read()
                else:
                    img = None
        else:
            img = None
    if not img:
        img = await ctx.author.avatar_url_as(format="png").read()
    return img


async def get_image_url(ctx, image):
    if ctx.message.attachments:
        img = ctx.message.attachments[0].proxy_url

    elif isinstance(image, discord.PartialEmoji):
        img = image.url

    elif isinstance(image, (discord.Member, discord.User)):
        img = image.avatar_url

    elif image is None:
        img = ctx.author.avatar_url
    else:
        url = str(image).strip("<>")
        if re.match(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", url):
            async with ctx.bot.session.get(url) as resp:
                img = url if resp.headers["Content-type"].startswith("image") else None
        else:
            img = None
    if not img:
        img = ctx.author.avatar_url
    return img


class Polaroid(commands.Cog, command_attrs=dict(hidden=False)):
    def __init__(self, bot):
        self.bot = bot

    @executor_function
    def do_polaroid(self, img, method: str, args: list = None, kwargs: dict = None):
        img = polaroid.Image(img)
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        method = getattr(img, method)
        method(*args, **kwargs)
        return img

    async def send_polaroid(self, ctx, image, method: str, *args, **kwargs):
        try:
            image = await get_image_object(ctx, image)
        except:
            await ctx.send(embed=ctx.embed(description='Invalid URL provided.'))
        img = await self.do_polaroid(image, method, *args, **kwargs)
        file = discord.File(BytesIO(img.save_bytes()),
                            filename=f"{method}.png")

        embed = ctx.embed()
        embed.set_image(url=f"attachment://{method}.png")
        await ctx.send(embed=embed, file=file)

    @commands.command(help='Makes an image rainbowey')
    async def rainbow(self, ctx, *,
                      image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='apply_gradient')

    @commands.command(help='like putin')
    async def wide(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='resize', args=(2000, 900, 1))

    @commands.command(help='Inverts an image')
    async def invert(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='invert')

    @commands.command(help='It\'s like looking in a mirror')
    async def flip(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='fliph')

    @commands.command(aliases=['colourize'], help='Colorizes an image.')
    async def colorize(self, ctx, *,
                       image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='colorize')

    @commands.command(help='Blurs an image? Duh')
    async def blur(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='box_blur')

    @commands.command(help='cursed')
    async def sobelh(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='sobel_horizontal')

    @commands.command(help='cursed')
    async def sobelv(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='sobel_vertical')

    @commands.command(help='Decomposes the image')
    async def decompose(self, ctx, *,
                        image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='decompose_max')

    @commands.command(help='Turns an image black and white')
    async def grayscale(self, ctx, *,
                        image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='grayscale')

    @commands.command(help='Solarizes an image')
    async def solarize(self, ctx, *,
                       image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='solarize')

    @commands.command(help='Rotates an image sideways')
    async def sideways(self, ctx, *,
                       image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='rotate90')

    @commands.command(help='Rotates an image upsidedown')
    async def upsidedown(self, ctx, *,
                         image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='rotate180')

    @commands.command(help='Makes an image monochrome.')
    async def monochrome(self, ctx, *,
                         image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='monochrome')

    @commands.command(help='Applies an emboss effect to an image.')
    async def emboss(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='emboss')

    @commands.command(help='Applies an edges effect to an image.')
    async def edges(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='edge_detection')

    @commands.command(help='Applies an oil effect to an image.')
    async def oil(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='oil', args=[4, 55])

    @commands.group(help='Some commands that apply simple filters.')
    async def filter(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @filter.command(help='Applies a rose filter on an image.')
    async def rose(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["rosetint"])

    @filter.command(help='Applies a pink filter to the image.')
    async def pink(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["pastel_pink"])

    @filter.command(help='Applies a liquid filter to the image.')
    async def liquid(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["liquid"])

    @filter.command(help='Applies a dramatic filter to the image.')
    async def dramatic(self, ctx, *,
                       image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["dramatic"])

    @filter.command(help='Applies a firenze filter to the image.')
    async def firenze(self, ctx, *,
                      image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["firenze"])

    @filter.command(help='Applies a golden filter to the image.')
    async def golden(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["golden"])

    @filter.command(help='Applies a lix filter to the image.')
    async def lix(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["lix"])

    @filter.command(help='Applies a neue filter to the image.')
    async def neue(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["neue"])

    @filter.command(help='Applies an obsidian filter to the image.')
    async def obsidian(self, ctx, *,
                       image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["obsidian"])

    @filter.command(help='Applies a ryo filter to the image.')
    async def ryo(self, ctx, *, image: typing.Union[discord.PartialEmoji, discord.Member, discord.User, str] = None):
        await self.send_polaroid(ctx, image, method='filter', args=["ryo"])


def setup(bot):
    bot.add_cog(Polaroid(bot))

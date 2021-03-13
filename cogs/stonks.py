import math

import discord
import humanize
from discord.ext import commands, tasks
#from prettytable import PrettyTable
import tabulate

from utils.default import plural

from cogs.economy import get_stats

FINNHUB_URL = "https://finnhub.io/api/v1/"


class Stocks(commands.Cog, command_attrs=dict(hidden=False)):
    """
    Buy and sell stocks. Prices are directly related to real life prices.
    This works with the Economy commands.
    """
    def __init__(self, bot):
        """Creates the cog."""
        self.bot = bot
        self.finnhub = self.bot.config.finnhub
        self.del_none.start()

    @tasks.loop(hours=12)
    async def del_none(self):
        await self.bot.db.execute('DELETE FROM stocks WHERE amount = 0')
        
    @commands.command()
    async def dividend(self, ctx, dividend:float, stock_price:float, amount:int):
        """
        dividend can be find by searching it on google on the information card find `Div yield` you can enter it like 5.79 for 5.79%
        Stock price is just the stock price
        Amount is the amount of stocks you own
        """
        total_price = stock_price*amount
        real_dividend = dividend/100
        price = total_price*real_dividend
        return await ctx.send(price)

    @commands.command()
    async def buy(self, ctx, ticker: str = 'MSFT', amount='1'):
        """Buys a stock
        You can view a list of all stocks at https://stockanalysis.com/stocks/
        """
        wallet, _ = await get_stats(ctx, ctx.author.id)
        ticker = ticker.upper()

        async with self.bot.session.get(f'{FINNHUB_URL}/quote?symbol={ticker}&token={self.finnhub}') as data:
            stock = await data.json()

        if stock["c"] == 0:
            return await ctx.send('Invalid stock provided.')

        price: int = round(stock["c"])
        humanized_price: str = humanize.intcomma(price)

        if amount == 'max':
            amount = math.floor(wallet / price)
            if amount == 0:
                return await ctx.send(f'You don\'t have enough money to buy a share of {ticker}. '
                                      f'You need **${humanize.intcomma(price - wallet)}** more in order to purchase a share of {ticker}.')

        try:
            if int(amount):
                amount = int(amount)
        except ValueError:
            return await ctx.send("Invalid amount provided.")

        total: int = amount * price
        humanized_total: str = humanize.intcomma(total)

        share: str = plural("share(s)", amount)

        if total > wallet:
            return await ctx.send(f'You need **${humanize.intcomma(total - wallet)}** more in order to purchase'
                                  f' **{amount}** {share} of **{ticker}**')

        answer, message = await ctx.confirm(
            f'Confirm to buy **{amount}** {share} of **{ticker}** at **${humanized_price}**'
            f' per share for a total of **${humanized_total}**.'
        )

        if answer:
            stock_sql = (
                "INSERT INTO stocks(user_id, ticker, amount) VALUES($1, $2, $3) "
                "ON CONFLICT (user_id, ticker) "
                "DO UPDATE SET amount = stocks.amount + $3"
            )
            stock_values = (ctx.author.id, ticker, amount)

            eco_sql = (
                "UPDATE economy "
                "SET wallet = $1 "
                "WHERE user_id = $2"
            )
            eco_values = (wallet - total, ctx.author.id)

            await self.bot.db.execute(stock_sql, *stock_values)
            await self.bot.db.execute(eco_sql, *eco_values)

            await message.edit(content=f'Purchased **{amount}** {share} of **{ticker}** for **${humanized_total}**.')

        if not answer:
            await message.edit(content='Cancelled the transaction.')

    @commands.command(help='Sells a stock')
    async def sell(self, ctx, ticker: str = 'MSFT', amount='1'):
        ticker = ticker.upper()

        sql = (
            "SELECT amount FROM stocks WHERE user_id = $1 AND ticker = $2"
        )
        check = await ctx.bot.db.fetchval(sql, ctx.author.id, ticker)
        if not check:
            return await ctx.send(f'You don\'t have any shares of **{ticker}**')

        try:
            if amount != 'max' and int(amount) > check:
                return await ctx.send(f"You only have {check} {plural('share(s)', check)} of {ticker}")
        except ValueError:
            return await ctx.send("Invalid amount provided.")

        if amount == 'max':
            amount = check
        amount = int(amount)

        async with self.bot.session.get(f'{FINNHUB_URL}/quote?symbol={ticker}&token={self.finnhub}') as r:
            data: dict = await r.json()

        if data["c"] == 0:
            return await ctx.send('Invalid stock provided.')

        stock: dict = data

        price: int = round(stock["c"])
        total: int = amount * price

        humanized_price: str = humanize.intcomma(price)
        humanized_total: str = humanize.intcomma(total)

        share: str = plural("share(s)", amount)
        answer, message = await ctx.confirm(
            f'Confirm to sell **{amount}** {share} of **{ticker}** at **${humanized_price}**'
            f' per share for a total of **${humanized_total}**.'
        )

        if answer:
            stock_sql = (
                "UPDATE stocks "
                "SET amount = stocks.amount - $3 "
                "WHERE user_id = $1 AND ticker = $2"
            )
            stock_values = (ctx.author.id, ticker, amount)

            wallet, _ = await get_stats(ctx, ctx.author.id)
            eco_values = (wallet + total, ctx.author.id)

            await self.bot.db.execute("UPDATE economy SET wallet = $1 WHERE user_id = $2", *eco_values)
            await self.bot.db.execute(stock_sql, *stock_values)

            await message.edit(content=f'Sold **{amount}** {share} of **{ticker}** for **${humanized_total}**.')
        else:
            await message.edit(content='Cancelled the transaction.')

    @commands.command(help='Views your stock portfolio')
    async def portfolio(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author

        stuff = await self.bot.db.fetch("SELECT ticker, amount FROM stocks WHERE user_id = $1", user.id)
        if len(stuff) == 0:
            return await ctx.send(f'{user.mention} has no stocks', allowed_mentions=discord.AllowedMentions().none())
        table = tabulate.tabulate((dict(thing) for thing in stuff if thing["amount"] != 0), headers="keys", tablefmt="github")
        embed = ctx.embed(title=f"{user}\'s stocks:", description=f'```py\n{table}```')
        await ctx.send(embed=embed)

    @commands.command(help='Looks up a stocks price.', aliases=['stock_lookup'])
    async def lookup(self, ctx, ticker: str):
        ticker = ticker.upper()

        async with self.bot.session.get(f'{FINNHUB_URL}/quote?symbol={ticker}&token={self.finnhub}') as r:
            data: dict = await r.json()

        if data["c"] == 0:
            return await ctx.send('Yeah so that\'s not a valid stock lmao')

        stats = f'```yaml\n' \
                f'Current: {data["c"]}\n' \
                f'Daily High: {data["h"]}\n' \
                f'Daily Low: {data["l"]}\n' \
                f'Opening: {data["o"]}\n' \
                f'Previous Close: {data["pc"]}```'

        await ctx.send(stats)

    @commands.command(help='Search to see if a stock ticker exists.')
    async def check(self, ctx, search):
        search = search.upper()
        async with self.bot.session.get(f'{FINNHUB_URL}/search?q={search}&token={self.finnhub}') as r:
            data: dict = await r.json()

        if not data["result"]:
            return await ctx.message.add_reaction("❌")
        if data["result"][0]["symbol"] == search:
            await ctx.message.add_reaction("✅")
            await ctx.invoke(ctx.bot.get_command('lookup'), search)
        else:
            await ctx.message.add_reaction("❌")


def setup(bot):
    bot.add_cog(Stocks(bot))

import json

import decouple
import tornado.ioloop
import tornado.web
from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from models import Asset, Swap

DEBUG = decouple.config('DEBUG', default=False, cast=bool)

engine = create_async_engine(
    decouple.config('DATABASE_URL'),
    echo=DEBUG,
)

async_session = sessionmaker(engine,
                             expire_on_commit=False,
                             class_=AsyncSession)


class MainHandler(tornado.web.RequestHandler):
    """
    Provides accumulated information of all pairs for last 24 hours.
    """
    async def get(self):
        async with async_session() as session:
            # 24 hours ago since last imported transaction timestamp
            last_24h = (await session.execute(select(func.max(Swap.timestamp))
                                              )).scalar() - 24 * 3600
            # get names of all assets
            assets = {}
            for a, in await session.execute(select(Asset)):
                assets[a.id] = a
            # build list of all asset pairs
            pairs = {}
            for a1id, a2id in await session.execute(
                    select(
                        Swap.__table__.c.asset1_id,
                        Swap.__table__.c.asset2_id,
                    ).distinct()):
                a1 = assets[a1id]
                a2 = assets[a2id]
                pairs[a1.hash + "_" + a2.hash] = {
                    "base_id": a2.hash,
                    "base_name": a2.name,
                    "base_symbol": a2.symbol,
                    "quote_id": a1.hash,
                    "quote_name": a1.name,
                    "quote_symbol": a1.symbol,
                    "base_volume": 0,
                    "quote_volume": 0,
                }
            # get trade volumes over last 24 hours if exists
            # (sum(amount) from swap table)
            for a1id, a2id, a1vol, a2vol in await session.execute(
                    select(
                        Swap.__table__.c.asset1_id,
                        Swap.__table__.c.asset2_id,
                        func.sum(Swap.__table__.c.asset1_amount),
                        func.sum(Swap.__table__.c.asset2_amount),
                    ).where(Swap.__table__.c.timestamp > last_24h).group_by(
                        Swap.__table__.c.asset1_id,
                        Swap.__table__.c.asset2_id,
                    )):
                pairs[a1.hash + "_" + a2.hash]["base_volume"] = int(a1vol)
                pairs[a1.hash + "_" + a2.hash]["quote_volume"] = int(a2vol)
            # obtain last prices
            for a1id, a2id, last_price in await session.execute(
                    select(Swap.__table__.c.asset1_id,
                           Swap.__table__.c.asset2_id,
                           Swap.__table__.c.price).distinct(
                               Swap.__table__.c.asset1_id,
                               Swap.__table__.c.asset2_id,
                           ).order_by(Swap.__table__.c.asset1_id,
                                      Swap.__table__.c.asset2_id,
                                      Swap.__table__.c.timestamp.desc())):
                pairs[assets[a1id].hash + "_" +
                      assets[a2id].hash]['last_price'] = last_price
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(pairs))


class PairHandler(tornado.web.RequestHandler):
    """
    Provides information about specific pairs.
    """
    async def get(self, asset1, asset2):
        async with async_session() as session:
            last_24h = session.execute(select(func.max(Swap.timestamp)))
            # lookup assets by symbol
            a1 = session.execute(
                select(Asset).where(Asset.symbol == asset1.upper()))
            a2 = session.execute(
                select(Asset).where(Asset.symbol == asset2.upper()))
            # get asset1 info or 404
            a1 = (await a1).scalar()
            if not a1:
                await a2  # avoid "never awaited" warning
                self.set_status(404)
                self.write('Symbol {} not found.'.format(asset1))
                return
            # get asset2 info or 404
            a2 = (await a2).scalar()
            if not a2:
                self.set_status(404)
                self.write('Symbol {} not found.'.format(asset2))
                return
            # get accumulated volume over last 24 hours
            last_24h = (await last_24h).scalar() - 24 * 3600
            volume = session.execute(
                select(
                    func.sum(Swap.asset1_amount),
                    func.sum(Swap.asset2_amount),
                ).where(
                    and_(
                        Swap.timestamp > last_24h,
                        Swap.asset1_id == a1.id,
                        Swap.asset2_id == a2.id,
                    )))
            # get last price (price of last swap by timestamp)
            price = (await session.execute(
                select(Swap.__table__.c.price).where(
                    and_(Swap.asset1_id == a1.id,
                         Swap.asset2_id == a2.id)).order_by(
                             Swap.timestamp.desc()).limit(1))).scalar()
            if not price:
                # if no swap between asset1 and asset2 exists
                # then there is no such pair
                self.set_status(404)
                self.write('Pair {}{} not found.'.format(asset1, asset2))
                return
            for a1vol, a2vol in await volume:
                break
            response = {
                "base_id": a2.hash,
                "base_name": a2.name,
                "base_symbol": a2.symbol,
                "quote_id": a1.hash,
                "quote_name": a1.name,
                "quote_symbol": a1.symbol,
                "last_price": price,
                "base_volume": int(a1vol or 0),
                "quote_volume": int(a2vol or 0)
            }
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(response))


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/(.+)-(.+)", PairHandler),
    ])


def main():
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

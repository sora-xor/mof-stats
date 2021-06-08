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
    async def get(self):
        async with async_session() as session:
            last_24h = (await session.execute(select(func.max(Swap.timestamp))
                                              )).scalar() - 24 * 3600
            pairs = {}
            a1 = Asset.__table__.alias('a1')
            a2 = Asset.__table__.alias('a2')
            for row in await session.execute(
                    select(
                        Swap.__table__.c.asset1_id,
                        Swap.__table__.c.asset2_id,
                        a1.c.hash,
                        a2.c.hash,
                        a1.c.name,
                        a2.c.name,
                        a1.c.symbol,
                        a2.c.symbol,
                        func.sum(Swap.__table__.c.asset1_amount),
                        func.sum(Swap.__table__.c.asset2_amount),
                    ).where(Swap.__table__.c.timestamp > last_24h).group_by(
                        Swap.__table__.c.asset1_id,
                        Swap.__table__.c.asset2_id,
                        a1.c.hash,
                        a2.c.hash,
                        a1.c.name,
                        a2.c.name,
                        a1.c.symbol,
                        a2.c.symbol,
                    ).join(a1, a1.c.id == Swap.asset1_id).join(
                        a2, a2.c.id == Swap.asset2_id)):
                (a1id, a2id, a1hash, a2hash, a1name, a2name, a1sym, a2sym,
                 a1vol, a2vol) = row
                price = (await session.execute(
                    select(Swap.__table__.c.price).where(
                        and_(Swap.asset1_id == a1id,
                             Swap.asset2_id == a2id)).order_by(
                                 Swap.timestamp.desc()).limit(1))).scalar()
                pairs[a1hash + "_" + a2hash] = {
                    "base_id": a2hash,
                    "base_name": a2name,
                    "base_symbol": a2sym,
                    "quote_id": a1hash,
                    "quote_name": a1name,
                    "quote_symbol": a1sym,
                    "last_price": price,
                    "base_volume": str(a1vol),
                    "quote_volume": str(a2vol),
                }
        self.write(json.dumps(pairs))


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])


def main():
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()

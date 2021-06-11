import decouple
from sqlalchemy import (BigInteger, Column, Float, ForeignKey, Index, Integer,
                        Numeric, String)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

DEBUG = decouple.config('DEBUG', default=False, cast=bool)

Base = declarative_base()


def get_db_engine():
    return create_async_engine(
        decouple.config('DATABASE_URL'),
        echo=DEBUG,
    )


class Asset(Base):
    __tablename__ = 'asset'

    id = Column(Integer, primary_key=True)
    hash = Column(String(66), unique=True, nullable=False)
    symbol = Column(String(8), nullable=False)
    name = Column(String(128), nullable=False)
    precision = Column(Integer, nullable=False)
    trade_volume = Column(Float)


class Swap(Base):
    __tablename__ = 'swap'

    id = Column(Numeric(20), primary_key=True)
    block = Column(Integer, nullable=False)
    timestamp = Column(BigInteger, index=True, nullable=False)
    xor_fee = Column(Numeric(20), nullable=False)
    asset1_id = Column(ForeignKey("asset.id"), nullable=False)
    asset2_id = Column(ForeignKey("asset.id"), nullable=False)
    asset1_amount = Column(Numeric(33), nullable=False)
    asset2_amount = Column(Numeric(33), nullable=False)
    price = Column(Float)
    filter_mode = Column(String(32), nullable=False)
    swap_fee_amount = Column(Numeric(21))


Index('idx_swap_asset1_id_asset2_id', Swap.asset1_id, Swap.asset2_id)
Index('idx_swap_asset1_id_asset2_id_timestamp_desc', Swap.asset1_id,
      Swap.asset2_id, Swap.timestamp.desc())

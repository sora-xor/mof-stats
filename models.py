from sqlalchemy import (BigInteger, Column, Float, ForeignKey, Integer,
                        Numeric, String)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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

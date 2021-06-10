import argparse
import asyncio
from dataclasses import asdict
from time import sleep

import decouple
import requests
from scalecodec.type_registry import load_type_registry_file
from sqlalchemy import and_, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from substrateinterface import SubstrateInterface
from tqdm import trange

from models import Asset, Base, Swap, get_db_engine
from processing import (get_processing_functions, get_timestamp,
                        should_be_processed)


def connect_to_substrate_node():
    try:
        substrate = SubstrateInterface(
            url=decouple.config('SUBSTRATE_URL', "ws://127.0.0.1:9944"),
            type_registry_preset="default",
            type_registry=load_type_registry_file("custom_types.json"),
        )
        return substrate
    except ConnectionRefusedError:
        print(
            "⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first"  # noqa
        )
        return None


def get_events_from_block(substrate, block_id: int):
    block_hash = substrate.get_block_hash(block_id=block_id)

    # Retrieve extrinsics in block
    result = substrate.get_runtime_block(block_hash=block_hash,
                                         ignore_decoding_errors=True)
    events = substrate.get_events(block_hash)

    grouped_events = {}
    for event in events:
        event = str(event)
        eventdict = eval(event)
        idx = eventdict["extrinsic_idx"]

        if idx in grouped_events.keys():
            grouped_events[idx].append(eventdict)
        else:
            grouped_events[idx] = [eventdict]
    return result, grouped_events


def process_events(dataset, new_map, result, grouped_events):
    extrinsic_idx = 0
    timestamp = get_timestamp(result)

    for extrinsic in result["block"]["extrinsics"]:
        extrinsic_events = grouped_events[extrinsic_idx]
        extrinsic_idx += 1

        exstr = str(extrinsic)
        exdict = eval(exstr)

        if should_be_processed(exdict):
            tx_type = exdict["call_function"]
            processing_func = new_map.get(tx_type)
            if processing_func:
                tx = processing_func(timestamp, extrinsic_events, exdict)
                if tx:
                    dataset.append(asdict(tx))


async def get_or_create_asset(session, assets, hash):
    if hash in assets:
        return assets[hash]
    data = requests.get('https://sorascan.com/api/v1/asset/' +
                        hash).json()['data']['attributes']
    a = Asset(hash=hash,
              id=data['id'],
              name=data['name'],
              symbol=data['symbol'],
              precision=data['precision'])
    session.add(a)
    await session.commit()
    assets[hash] = a
    return a


async def async_main(clean=False, silent=False):
    engine = get_db_engine()
    # create tables if neccessary
    async with engine.begin() as conn:
        if clean:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # expire_on_commit=False will prevent attributes from being expired
    # after commit.
    async_session = sessionmaker(engine,
                                 expire_on_commit=False,
                                 class_=AsyncSession)
    # get the number of last block in the chain
    substrate = connect_to_substrate_node()
    end = substrate.get_runtime_block(
        substrate.get_chain_head())['block']['header']['number']
    selected_events = {'swap'}
    func_map = {
        k: v
        for k, v in get_processing_functions().items() if k in selected_events
    }
    async with async_session() as session:
        # get list of <Asset>s already in the DB
        assets = {}
        for a, in await session.execute(select(Asset)):
            assets[a.hash] = a
        # find number of last block already in DB and resume from there
        begin = (await session.execute(func.max(Swap.block))).scalar()
        if begin:
            begin += 1
        else:
            begin = 1
        # sync from last block in the DB to last block in the chain
        pending = None
        if not silent:
            print('Importing from', begin, 'to', end)
        for block in (range if silent else trange)(begin, end):
            # get events from <block> to <dataset>
            dataset = []
            res, events = get_events_from_block(substrate, block)
            process_events(dataset, func_map, res, events)
            # await previous INSERT to finish if any
            if pending:
                try:
                    await pending
                except IntegrityError as e:
                    # normally this should not happen but for some reason there
                    # are transactions with duplicate IDs in the chain
                    print('WARNING: Error during insert:')
                    print(e)
                    await session.rollback()
                    # rollback causes objects in <assets> to expire
                    # need to reload them
                    assets = {}
                    for a, in await session.execute(select(Asset)):
                        assets[a.hash] = a
                pending = None
            # prepare data to be INSERTed
            swaps = []
            for tx in dataset:
                tx['asset1_id'] = (await get_or_create_asset(
                    session, assets, tx.pop('asset1_type'))).id
                tx['asset2_id'] = (await get_or_create_asset(
                    session, assets, tx.pop('asset2_type'))).id
                if tx['asset2_amount']:
                    tx['price'] = tx['asset1_amount'] / tx['asset2_amount']
                swaps.append(Swap(block=block, **tx))
            if swaps:
                session.add_all(swaps)
                pending = session.commit()
        if pending:
            await pending
        # update trade_volume stats
        last_24h = (await session.execute(select(func.max(Swap.timestamp))
                                          )).scalar() - 24 * 3600
        await session.execute(
            update(Asset).values(
                trade_volume=select(func.sum(Swap.asset1_amount)).where(
                    and_(Swap.asset1_id == Asset.id,
                         Swap.timestamp > last_24h)).scalar_subquery() +
                select(func.sum(Swap.asset2_amount)).where(
                    and_(Swap.asset2_id == Asset.id,
                         Swap.timestamp > last_24h)).scalar_subquery()))
        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Import swap history from Substrate node into DB.')
    parser.add_argument(
        '--clean',
        '-c',
        action='store_true',
        help='clean (drop) and re-create database tables before import')
    parser.add_argument('--silent',
                        '-s',
                        action='store_true',
                        help='print no output except errors')
    parser.add_argument('--follow',
                        '-f',
                        action='store_true',
                        help='continiously poll for new blocks')
    args = parser.parse_args()
    if args.follow:
        # in follow mode import new blocks then sleep for 1 minute
        # then import again in a loop
        while True:
            asyncio.run(async_main(args.clean, args.silent))
            if not args.silent:
                print('Waiting for new blocks')
            sleep(60)
    else:
        asyncio.run(async_main(args.clean, args.silent))

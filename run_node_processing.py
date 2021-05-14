from dataclasses import asdict

import pandas as pd
from scalecodec.type_registry import load_type_registry_file
from substrateinterface import SubstrateInterface

from processing import get_processing_functions, get_timestamp, should_be_processed


def connect_to_substrate_node():
    try:
        substrate = SubstrateInterface(
            url="ws://127.0.0.1:9944",
            type_registry_preset="default",
            type_registry=load_type_registry_file("custom_types.json"),
        )
        return substrate
    except ConnectionRefusedError:
        print(
            "⚠️ No local Substrate node running, try running 'start_local_substrate_node.sh' first"
        )
        return None


def get_events_from_block(substrate, block_id: int):
    block_hash = substrate.get_block_hash(block_id=block_id)

    # Retrieve extrinsics in block
    result = substrate.get_runtime_block(
        block_hash=block_hash, ignore_decoding_errors=True
    )
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


def run_event_parser(start_block=0, num_blocks=1000):
    substrate = connect_to_substrate_node()
    if not substrate:
        exit()
    dataset = []

    selected_events = {'swap'}
    func_map = get_processing_functions()
    if not selected_events:
        selected_events = set(func_map.keys())
    new_map = dict(filter(lambda x: x[0] in selected_events, func_map.items()))

    for k in range(start_block, start_block + num_blocks):
        res, events = get_events_from_block(substrate, k)
        process_events(dataset, new_map, res, events)
    # We push data to pandas and save as csv.
    ds = pd.DataFrame(dataset).set_index('id')
    ds.to_csv('dataset.csv')

    # TODO: add analytics on pandas dataframe and write it in redis


if __name__ == "__main__":
    run_event_parser(10000, 100)

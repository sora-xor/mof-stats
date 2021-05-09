import json
from scalecodec.type_registry import load_type_registry_file
from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(
    url='wss://ws.sora2.soramitsu.co.jp',
    type_registry_preset='default',
    type_registry=load_type_registry_file('custom_types.json'),
)

block_hash = substrate.get_block_hash(block_id=168570)
print(block_hash)

# Retrieve extrinsics in block
result = substrate.get_runtime_block(block_hash=block_hash, ignore_decoding_errors=True)
events = substrate.get_events(block_hash)


groupedEvents = {}
for event in events:
	event = str(event)
	eventdict = eval(event)
	# print(eventdict['event_id'])
	# print(eventdict)
	idx = eventdict['extrinsic_idx']

	if idx in groupedEvents.keys():
		groupedEvents[idx].append(eventdict)
	else:
		groupedEvents[idx] = [eventdict]


print(len(result['block']['extrinsics']))
print(len(groupedEvents))

print(result)
print("\n")

extrinsicIdx = 0
for extrinsic in result['block']['extrinsics']:

	extrinsicEvents = groupedEvents[extrinsicIdx]
	extrinsicIdx += 1

	exstr = str(extrinsic)
	print(exstr)
	exdict = eval(exstr)
	print("exdict", exdict)
	print("extrinsicEvents", extrinsicEvents)

	if 'account_id' in exdict.keys():
		print('account_id', '0x' + exdict['account_id'])

	if 'extrinsic_hash' in exdict.keys():
		print('tx hash', '0x' + exdict['extrinsic_hash'])


	if 'call_function' in exdict.keys():
		txType = exdict['call_function']
		print('tx type', txType)

		if txType == 'swap':

			# verify that the swap was a success
			swapSuccess = False
			for event in extrinsicEvents:
				if event['event_id'] == 'SwapSuccess':
					swapSuccess = True
				print(event)

			if not swapSuccess:
				print("FAILED SWAP!")
				continue

			inputAssetType = None
			outputAssetType = None
			inputAmount = None
			outputAmount = None

			filterMode = None

			for param in exdict['params']:
				print("param", param)
				if param['name'] == 'input_asset_id':
					inputAssetType = param['value']
				elif param['name'] == 'output_asset_id':
					outputAssetType = param['value']
				elif param['name'] == 'swap_amount':
					if 'WithDesiredInput' in param['value']:
						inputAmount = param['value']['WithDesiredInput']['desired_amount_in']
						outputAmount = param['value']['WithDesiredInput']['min_amount_out']
					else: #then we do it by desired output
						inputAmount = param['value']['WithDesiredOutput']['max_amount_in']
						outputAmount = param['value']['WithDesiredOutput']['desired_amount_out']
				elif param['name'] == 'selected_source_types':
					filterMode = 'SMART' if len(param['value']) < 1 else param['value'][0] if len(param['value']) == 1 else param['value']
					#TODO: handle filterMode here

			print('SWAP', inputAssetType, outputAssetType, inputAmount, outputAmount, filterMode, swapSuccess)

		elif txType == 'withdraw_liquidity':
			withdrawAsset1Type = None
			withdrawAsset2Type = None
			withdrawAsset1Amount = None
			withdrawAsset2Amount = None
			for param in exdict['params']:
				# print("param", param)
				if param['name'] == 'output_asset_a':
					withdrawAsset1Type = param['value']
				elif param['name'] == 'output_asset_b':
					withdrawAsset2Type = param['value']
				elif param['name'] == 'output_a_min':
					withdrawAsset1Amount = param['value']
				elif param['name'] == 'output_b_min':
					withdrawAsset2Amount = param['value']

			print("WIDTHDRAW LIQUIDITY", withdrawAsset1Type, withdrawAsset2Type, withdrawAsset1Amount, withdrawAsset2Amount)

		elif txType == 'deposit_liquidity':
			for param in exdict['params']:
				print("param", param)
				depositAsset1Type = None
				depositAsset2Type = None
				depositAsset1Amount = None
				depositAsset2Amount = None

				# if param['name'] == 'input_asset_a':
				# elif param['name'] == 'input_asset_b':



	print('')



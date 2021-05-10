import json
from scalecodec.type_registry import load_type_registry_file
from substrateinterface import SubstrateInterface

substrate = SubstrateInterface(
    url='wss://ws.sora2.soramitsu.co.jp',
    type_registry_preset='default',
    type_registry=load_type_registry_file('custom_types.json'),
)

block_hash = substrate.get_block_hash(block_id=182769)
print(block_hash)

# Retrieve extrinsics in block
result = substrate.get_runtime_block(block_hash=block_hash, ignore_decoding_errors=True)
events = substrate.get_events(block_hash)


groupedEvents = {}
for event in events:
	event = str(event)
	eventdict = eval(event)
	idx = eventdict['extrinsic_idx']

	if idx in groupedEvents.keys():
		groupedEvents[idx].append(eventdict)
	else:
		groupedEvents[idx] = [eventdict]


# print(len(result['block']['extrinsics']))
# print(len(groupedEvents))

print(result)
print("\n")

extrinsicIdx = 0
for extrinsic in result['block']['extrinsics']:

	extrinsicEvents = groupedEvents[extrinsicIdx]
	extrinsicIdx += 1

	exstr = str(extrinsic)
	# print(exstr)
	exdict = eval(exstr)
	print("exdict", exdict)
	# print("extrinsicEvents", extrinsicEvents)

	if 'account_id' in exdict.keys():
		print('account_id', '0x' + exdict['account_id'])

	if 'extrinsic_hash' in exdict.keys():
		print('tx hash', '0x' + exdict['extrinsic_hash'])


	if 'call_function' in exdict.keys():
		txType = exdict['call_function']
		print('tx type', txType)

		if txType == 'swap':

			# verify that the swap was a success
			swapSuccess     = False

			inputAssetType  = None
			outputAssetType = None
			inputAmount     = None
			outputAmount    = None
			feeAmount       = None
			filterMode      = None

			for event in extrinsicEvents:
				# print(event)
				if event['event_id'] == 'SwapSuccess':
					swapSuccess = True

				elif event['event_id'] == 'Exchange':
					inputAmount = event['params'][4]['value']
					outputAmount = event['params'][5]['value']
					feeAmount = event['params'][6]['value']

			if not swapSuccess:
				print("FAILED SWAP!")
				continue

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

			print('SWAP', inputAssetType, outputAssetType, inputAmount, outputAmount, filterMode, swapSuccess, feeAmount)

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

		elif txType == 'as_multi': #incoming assets from the HASHI bridge

			bridgeSuccess = False
			assetId       = None
			bridgedAmt    = None
			extTxHash     = None #tx hash on the external chain

			for event in extrinsicEvents:
				print(event)

				if event['event_id'] == 'ExtrinsicSuccess':
					bridgeSuccess = True
				elif event['event_id'] == 'Transferred':
					assetId = event['params'][0]['value']
					bridgedAmt = event['params'][3]['value']
				elif event['event_id'] == 'RequestRegistered':
					extTxHash = event['params'][0]['value']

			if not bridgeSuccess:
				print("INCOMING BRIDGE TX FAILURE")
				continue

			print("INCOMING BRIDGE", assetId, bridgedAmt, extTxHash, bridgeSuccess)

			# for param in exdict['params']:
			# 	print("param", param)
			# 	if param['name'] == 'input_asset_a':
		elif txType == 'transfer_to_sidechain': #outgoing assets across the HASHI bridge

			bridgeSuccess   = False
			outoingAssetId  = None
			outoingAssetAmt = None
			extAddress      = None
			extType         = None

			for param in exdict['params']:
				print("param", param)

				if param['name'] == 'asset_id':
					outoingAssetId = param['value']
				elif param['name'] == 'amount':
					outoingAssetAmt = param['value']
				elif param['name'] == 'to':
					extType = param['type']
					extAddress = param['value']

			for event in extrinsicEvents: #TODO: should add logic here to collec the tx fee data

				if event['event_id'] == 'ExtrinsicSuccess':
					bridgeSuccess = True

			if not bridgeSuccess:
				print("OUTGOING BRIDGE TX FAILURE")
				continue

			print("OUTOING BRIDGE", outoingAssetId, outoingAssetAmt, extType, extAddress, bridgeSuccess)

		elif txType == 'claim':
			claimSuccess = False
			assetId      = None
			assetAmt     = None
			xorFeePaid   = None

			for event in extrinsicEvents:
				print(event)

				if event['event_id'] == 'ExtrinsicSuccess':
					claimSuccess = True
				elif event['event_id'] == 'Transferred' and event['event_idx'] == 1:
					assetId = event['params'][0]['value']
					assetAmt = event['params'][3]['value']
				elif event['event_id'] == 'FeeWithdrawn':
					xorFeePaid = event['params'][1]['value']

			if not claimSuccess:
				print("CLAIM TX FAILURE")
				continue

			print("CLAIM", assetId, assetAmt, claimSuccess, xorFeePaid)



	print('')



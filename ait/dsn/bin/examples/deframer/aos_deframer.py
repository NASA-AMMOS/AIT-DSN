#!/usr/bin/python3
#
# AOS Deframer contributed by ASU / Patrick Hailey
#
# An example AOS Deframer and Packet Processor developed for use by ASU as
# part of their GDS. This provides a baseline example implementation of the
# functionality necessary in a frame / packet handler to coerce data received
# via an SLE interface into telemetry packets for further processing and
# visualization.

"""
aos_deframer.py processes AOS frames into telemetry packets

"""

import sys, io, math, gevent, socket
from gevent.server import DatagramServer
from time import sleep

__author__ = "Patrick Hailey / ASU"

####################################
#Debug check: set 'pktPrint' to the following values to save samples of each packet type:
# Default - No Packets: 0
# XB1 FSW: 1
# XB1 SOH: 2
# Mini-NS1: 3
# Mini-NS2: 4
# IRIS Long: 5
# TBD: 6
# debug: 10
pktPrint = 0
####################################
#mpdu_pointer = 0
#curr_remainder = 0
#frame_counter = 0 #check if this should be 0 or 1 to start with
#max_pkts = 1
tf_header = 8 #length in bytes of Transfer Frame Primary Header
tf_fecf = 2 #length in bytes of Frame Error Control Field
aos_trail_fill = 6 # TODO: not quite sure where this is defined in documentation, but they're added after the end of data but before the 0xDC fill bytes
ccsds_prm = 6 # length in bytes ccsds primary header
ccsds_sec = 6 #length in bytes of ccsds secondary header
aos_long_frm = 1115 #length in bytes of Long AOS frame
aos_long_frm_df = 1105 #length in bytes of Long AOS frame data field (tf_header and tf_fecf removed)
aos_long_frm_df_end = 1113 #end position of Long frame data field
aos_short_frm = 223 #length in bytes of Short AOS frame
aos_short_frm_df = 213 #length in bytes of Short AOS frame data field (tf_header and tf_fecf removed)
aos_short_frm_df_end = 221 #end position of Short frame data field
max_pkts_long = 28 #max possible number of lunahmap packets of any type in 1 AOS Long frame
max_pkts_short = 6 #max possible number of lunahmap packets of any type in 1 AOS Short frame
aos_tlm_vcid = 30082 # Space Packet Virtual Channel ID (0x7582h)
aos_idle_vcid = 30143 # AOS IDLE Fram Virtual Channel ID (0x75BFh)
partial_header = False
count_pld_pb = 0 # count of payload playback packets that have been downlinked
count_soh_pb = 0 # count of soh playback packets that have been downlinked
count_fsw_pb = 0 # count of fsw playback packets that have been downlinked

# TODO: Combine all three packet managers into one packet manager with multiple class variables, getters, setters, etc.
class packet_manager():

	def __init__(self):
		self.temp_tlm_packet = bytearray()

	def set_packet(self, temp_tlm_packet):
		self.temp_tlm_packet = temp_tlm_packet

	def get_packet(self):
		return self.temp_tlm_packet

	def clear_packet(self):
		self.temp_tlm_packet = bytearray()

class packet_len_manager():

	def __init__(self):
		self.ccsds_packet_len = 0

	def set_packet(self, ccsds_packet_len):
		self.ccsds_packet_len = ccsds_packet_len

	def get_packet(self):
		return self.ccsds_packet_len

	def clear_packet(self):
		self.ccsds_packet_len = 0

class partial_header_manager():

	def __init__(self):
		self.partial_header = False

	def set_partial_header(self, partial_header):
		self.partial_header = partial_header

	def get_partial_header(self):
		return self.partial_header

	def clear_partial_header(self):
		self.partial_header = False

class cassy_server(DatagramServer):
	"""
	UDP Datagram server that handles incoming messages (telemetry data) from CaSSY on port :9999 and
	from DSN on port :TBD

	:param DatagramServer
	"""

	def handle(self, data, address):
		""" This handler is called whenever a message is received by the DatagramServer; capturing
		that message data and putting it through AOS decoder logic (decode_aos() method)

		:param data: The data of the message received
		:param address: The address that sent the message
		"""

		AOS_packet = bytearray(data)

		# TODO:insert function here to grab initial telemetry frame count once only for future error checking

		# Decode the AOS packet data
		packet_data = decode_aos(AOS_packet)

		# temp_tlm_packet holds a partial telemetry packet left over from previous AOS frame
		packet = packet_data ['temp_tlm_packet']

		# ccsds_packet_len holds the packet length for the current telemetry packet being processed
		ccsds_packet_len = packet_data ['ccsds_packet_len']

		tlm_packet_manager.set_packet(packet)
		tlm_packet_len_manager.set_packet(ccsds_packet_len)

		# final_tlm_packet holds the telemetry packet sent to AIT via telem_bridge() method
		final_tlm_packet = (packet_data ['final_tlm_packet'])

		# Only send complete, non-idle packets to AIT
		if not final_tlm_packet:
			print("Not sending IDLE, incomplete, or bad packets to AIT")
		else:
			print("Telemetry Packet Sent to AIT")
			final_tlm_packet = bytearray()

def decode_aos(AOS_packet):
	"""
	Logic to decode AOS frames that are sent by IRIS/CaSSY/DSN

	:param AOS_packet: the AOS frame data to decode
	"""

 	# First 2 bytes of AOS frame should be 0x7582 (30082 dec) - Space Packet Virtual Channel ID
	pkt_type = int.from_bytes(AOS_packet[0:2], "big")

	#This isn't the right spot for this, but we need get an initial frame count somewhere... hard code to 0 for now
	#need a different frame counter for IDLE and TLM packets; ignore count on bad packets; check if different TLM packet types get a different count
	curr_frame_counter = 0

	# Get the partial header from the manager from the previous AOS frame if there is one
	# Partial header is caused by too-small remaining bytes from previous AOS frame to extract packet length
	partial_header = partial_header_manager.get_partial_header()

	# Only perform AOS decoding if the packet type is Space Packet Virtual Channel ID (0x7582h)
	if pkt_type == aos_tlm_vcid:

		print("Telemetry packet received")

		# Detect if AOS long frame or AOS short frame packet was received
		if len(AOS_packet) == aos_long_frm:
			aos_df = aos_long_frm_df
			aos_df_end = aos_long_frm_df_end
		elif len(AOS_packet) == aos_short_frm:
			aos_df = aos_short_frm_df
			aos_df_end = aos_short_frm_df_end
		else:
			print("Unrecognized AOS Frame Size")

		# Check sequence count number, make sure frames are being received in order
		if int.from_bytes(AOS_packet[2:5], "big") < curr_frame_counter:
			print("Packets are out of order!")
			# TODO: perform packets out of order Error Correction

		# Perform AOS decoding if AOS frame number is correct
		else:
			# Get the MPDU pointer to know where the next telemetry packet begins in AOS data field
			mpdu_pointer = int.from_bytes(AOS_packet[6:8], "big")

			# mpdu_pointer == 0 signifies that the AOS data field begins with a new telemetry packet
			if mpdu_pointer == 0: #new tlm packet starts immediately

				# curr_remainder contains the current remaining number of bytes of the AOS data field that can contain telemetry packet data
				curr_remainder = aos_df_end

				# If temp_tlm_packet left from last AOS frame was too small to extract length, add temp_tlm_packet data onto front of new data field
				if partial_header == True:
					temp_tlm_packet = tlm_packet_manager.get_packet()
					# Extend the AOS data field we are looking at to include the initial telemetry packet header bytes from the previous AOS frame
					temp_tlm_packet.extend(AOS_packet[tf_header:aos_df_end])
					# Extract the packet length from the reconstructed telemetry packet header
					ccsds_packet_len = int.from_bytes(temp_tlm_packet[4:6], "big") + ccsds_prm + 1
					partial_header = False
					partial_header_manager.set_partial_header(partial_header)
				# If the partial_header is False, just grab the length of the first telemetry packet of the AOS data field normally
				else:
					# Need to add 7 since this BCT/CCSDS value is excluding 6 byte primary header (and also subtracts 1)
					ccsds_packet_len = int.from_bytes(AOS_packet[12:14], "big") + ccsds_prm + 1

				# current_pointer is the current starting position of the first unused byte in the remaining AOS data field
				curr_pointer = tf_header

				# Loop through the AOS data field, looking for telemetry packets
				for i in range(0, max_pkts_long):
					# Check if entire remainder AOS frame will be utilized by a single telemetry packet
					if ccsds_packet_len > curr_remainder:
						# If the telemetry packet is larger than the entire current AOS data field, and flows over to 1+ more AOS frames
						# TODO: this conditional is redundant... remove the 'if' logic below, but keep the logic from the 'else'
						if ccsds_packet_len > aos_df:
							packet = AOS_packet[curr_pointer:aos_df_end]
							tlm_packet_manager.set_packet(packet)
							tlm_packet_len_manager.set_packet(ccsds_packet_len)
							final_tlm_packet = bytearray()
							# Return empty final_tlm_packet because it is not completely built yet, preserve current telemetry packet data to temp_tlm_packet
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}
						# Use for packets smaller than AOS data field
						# TODO: remove if/else, but keep 'else' logic below
						else:
							tlm_packet_manager.set_packet(AOS_packet[(curr_pointer):aos_df_end])
							tlm_packet_len_manager.set_packet(ccsds_packet_len)
							final_tlm_packet = bytearray()
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}
						break

					# Multiple AOS frames in this telemetry packet
					else:
						# Send whole smaller telemetry packet to AIT
						final_tlm_packet = AOS_packet[curr_pointer: (curr_pointer + ccsds_packet_len)]
						curr_pointer = curr_pointer + ccsds_packet_len
						##### Reset 'Returned' variables to continue looping through same AOS frame TODO: these variable resets may be redundant
						temp_tlm_packet = bytearray()
						tlm_packet_manager.set_packet(temp_tlm_packet)
						ccsds_packet_len = 0

						# Send the telemetry packet to AIT via telem_bridge() method; TODO: move this to immediately follow final_tlm_packet assignment every time
						telem_bridge(final_tlm_packet)

						# Check if packet has nothing left but filler, meaning the AOS decoding on the message data is complete
						if AOS_packet[curr_pointer + aos_trail_fill] == 0xDC:
							# Return because we are done decoding AOS frame
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.clear_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}
							# break out of the for loop and move on to next AOS Frame
							break
						# If the remainder of the packet is full of realtime or playback data, continue looping to extract additional telemetry packets
						elif AOS_packet[curr_pointer] == 0x08 or AOS_packet[curr_pointer] == 0x09 or AOS_packet[curr_pointer] == 0x0C or AOS_packet[curr_pointer] == 0x0D: #08/09 is realtime (fsw/pld),  0C/0D is playback (fsw/pld)
							curr_remainder = aos_df_end - curr_pointer
							#Get new packet length
							ccsds_packet_len = int.from_bytes(AOS_packet[(curr_pointer + 4) : (curr_pointer + 6)], "big")  + ccsds_prm + 1
						# cycle through frame for additional small packets...
						# should only get here with garbage data
						else:
							curr_remainder = curr_remainder - ccsds_packet_len
							break

				# TODO: this code below until the elif may be redundant; TBD if we remove
				# save the rest of the message data that has not been processed to the temp_tlm_packet
				temp_tlm_packet = AOS_packet[curr_pointer:aos_df_end]
				tlm_packet_manager.set_packet(temp_tlm_packet)
				# save the packet length remaining
				tlm_packet_len_manager.set_packet(ccsds_packet_len)
				# return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_length
				return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}

			# mpdu_pointer == 2047 signifies this AOS frame is a partial telemetry packet (containing neither the beginning nor end of the packet) to be appended onto a temp_tlm_packet and there is not a new telemetry packet within this AOS frame
			elif mpdu_pointer == 2047:

				# TODO: Check if remainder from last AOS frame was too small to extract length; if so, add that remainder on to front of new data field
				if partial_header == True:
					# Add rest of packet to the temp_tlm_packet
					temp_tlm_packet = tlm_packet_manager.get_packet()
					temp_tlm_packet.extend(AOS_packet[tf_header:aos_df_end])
					tlm_packet_manager.set_packet(temp_tlm_packet)

					# Update the ccsds_packet_len
					ccsds_packet_len = int.from_bytes(temp_tlm_packet[4:6], "big") + ccsds_prm + 1
					tlm_packet_len_manager.set_packet(ccsds_packet_len)

					# Reset the partial header flag to False
					partial_header = False
					partial_header_manager.set_partial_header(partial_header)

					# Reset the final_tlm_packet (by definition, final_tlm_packet will always be empty in this 'elif')
					final_tlm_packet = bytearray()

					# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len
					return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}
				else:
					# Update the temp_tlm_packet to extend the temp_tlm_packet packet and then move on to the next AOS frame
					temp_tlm_packet = tlm_packet_manager.get_packet()
					temp_tlm_packet.extend(AOS_packet[tf_header:aos_df_end])
					tlm_packet_manager.set_packet(temp_tlm_packet)
					ccsds_packet_len = tlm_packet_len_manager.get_packet()
					final_tlm_packet = bytearray()
					# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len
					return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}

			# mdpu <> 0 and mdpu <> 2047 signifies the first byte of the first new telemetry packet within the AOS data field
			else:
				# Check if remainder from last AOS frame was too small to extract length; if so, add that remainder on to front of new data field
				if partial_header == True:
					# Update the temp_tlm_packet
					temp_tlm_packet = tlm_packet_manager.get_packet()
					temp_tlm_packet.extend(AOS_packet[tf_header:mpdu_pointer + tf_header])

					# Update the ccsds_packet_len
					# Note: Setting the length may not be needed because we have a full packet now
					ccsds_packet_len = int.from_bytes(temp_tlm_packet[4:6], "big") + ccsds_prm + 1

					# Update the partial_header
					partial_header = False
					partial_header_manager.set_partial_header(partial_header)

					# Update the final_tlm_packet
					final_tlm_packet = temp_tlm_packet

					# Send the fully built telemetry packet to AIT via telem_bridge() method
					telem_bridge(final_tlm_packet)
				# Normal case; Length of packet is known
				else:
					temp_tlm_packet = tlm_packet_manager.get_packet()
					ccsds_packet_len = tlm_packet_len_manager.get_packet()

					# If the temp_tlm_packet is empty, create one
					if not temp_tlm_packet:
						temp_tlm_packet = AOS_packet[tf_header:mpdu_pointer + tf_header]
						print(temp_tlm_packet)
					# Add on to the current tmp_tlm_packet
					else:
						temp_tlm_packet.extend(AOS_packet[tf_header:mpdu_pointer + tf_header])

					final_tlm_packet = temp_tlm_packet

					# Send the final_tlm_packet to AIT via the telem_bridge() method
					telem_bridge(final_tlm_packet)

				# We have completed the first packet within the current AOS frame and now need to check the frame and search for additional packets
				temp_tlm_packet = bytearray()
				tlm_packet_manager.set_packet(temp_tlm_packet)
				ccsds_packet_len = 0
				curr_pointer = tf_header + mpdu_pointer
				curr_remainder = aos_df_end - curr_pointer
				#Get new packet length
				ccsds_packet_len = int.from_bytes(AOS_packet[(curr_pointer + 4) : (curr_pointer + 6)], "big")  + ccsds_prm + 1
				# TODO: need to check this length inside the 0xDC loop and add the 6 extra random bytes. Need to figure out what is defined in these bytes
				tlm_packet_len_manager.set_packet(ccsds_packet_len)
				# TODO: walk through script and make sure final_tlm_packet bytearray is being emptied appropriately (doesn't always need to be emptied after sending the packet)
				# ccsds_packet_len is at bytes 7 and 8; check if they are a valid length or if they are 0xDCDC
				if ccsds_packet_len == 56547:#(ccsds_prm + 1 + DCDC = 56540 + 6 + 1)
					ccsds_packet_len = 0
					tlm_packet_len_manager.set_packet(ccsds_packet_len)
					# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len here because returning all empty values and beginning a new AOS frame
					return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.clear_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}

				# If additional data in the frame does exist, loop through it and break into additional packets
				for i in range(0, max_pkts_long):
					if ccsds_packet_len > curr_remainder:
						##############
						# TODO: need to make sure this search range doesnt go outside of the range of the remaining
						if AOS_packet[curr_pointer + aos_trail_fill] == 0xDC: # This seems redundant to previous check for 0xDC
							print(ccsds_packet_len)
							# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len and break out of the for loop
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.clear_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}
							break # redundant- remove
						# if byte is not equal to 0xDC, we have a partial packet
						else:
							packet = AOS_packet[curr_pointer:aos_df_end] # rename this to temp_tlm_packet
							tlm_packet_manager.set_packet(packet)

							# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len to persist the temporary telemetry packet
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.get_packet()}
							break # redundant- remove

					else:
						# TODO: fix the case when aos_trail_fill extends packet beyond data field
						if AOS_packet[curr_pointer + aos_trail_fill] == 0xDC:
							# Return the final_tlm_packet, temp_tlm_packet, and ccsds_packet_len because...
							return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.clear_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}
							break # redundant- remove
						# Check the type of data packet
						elif AOS_packet[curr_pointer] == 0x08 or AOS_packet[curr_pointer] == 0x09 or AOS_packet[curr_pointer] == 0x0C or AOS_packet[curr_pointer] == 0x0D: #08 is realtime, 0C is playback
							final_tlm_packet = AOS_packet[curr_pointer: (curr_pointer + ccsds_packet_len)]

							# Send the final_tlm_packet to AIT
							telem_bridge(final_tlm_packet)
							##### Reset 'Returned' variables to continue looping through same AOS frame
							temp_tlm_packet = bytearray()
							curr_pointer = curr_pointer + ccsds_packet_len
							ccsds_packet_len = 0
							print(curr_pointer)
							curr_remainder = aos_df_end - curr_pointer
							# need to carry this temp_tlm_packet to next AOS frame, use at position10. need to also carry through a true/false trigger to define packet length at that point
							if curr_remainder < 6: #LMAP packet length is found at bytes 5&6
								temp_tlm_packet = AOS_packet[curr_pointer : aos_df_end]
								print(temp_tlm_packet)
								partial_header = True
								partial_header_manager.set_partial_header(partial_header)
								tlm_packet_manager.set_packet(temp_tlm_packet)
								return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.get_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}
								break # redundant- remove
							else:
								# Get new packet length
								ccsds_packet_len = int.from_bytes(AOS_packet[(curr_pointer + 4) : (curr_pointer + 6)], "big")  + ccsds_prm + 1
								print(ccsds_packet_len)
						else: # cycle through frame for additional small packets
							print("made it here_18") # should only get here with garbage data
							curr_remainder = curr_remainder - ccsds_packet_len
							break
				# TODO: TBD if this return is necessary, this may never be called
				return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : tlm_packet_manager.clear_packet(), 'ccsds_packet_len' : tlm_packet_len_manager.clear_packet()}

	# Print if we receive IDLE packet should be 0x75BF (30143 dec)
	elif pkt_type == aos_idle_vcid:
		print("IDLE Packet Received")
		temp_tlm_packet = bytearray()
		final_tlm_packet = bytearray()
		ccsds_packet_len = 0
		return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : temp_tlm_packet, 'ccsds_packet_len' : ccsds_packet_len }
	else:
		print("Unrecognized Packet Type")
		temp_tlm_packet = bytearray()
		final_tlm_packet = bytearray()
		ccsds_packet_len = 0
		return {'final_tlm_packet' : final_tlm_packet, 'temp_tlm_packet' : temp_tlm_packet, 'ccsds_packet_len' : ccsds_packet_len}

def telem_bridge(final_tlm_packet):
	''' telem_bridge is used to send a telemetry packet to AIT. This is LunaH-Map specific code
	for sending telemetry packets to AIT.

	:param final_tlm_packet: the telmetry packet to send to AIT
	'''

	# Send telemetry packet to AIT telemetry port(s)
	print("Sending telemetry packet to AIT for processing")


if __name__ == "__main__":
	try:
		tlm_packet_manager = packet_manager()
		tlm_packet_len_manager = packet_len_manager()
		partial_header_manager = partial_header_manager()
		cassy_server(':9999').serve_forever() #Process will not terminate on its own
	except KeyboardInterrupt:
		cassy_server.close()

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2018, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import os
import unittest
import mock

import ait.core
from ait.dsn.sle.frames import AOSTransFrame, AOSConfig, AOSDataFieldType

# Supress logging because noisy
patcher = mock.patch('ait.core.log.info')
patcher.start()


class AosTest(unittest.TestCase):

    def setUp(self):
        # Create a config instance (otherwise we would need to update the cfg yaml)

        # The virtual channel map which maps virtual channel ids (integer) to
        # a string indicating the type of the AOS data
        # fields (b_pdu,m_pdu.vca_sdu,idle)
        self.virt_chan_map = {1: "b_pdu",
                              2: "m_pdu",
                              3: "vca_sdu",
                              4: "idle"}

        # The shared AOS config, indicating which optional fields exists and the
        # Virtual channel map
        self.aos_cfg = AOSConfig(virtual_channels=self.virt_chan_map,
                                 frame_header_error_control_included=True,
                                 operational_control_field_included=True,
                                 frame_error_control_field_included=True)

    def tearDown(self):
        pass

    def test_decode_aos_mpdu(self):

        # ver, spccrft,vrtchn  ...  vc frm cnt       ...    signalin     ..frmHdrErrCtrl..
        # 01,110011 10,000010 00000000 00000000 00000001,  1,0,01,0101   00000000 00000001
        frame_data_hdr = "7382000001950001"

        # M_PDU header: 5 bits reserved, 11 first header pointer: 07FF
        # 00000,000 00001111   00000001 000100011 01000101  01100111
        # Remaining: M_PDU packet zone
        MPDU_NO_PARTIAL_HDR = "0000"
        frame_data_body = "000001234567"


        # frame data trailer: four and two bytes
        frame_data_trlr = "000003FF0880"

        data_hex_str = frame_data_hdr + frame_data_body + frame_data_trlr

        frame_data = bytes.fromhex(data_hex_str)

        aos_frame = AOSTransFrame(config=self.aos_cfg, data=frame_data)

        # Test super-class methods / property-access
        frame_vc = aos_frame.virtual_channel
        mstr_chan_id = aos_frame.master_channel_id
        has_data = aos_frame.contains_data()
        data_field = aos_frame.data_field

        # Test direct access of signal field parts
        df_type = aos_frame['aos_data_field_type']
        replay_flag = aos_frame['replay_flag']
        vc_fc_c_uf = aos_frame['virtual_channel_frame_count_cycle_use_flag']
        vc_fc_c = aos_frame['virtual_channel_frame_count_cycle']


        self.assertEqual(mstr_chan_id, 462)
        self.assertEqual(frame_vc, 2)
        self.assertEqual(df_type, AOSDataFieldType.M_PDU)
        self.assertNotEqual(df_type, AOSDataFieldType.B_PDU)

        self.assertEqual(replay_flag, 1)
        self.assertEqual(vc_fc_c_uf,  0)
        self.assertEqual(vc_fc_c, 5)

        self.assertTrue(has_data)


        self.assertEqual(data_field.hex(), '000001234567')

        mpdu_data = aos_frame['mpdu_packet_zone']
        self.assertEqual(mpdu_data.hex(), '01234567')

        mpdu_data_idle = aos_frame['mpdu_is_idle_data']
        self.assertFalse(mpdu_data_idle)




    def test_decode_aos_bpdu(self):

        # ver, spccrft,vrtchn  ...  vc frm cnt       ...    signalin     ..frmHdrErrCtrl..
        # 01,110011 10,000001 00000000 00000000 00000001,  0,0,01,0001   00000000 00000001
        frame_data_hdr = "7381000001110001"

        # B_PDU header: 2 bits reserved, 14 bitstream data pointer: 010F
        # 00,000001 00001111, then random octets

        # Remaining: B_PDU packet zone
        frame_data_body = "010F01234567"

        # frame data trailer: four and two bytes
        frame_data_trlr = "000003FF0880"

        data_hex_str = frame_data_hdr + frame_data_body + frame_data_trlr
        frame_data = bytes.fromhex(data_hex_str)
        aos_frame = AOSTransFrame(config=self.aos_cfg, data=frame_data)

        frame_vc = aos_frame.virtual_channel
        mstr_chan_id = aos_frame.master_channel_id
        df_type = aos_frame['aos_data_field_type']

        has_data = aos_frame.contains_data()

        self.assertEqual(mstr_chan_id, 462)
        self.assertEqual(frame_vc, 1)
        self.assertEqual(df_type, AOSDataFieldType.B_PDU)
        self.assertTrue(has_data)

        bpdu_ptr = aos_frame['bpdu_bitstream_data_ptr']
        bpdu_idle = aos_frame['bpdu_contains_idle_data']  ##True when (self['bpdu_bitstream_data_ptr'] == b'11111111111110')
        bpdu_data = aos_frame['bpdu_data_zone']

        self.assertFalse(bpdu_idle)




    def test_decode_aos_pkt_idle(self):

        # Higher level idle packet (When aosfrm['virtual_channel_id'] == b'111111')

        # ver, spccrft,vrtchn  ...  vc frm cnt       ...    signalin     ..frmHdrErrCtrl..
        # 01,110011 10,111111 00000000 00000000 00000001,  0,0,01,0001   00000000 00000001
        frame_data_hdr = "73BF000001110001"

        # No data field
        frame_data_body = ""

        # frame data trailer: four and two bytes
        frame_data_trlr = "000003FF0880"

        data_hex_str = frame_data_hdr + frame_data_body + frame_data_trlr
        frame_data = bytes.fromhex(data_hex_str)
        aos_frame = AOSTransFrame(config=self.aos_cfg, data=frame_data)

        frame_vc = aos_frame.virtual_channel
        mstr_chan_id = aos_frame.master_channel_id
        df_type = aos_frame['aos_data_field_type']
        is_idle = aos_frame.is_idle_frame
        self.assertTrue(is_idle)
        self.assertIsNone(df_type)




    def test_decode_aos_df_idle(self):

        # ver, spccrft,vrtchn  ...  vc frm cnt       ...    signalin     ..frmHdrErrCtrl..
        # 01,110011 10,000100 00000000 00000000 00000001,  0,0,01,0001   00000000 00000001
        frame_data_hdr = "7384000001110001"

        # M_PDU header: 5 bits reserved, 11 first header pointer: 07FF
        # 00000,000 00001111   00000001 000100011 01000101  01100111

        # Remaining: M_PDU packet zone
        frame_data_body = "000F01234567"

        # frame data trailer: four and two bytes
        frame_data_trlr = "000003FF0880"

        data_hex_str = frame_data_hdr + frame_data_body + frame_data_trlr
        frame_data = bytes.fromhex(data_hex_str)
        aos_frame = AOSTransFrame(config=self.aos_cfg, data=frame_data)

        frame_vc = aos_frame.virtual_channel
        mstr_chan_id = aos_frame.master_channel_id
        df_type = aos_frame['aos_data_field_type']

        self.assertEqual(df_type, AOSDataFieldType.IDLE)
        has_data = aos_frame.contains_data()
        self.assertTrue(has_data)

    def test_decode_aos_vcasdu(self):

        # ver, spccrft,vrtchn  ...  vc frm cnt       ...    signalin     ..frmHdrErrCtrl..
        # 01,110011 10,000011 00000000 00000000 00000001,  0,0,01,0001   00000000 00000001
        frame_data_hdr = "7383000001110001"

        # VCASDU, just data with no header/trailer
        frame_data_body = "01234567"

        # frame data trailer: four and two bytes
        frame_data_trlr = "000003FF0880"

        data_hex_str = frame_data_hdr + frame_data_body + frame_data_trlr

        frame_data = bytes.fromhex(data_hex_str)

        aos_frame = AOSTransFrame(config=self.aos_cfg, data=frame_data)
        df_type = aos_frame['aos_data_field_type']

        # Test data field type
        self.assertEqual(df_type, AOSDataFieldType.VCA_SDU)

        # test that all datafield is VCASDU data field
        vcasdu_data = aos_frame['vcasdu_data_zone']
        self.assertEqual(vcasdu_data.hex(), '01234567')

    def test_default_config(self):
        l_aos_cfg = AOSConfig()

        self.assertFalse(l_aos_cfg.operational_control_field_included)
        self.assertFalse(l_aos_cfg.frame_error_control_field_included)
        self.assertFalse(l_aos_cfg.frame_header_error_control_included)
        self.assertEqual(l_aos_cfg.operational_control_field_len, 0)

        # default config sould have virtual channel 1 assigned a type
        self.assertIsNotNone(l_aos_cfg.get_data_field_type(1))

        # But these virtual channel ids should all be undefined
        self.assertIsNone(l_aos_cfg.get_data_field_type(100))
        self.assertIsNone(l_aos_cfg.get_data_field_type(-1))


    def test_reject_encode(self):
        pass
import pytest
import ait.dsn.sle.tctf as tctf

@pytest.fixture()
def random_1024_bytes():
    seed ='b66511a051d3964081c2b2ddbd58837ef8d0e5d9d09dc29afcbb9ae94658bf9226ade28dbdf56cd181ecddd1dedfac8b162b1bddd41307cacc04f560d12b4dc0ca60d80bee032fcccb2640127ac997c26e4599ef898204650c137e4c499807b8b3f9929714e6e30e572be68b8cc1312fcc35f265346295623f459dd364f39bbd24a156bd7585e4e5f16075bb0019179c72902879f435bc250b7d5eaf138b8907d2133dc2459764aa28825861fb66701a99080b59738af6d966a0de72c0142541b1052f4f3a65aa06dbb765e218e85571d429cabfac580d52d6c9ea279fef068828393dd1fd2aa8ffc2f1cc6b1d8982fdf6c225321ae1d1eb63fe333009b32239a9db43eab84482ca5a9316249301398c264dbceef69c4c28e7e892af4ea62b8c7837d37c1b73cd991498c7a48a68bcb80a424dd76a7eca728b110dd37420f2d0fae3f2531f55d03fa4613e559b54a4188bee86e29fccc3023f6412906e692b88d6b3840811dadd98519c8fb1b49d0d0b722ed6a01da7c93d47cdd6e667d53fa5a34ac1098ab5eea14e4acd1ceccd86d761871652ddc6b74722ee2b1f011bf97c254ebfa5dd1d6d792f17db3b914060d2a0dc9608ce40f0362c11cfaaa7135b4547110ce7a6e87b6225551cfc1c44aaa24a032268b9815bda407a45c065638625ed7cecccfb9e7c80b21e4cb5cf625b015f181b262fb32c20c24fd6ad2eb8535ba88dec8f7465809abfda7102faeb096c14da5e8d87a115034e5f81806a14547dc8a64fe59f2681442c926df94f15d2c20bb472c66d1c39271527ac74efbc7416e16fce11f364c4f82b24c485d0f34b7833be7f986232fbf670238b60a91ff6fbac3497e95e24c89eebc95f4056d796c1eb5f19e583b1559f9262f023fc33a0150d1b4bdaa3d72ee636be1be0745fb4609d63e3fd9ee238d420e48cc4a58ccc6ec0a435d90ee5af3561f05fbbffaa78efaf03a64d08cdc3d0ca56558e056ad2aa622d60beddb3f2b5c4bc7ed816339f103c863c70f6d66f3e0ec83c54906337edf20491bbef2a2caa54a8ff79dd9fc547dc232f494aaa7782a9210124f5d01712555882af6bfda6c8d2261e837271770e4df43cc8656aedf82ab3c767649bde9407cc63506f02fdad6008deae1f2b171016c44bb8da8dc291d008f0ba9a360d73b8403eeab07eac44b9c4d1ec501d71846a4fcba5b0c17f826d5e67dd2df52e349214cc2723b6a1fe8680d63cd0d99c6a7ec61c74f512b8e058f26f8473f47a74319d4d83339a6dc3055dea072dff16ad0e390925f7c00fdd77f65a044c8a5067294933992b257c89aad6032889d63e4ddace083859bc31f6854c69e35f73a74de1a7c6f2793166e797ca682ee776fce813a1ef28d3bbed0efce43acfa6803bb3ab7b82a9d525e4db6ce9658b317ead0c3efbad8d8878a4ea96a9283ef7e9e5bd'
    return bytes.fromhex(seed)

@pytest.fixture()
def random_payload_no_ecf(random_1024_bytes):
    cut = tctf.ICD.Sizes.MAX_DATA_FIELD_NO_ECF_OCTETS.value
    payload = random_1024_bytes[:cut]
    return payload

@pytest.fixture()
def random_payload_ecf(random_1024_bytes):
    cut = tctf.ICD.Sizes.MAX_DATA_FIELD_ECF_OCTETS.value
    payload = random_1024_bytes[:cut]
    return payload

@pytest.fixture()
def random_payload_random_len(random_1024_bytes):
    cut = 71
    payload = random_1024_bytes[:cut]
    return payload

def test_TCTF_no_ecf(random_payload_no_ecf):
    tf_version_num = 1
    bypass = 1
    cc = 1
    rsvd = 1
    scID = 123
    vcID = 2
    frame_seq_num = 1
    frame = tctf.TCTransFrame(tf_version_num, bypass, cc, rsvd, scID, vcID,
                              frame_seq_num, random_payload_no_ecf)

    encoded_frame_hex = frame.encode()

    decoded_frame = tctf.TCTransFrame.decode(encoded_frame_hex)
    decoded_frame_header = decoded_frame.header_map

    assert decoded_frame_header[tctf.HeaderKeys.TRANSFER_FRAME_VERSION_NUM] == tf_version_num
    assert decoded_frame_header[tctf.HeaderKeys.BYPASS_FLAG] == bypass
    assert decoded_frame_header[tctf.HeaderKeys.CONTROL_COMMAND_FLAG] == cc
    assert decoded_frame_header[tctf.HeaderKeys.RESERVED] == rsvd
    assert decoded_frame_header[tctf.HeaderKeys.SPACECRAFT_ID] == scID
    assert decoded_frame_header[tctf.HeaderKeys.VIRTUAL_CHANNEL_ID] == vcID
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_LENGTH] \
        == tctf.ICD.Sizes.MAX_FRAME_OCTETS.value-1 # Per ICD subtract 1
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_SEQ_NUM] == frame_seq_num
    assert decoded_frame.payload == random_payload_no_ecf
    assert decoded_frame.ecf == None


def test_TCTF_ecf(random_payload_ecf):
    tf_version_num = 0
    bypass = 0
    cc = 0
    rsvd = 1
    scID = 50
    vcID = 1
    frame_seq_num = 191
    frame = tctf.TCTransFrame(tf_version_num, bypass, cc, rsvd, scID, vcID,
                              frame_seq_num, random_payload_ecf, apply_ecf=True)

    encoded_frame_hex = frame.encode()
    
    decoded_frame = tctf.TCTransFrame.decode(encoded_frame_hex, True)
    decoded_frame_header = decoded_frame.header_map
    
    assert decoded_frame_header[tctf.HeaderKeys.TRANSFER_FRAME_VERSION_NUM] == tf_version_num
    assert decoded_frame_header[tctf.HeaderKeys.BYPASS_FLAG] == bypass
    assert decoded_frame_header[tctf.HeaderKeys.CONTROL_COMMAND_FLAG] == cc
    assert decoded_frame_header[tctf.HeaderKeys.RESERVED] == rsvd
    assert decoded_frame_header[tctf.HeaderKeys.SPACECRAFT_ID] == scID
    assert decoded_frame_header[tctf.HeaderKeys.VIRTUAL_CHANNEL_ID] == vcID
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_LENGTH] \
        == tctf.ICD.Sizes.MAX_FRAME_OCTETS.value-1 # Per ICD subtract 1
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_SEQ_NUM] == frame_seq_num
    assert decoded_frame.payload == random_payload_ecf
    assert decoded_frame.ecf == b'C\x86'

def test_TCTF_random_len_ecf(random_payload_random_len):
    tf_version_num = 3
    bypass = 0
    cc = 1
    rsvd = 0
    scID = 66
    vcID = 3
    frame_seq_num = 55
    frame = tctf.TCTransFrame(tf_version_num, bypass, cc, rsvd, scID, vcID,
                              frame_seq_num, random_payload_random_len, apply_ecf=True)

    encoded_frame_hex = frame.encode()
    
    decoded_frame = tctf.TCTransFrame.decode(encoded_frame_hex, True)
    decoded_frame_header = decoded_frame.header_map
    
    assert decoded_frame_header[tctf.HeaderKeys.TRANSFER_FRAME_VERSION_NUM] == tf_version_num
    assert decoded_frame_header[tctf.HeaderKeys.BYPASS_FLAG] == bypass
    assert decoded_frame_header[tctf.HeaderKeys.CONTROL_COMMAND_FLAG] == cc
    assert decoded_frame_header[tctf.HeaderKeys.RESERVED] == rsvd
    assert decoded_frame_header[tctf.HeaderKeys.SPACECRAFT_ID] == scID
    assert decoded_frame_header[tctf.HeaderKeys.VIRTUAL_CHANNEL_ID] == vcID
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_LENGTH] \
        == 71 + tctf.ICD.Sizes.PRIMARY_HEADER_OCTETS.value + tctf.ICD.Sizes.ECF_OCTETS.value - 1  # Per ICD subtract 1
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_SEQ_NUM] == frame_seq_num
    assert decoded_frame.payload == random_payload_random_len
    assert decoded_frame.ecf == b'2\xb4'
    
def test_TCTF_random_len_no_ecf(random_payload_random_len):
    tf_version_num = 2
    bypass = 1
    cc = 0
    rsvd = 1
    scID = 321
    vcID = 8
    frame_seq_num = 222
    frame = tctf.TCTransFrame(tf_version_num, bypass, cc, rsvd, scID, vcID,
                              frame_seq_num, random_payload_random_len)

    encoded_frame_hex = frame.encode()
    
    decoded_frame = tctf.TCTransFrame.decode(encoded_frame_hex)
    decoded_frame_header = decoded_frame.header_map
    
    assert decoded_frame_header[tctf.HeaderKeys.TRANSFER_FRAME_VERSION_NUM] == tf_version_num
    assert decoded_frame_header[tctf.HeaderKeys.BYPASS_FLAG] == bypass
    assert decoded_frame_header[tctf.HeaderKeys.CONTROL_COMMAND_FLAG] == cc
    assert decoded_frame_header[tctf.HeaderKeys.RESERVED] == rsvd
    assert decoded_frame_header[tctf.HeaderKeys.SPACECRAFT_ID] == scID
    assert decoded_frame_header[tctf.HeaderKeys.VIRTUAL_CHANNEL_ID] == vcID
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_LENGTH] \
        == 71 + tctf.ICD.Sizes.PRIMARY_HEADER_OCTETS.value - 1  # Per ICD subtract 1
    assert decoded_frame_header[tctf.HeaderKeys.FRAME_SEQ_NUM] == frame_seq_num
    assert decoded_frame.payload == random_payload_random_len
    assert decoded_frame.ecf == None

import numpy as np
import pytest

from app.frame_payload_codec import ENCODING,FramePayloadError,SourceFramePayloadCodec


def pixels():
    value=np.zeros((7,9,4),dtype=np.uint8);value[1:6,2:8]=[7,91,203,177];return value


def test_compact_rgba_payload_round_trip_preserves_alpha():
    codec=SourceFramePayloadCodec();source=pixels();payload=codec.encode(source,("a",0));loaded=codec.decode(payload,9,7,("a",0))
    assert payload["encoding"]==ENCODING and np.array_equal(loaded,source) and np.array_equal(loaded[...,3],source[...,3])


def test_payload_is_deterministic():
    source=pixels();a=SourceFramePayloadCodec().encode(source);b=SourceFramePayloadCodec().encode(source)
    assert a==b


def test_payload_rejects_invalid_base64():
    payload=SourceFramePayloadCodec().encode(pixels());payload["data"]="not base64!"
    with pytest.raises(FramePayloadError,match="base64"):SourceFramePayloadCodec().decode(payload)


def test_payload_rejects_wrong_shape_and_byte_length():
    codec=SourceFramePayloadCodec();payload=codec.encode(pixels());payload["width"]+=1
    with pytest.raises(FramePayloadError,match="byte length"):codec.decode(payload)
    payload=codec.encode(pixels());payload["channels"]=3
    with pytest.raises(FramePayloadError,match="shape"):codec.decode(payload)


def test_payload_rejects_checksum_mismatch():
    codec=SourceFramePayloadCodec();payload=codec.encode(pixels());payload["checksum"]="0"*64
    with pytest.raises(FramePayloadError,match="checksum"):codec.decode(payload)


def test_payload_rejects_unsupported_encoding():
    codec=SourceFramePayloadCodec();payload=codec.encode(pixels());payload["encoding"]="unknown"
    with pytest.raises(FramePayloadError,match="unsupported"):codec.decode(payload)


def test_payload_has_decode_size_limit():
    codec=SourceFramePayloadCodec();payload=codec.encode(pixels());payload.update(width=16384,height=16384,byte_length=16384*16384*4)
    with pytest.raises(FramePayloadError,match="safe decode limit"):codec.decode(payload)


def test_legacy_nested_list_payload_still_loads():
    source=pixels();loaded=SourceFramePayloadCodec().decode(source.tolist(),9,7)
    assert np.array_equal(source,loaded)


def test_unchanged_payload_cache_hit_avoids_reencode():
    codec=SourceFramePayloadCodec();source=pixels();first=codec.encode(source,("source","id",0));second=codec.encode(source,("source","id",0))
    assert first==second and codec.stats.encode_calls==1 and codec.stats.cache_hits==1


def test_metadata_identity_change_does_not_affect_pixel_content_cache_when_identity_is_stable():
    codec=SourceFramePayloadCodec();source=pixels();identity=("source","id",0);codec.encode(source,identity);codec.encode(source,identity)
    assert codec.stats.encode_calls==1


def test_changed_frame_invalidates_only_its_payload():
    codec=SourceFramePayloadCodec();a=pixels();b=np.flip(a,axis=1).copy();codec.encode(a,("clip","id",0));codec.encode(b,("clip","id",1));a[0,0]=[1,2,3,4];codec.encode(a,("clip","id",0));codec.encode(b,("clip","id",1))
    assert codec.stats.encode_calls==3 and codec.stats.cache_hits==1


def test_codec_lru_respects_memory_limit():
    codec=SourceFramePayloadCodec(maximum_cache_bytes=100);a=np.random.default_rng(1).integers(0,256,(8,8,4),dtype=np.uint8);b=np.random.default_rng(2).integers(0,256,(8,8,4),dtype=np.uint8)
    codec.encode(a,("a",));codec.encode(b,("b",))
    assert len(codec._cache)==1

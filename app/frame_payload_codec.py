"""Deterministic, lossless RGBA frame payloads for project persistence."""

from __future__ import annotations

from collections import OrderedDict
import base64
from dataclasses import dataclass
from hashlib import sha256
import zlib

import numpy as np


ENCODING="rgba8-zlib-base64"
MAX_DIMENSION=16384
MAX_DECODED_BYTES=64*1024*1024


class FramePayloadError(ValueError):
    """Raised when an encoded pixel frame is invalid or unsafe."""


@dataclass
class CodecStats:
    encode_calls: int=0
    decode_calls: int=0
    cache_hits: int=0
    cache_misses: int=0
    checksum_calls: int=0


class SourceFramePayloadCodec:
    """Encode RGBA8 arrays and reuse unchanged payloads in a bounded LRU."""

    def __init__(self,compression_level: int=1,maximum_cache_bytes: int=64*1024*1024):
        self.compression_level=max(0,min(9,int(compression_level)))
        self.maximum_cache_bytes=max(1,int(maximum_cache_bytes));self.current_cache_bytes=0
        self._cache: OrderedDict[tuple,dict]=OrderedDict();self.stats=CodecStats()

    @staticmethod
    def _validated_frame(frame) -> np.ndarray:
        pixels=np.asarray(frame)
        if pixels.dtype!=np.uint8 or pixels.ndim!=3 or pixels.shape[2]!=4:
            raise FramePayloadError("pixel frame must be an H x W x 4 uint8 array")
        height,width=pixels.shape[:2];byte_length=width*height*4
        if width<1 or height<1 or width>MAX_DIMENSION or height>MAX_DIMENSION or byte_length>MAX_DECODED_BYTES:
            raise FramePayloadError("pixel frame exceeds the safe decode limit")
        return np.ascontiguousarray(pixels)

    def encode(self,frame,cache_identity=None) -> dict:
        pixels=self._validated_frame(frame);height,width=pixels.shape[:2];raw=pixels.tobytes(order="C")
        self.stats.checksum_calls+=1;checksum=sha256(raw).hexdigest()
        key=(cache_identity,width,height,checksum,ENCODING,self.compression_level)
        cached=self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key);self.stats.cache_hits+=1;return dict(cached)
        self.stats.cache_misses+=1;self.stats.encode_calls+=1
        encoded=base64.b64encode(zlib.compress(raw,self.compression_level)).decode("ascii")
        payload={
            "encoding":ENCODING,"width":width,"height":height,"channels":4,
            "dtype":"uint8","byte_length":len(raw),"checksum":checksum,"data":encoded,
        }
        self._put(key,payload);return dict(payload)

    def decode(self,payload,expected_width: int|None=None,expected_height: int|None=None,cache_identity=None) -> np.ndarray:
        if not isinstance(payload,dict):
            pixels=np.asarray(payload,dtype=np.uint8)
            if pixels.ndim!=3 or pixels.shape[2:]!=(4,):raise FramePayloadError("invalid legacy RGBA pixel shape")
            if expected_width is not None and pixels.shape[1]!=int(expected_width):raise FramePayloadError("pixel width does not match its owner")
            if expected_height is not None and pixels.shape[0]!=int(expected_height):raise FramePayloadError("pixel height does not match its owner")
            return np.ascontiguousarray(pixels)
        if payload.get("encoding")!=ENCODING:raise FramePayloadError("unsupported pixel payload encoding")
        try:
            width=int(payload["width"]);height=int(payload["height"]);channels=int(payload["channels"])
            byte_length=int(payload["byte_length"]);dtype=str(payload["dtype"]);checksum=str(payload["checksum"]);encoded=str(payload["data"])
        except (KeyError,TypeError,ValueError) as exc:raise FramePayloadError("invalid pixel payload metadata") from exc
        expected=width*height*4
        if width<1 or height<1 or width>MAX_DIMENSION or height>MAX_DIMENSION or expected>MAX_DECODED_BYTES:raise FramePayloadError("pixel payload exceeds the safe decode limit")
        if channels!=4 or dtype!="uint8" or byte_length!=expected:raise FramePayloadError("pixel payload shape or byte length is invalid")
        if expected_width is not None and width!=int(expected_width):raise FramePayloadError("pixel width does not match its owner")
        if expected_height is not None and height!=int(expected_height):raise FramePayloadError("pixel height does not match its owner")
        if len(encoded)>((expected+65536)*4//3+8):raise FramePayloadError("encoded pixel payload exceeds the safe limit")
        try:compressed=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError) as exc:raise FramePayloadError("pixel payload contains invalid base64") from exc
        if len(compressed)>expected+65536:raise FramePayloadError("compressed pixel payload exceeds the safe limit")
        try:
            decoder=zlib.decompressobj();raw=decoder.decompress(compressed,expected+1)
            if decoder.unconsumed_tail:raise FramePayloadError("pixel payload decompressed size is invalid")
            raw+=decoder.flush(max(1,expected+1-len(raw)))
        except zlib.error as exc:raise FramePayloadError("pixel payload decompression failed") from exc
        if not decoder.eof or decoder.unused_data or len(raw)!=expected:raise FramePayloadError("pixel payload decompressed size is invalid")
        self.stats.checksum_calls+=1
        if sha256(raw).hexdigest()!=checksum:raise FramePayloadError("pixel payload checksum does not match")
        self.stats.decode_calls+=1
        pixels=np.frombuffer(raw,dtype=np.uint8).reshape((height,width,4)).copy()
        key=(cache_identity,width,height,checksum,ENCODING,self.compression_level);self._put(key,dict(payload))
        return pixels

    def _put(self,key: tuple,payload: dict) -> None:
        previous=self._cache.pop(key,None)
        if previous is not None:self.current_cache_bytes-=len(previous["data"])
        self._cache[key]=payload;self.current_cache_bytes+=len(payload["data"])
        while self.current_cache_bytes>self.maximum_cache_bytes and len(self._cache)>1:
            _,removed=self._cache.popitem(last=False);self.current_cache_bytes-=len(removed["data"])

    def clear(self) -> None:
        self._cache.clear();self.current_cache_bytes=0

    def reset_stats(self) -> None:self.stats=CodecStats()


DEFAULT_FRAME_PAYLOAD_CODEC=SourceFramePayloadCodec()

import os
import sys
import zlib
import struct
import random
import subprocess


MODE_LENGTH = 0
MODE_CHUNK_TYPE = 1
MODE_CHUNK_DATA_VALID_CRC = 2
MODE_CHUNK_DATA_INVALID_CRC = 3
MODE_CRC = 4


def png_fuzz(seed, mode):
    with open(seed, 'rb') as f:
        buf = f.read()

    with open('bomb.png', 'wb') as f:
        f.write(buf[0:8])
        idx = 8  # PNG Header is 8 byte - 89 50 4E 47 0D 0A 1A 0A
        while idx < len(buf):
            tup = get_png_next_chunk(buf, idx)
            length = tup[1]
            chunk_type = tup[2]
            chunk_data = tup[3]
            crc32 = tup[4]
            if mode == MODE_LENGTH:
                length = mutate_length(tup[1])
            elif mode == MODE_CHUNK_TYPE:
                chunk_type = mutate_chunk_type(tup[2])
            elif mode == MODE_CHUNK_DATA_VALID_CRC:
                chunk_data = mutate_chunk(tup[3])
                crc32 = calc_crc32(chunk_data)
            elif mode == MODE_CHUNK_DATA_INVALID_CRC:
                chunk_data = mutate_chunk(tup[3])
            else:
                crc32 = mutate_crc(tup[3])
            idx = tup[0]
            f.write(length)
            f.write(chunk_type)
            f.write(chunk_data)
            f.write(crc32)


def get_png_next_chunk(buf, idx):
    """
    PNG Chunk Struct
    Length - 4
    ChunkType - 4
    ChunkData - Length
    CRC - 4
    """
    length_bytes = buf[idx:idx + 4]
    length_int = struct.unpack('>i', length_bytes)[0]
    idx += 4
    chunk_type = buf[idx:idx + 4]
    idx += 4
    chunk_data = buf[idx:idx + length_int]
    idx += length_int
    crc32 = buf[idx:idx + 4]
    idx += 4
    return idx, length_bytes, chunk_type, chunk_data, crc32


def mutate_length(buf):
    length = struct.unpack_from('>i', buf)[0]
    return uint32_to_bytes(int(length * random.SystemRandom().uniform(0.5, 1.5)))


def mutate_chunk_type(chunk_type):
    """
    각 바이트의 5번째 bit는 대소문자를 결정지으며, 각자 의미가 담겨 있다.
    0 - 대문자, 1 - 소문자
    
    Byte 1
    0 - 중요, 1 - 보조 
    
    Byte 2
    0 - 스펙에 있는 청크, 1 - 프로그램 개별 정의 청크
    
    Byte 4
    0 - 복사 불가, 1 - 복사 가능
    
    이 함수에선 청크의 5번째 bit를 조절한다.
    """
    for i in range(4):
        action = random.SystemRandom().randint(0, 5)
        if action == 0:
            chunk_type[i] = chunk_type[i] & 0x11101111  # 20% = Set to Uppercase
        elif action == 1:
            chunk_type[i] = chunk_type[i] | 0x00010000  # 20% = Set to Lowercase
        # 60% = do nothing
    return chunk_type


def mutate_chunk(chunk_data):
    new_chunk = {}
    data_idx = 0
    new_idx = 0
    action = random.SystemRandom().randint(1, 1000)
    while data_idx < len(chunk_data):
        if 0 < action <= 20:  # mutate
            new_chunk[new_idx] = ord(random.SystemRandom().randint(0, 255))
            data_idx += 1
            new_idx += 1
        elif 20 < action <= 22:  # Insert
            new_chunk[new_idx] = chunk_data[data_idx]
            new_chunk[new_idx + 1] = ord(random.SystemRandom().randint(0, 255))
            data_idx += 1
            new_idx += 2
        elif 22 < action <= 24:  # Drop
            data_idx += 1
        else:
            new_chunk[new_idx] = chunk_data[data_idx]
            data_idx += 1
            new_idx += 1
    return new_chunk


def calc_crc32(chunk_data):
    crc32_uint32 = zlib.crc32(chunk_data)
    crc32_bytes = uint32_to_bytes(crc32_uint32)
    return crc32_bytes


def mutate_crc(chunk_data):
    crc32_uint32 = zlib.crc32(chunk_data)
    crc32_bytes = uint32_to_bytes(crc32_uint32)

    for i in range(4):
        action = random.SystemRandom().randint(0, 1)
        if action == 0:
            crc32_bytes[i] = ord(random.SystemRandom().randint(0, 255))

    return crc32_bytes


def uint32_to_bytes(uint32):
    #converted_bytes = [
    #    uint32 / (0x100 * 0x100 * 0x100),
    #    uint32 / (0x100 * 0x100),
    #    uint32 / 0x100,
    #    uint32 % 0x100,
    #]
    return uint32.to_bytes(4, byteorder='big')


def main():
    exe_path = '\"C:\Program Files\Honeyview\Honeyview.exe\"'
    png_fuzz('seed.png', MODE_LENGTH)
    command = '{} {}'.format(exe_path, 'bomb.png')
    try:
        # result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        # result = subprocess.Popen(command, stderr=subprocess.STDOUT, shell=True)
        proc = subprocess.Popen(command,  stderr=subprocess.STDOUT, shell=True)
        out, err = proc.communicate()
        print(out, err, proc.returncode)
    except subprocess.CalledProcessError as e:
        print("Error:", e)


if __name__ == '__main__':
    main()

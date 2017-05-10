#!/usr/bin/env python3

import os
import sys
import zlib
import struct
import random
import subprocess
import signal
try:
    import src.config as conf
except ModuleNotFoundError:
    import config as conf


MODE_LENGTH = 0
MODE_CHUNK_TYPE = 1
MODE_CHUNK_DATA_VALID_CRC = 2
MODE_CHUNK_DATA_VALID_CRC_PRESERVE_LENGTH = 3
MODE_CHUNK_TYPE_DATA_VALID_CRC_PRESERVE_LENGTH = 4
MODE_CHUNK_DATA_INVALID_CRC = 5
MODE_CRC = 6


def png_fuzz(seed, fileout):
    with open(seed, 'rb') as f:
        buf = f.read()

    with open(fileout, 'wb') as f:
        f.write(buf[0:8])
        idx = 8  # PNG Header is 8 byte - 89 50 4E 47 0D 0A 1A 0A
        while idx < len(buf):
            mode = random.SystemRandom().randint(0, 4)

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
            elif mode == MODE_CHUNK_DATA_VALID_CRC_PRESERVE_LENGTH:
                chunk_data = mutate_chunk_preserve_length(tup[3])
            elif mode == MODE_CHUNK_TYPE_DATA_VALID_CRC_PRESERVE_LENGTH:
                chunk_type = mutate_chunk_type(tup[2])
                chunk_data = mutate_chunk_preserve_length(tup[3])
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
        new_type = []
        action = random.SystemRandom().randint(0, 5)
        if action == 0:
            new_type.append(bytes([chunk_type[i] & int('11101111', 2)]))  # 20% = Set to Uppercase
        elif action == 1:
            new_type.append(bytes([chunk_type[i] | int('00010000', 2)]))  # 20% = Set to Lowercase
        # 60% = do nothing
    return b''.join(new_type)


def mutate_chunk(chunk_data):
    new_chunk = []
    data_idx = 0
    action = random.SystemRandom().randint(1, 100)
    while data_idx < len(chunk_data):
        if 0 < action <= 10:  # mutate
            new_chunk.append(bytes([random.SystemRandom().randint(0, 255)]))
            data_idx += 1
        elif 10 < action <= 20:  # Insert
            new_chunk.append(bytes([chunk_data[data_idx]]))
            new_chunk.append(bytes([random.SystemRandom().randint(0, 255)]))
            data_idx += 1
        elif 20 < action <= 30:  # Drop
            data_idx += 1
        else:
            new_chunk.append(bytes([chunk_data[data_idx]]))
            data_idx += 1
    return b''.join(new_chunk)


def mutate_chunk_preserve_length(chunk_data):
    new_chunk = []
    data_idx = 0
    action = random.SystemRandom().randint(1, 100)
    while data_idx < len(chunk_data):
        if 0 < action <= 5:  # mutate
            new_chunk.append(bytes([random.SystemRandom().randint(0, 255)]))
            data_idx += 1
        else:
            new_chunk.append(bytes([chunk_data[data_idx]]))
            data_idx += 1
    return b''.join(new_chunk)


def calc_crc32(chunk_data):
    crc32_uint32 = zlib.crc32(chunk_data)
    crc32_bytes = uint32_to_bytes(crc32_uint32)
    return crc32_bytes


def mutate_crc(chunk_data):
    crc32_uint32 = zlib.crc32(chunk_data)
    crc32_bytes = uint32_to_bytes(crc32_uint32)

    new_crc32 = []
    for i in range(4):
        action = random.SystemRandom().randint(0, 1)
        if action == 0:
            new_crc32.append(bytes([random.SystemRandom().randint(0, 255)]))

    return b''.join(new_crc32)


def uint32_to_bytes(uint32):
    return uint32.to_bytes(4, byteorder='big')


def driver(exe_path, src_file, iteration):
    os.makedirs(os.path.abspath('gen'), exist_ok=True)
    with open('log.txt', 'w') as f:
        for i in range(iteration):
            fileout = os.path.abspath('gen/bomb{}.png'.format(i))
            png_fuzz(src_file, fileout)
            command = '{} \"{}\"'.format(exe_path, fileout)
            try:
                proc = subprocess.Popen(command, stderr=subprocess.STDOUT, shell=True)
                out, err = proc.communicate(timeout=1)
                msg = "[{}] Crash {}".format(i, os.path.basename(fileout))
                print(msg)
                f.write(msg)
                f.write('\n')
                f.flush()
            except subprocess.TimeoutExpired:
                # os.kill(proc.pid, signal.SIGINT)
                os.system("taskkill /f /im {}".format(os.path.basename(conf.EXECUTABLE_PATH)))  # Windows용 임시방편
                msg = "[{}] Failure {}".format(i, os.path.basename(fileout))
                print(msg)
                f.write(msg)
                f.write('\n')
                f.flush()
            except subprocess.CalledProcessError as e:
                msg = "[{}] Error: {} {}".format(i, e, os.path.basename(fileout))
                print(msg)
                f.write(msg)
                f.write('\n')
                f.flush()


def main():
    exe_path = conf.EXECUTABLE_PATH
    src_file = conf.SOURCE_FILE
    iteration = conf.ITERATION
    driver(exe_path, src_file, iteration)


if __name__ == '__main__':
    main()

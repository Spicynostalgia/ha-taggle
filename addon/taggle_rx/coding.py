"""Rate-1/2 K=7 channel coding and MSB-first CRC-8."""
import numpy as np


def convolution_encode(bits, generators=(0x6d, 0x4f)):
    state = 0; out = []
    for bit in bits:
        reg = (state << 1) | int(bit)
        out.extend((reg & g).bit_count() % 2 for g in generators)
        state = reg & 63
    return np.array(out, np.uint8)


def convolution_decode_exact(bits):
    """Invert the systematic recurrence, then check the second output.

    A violation is explicitly a failure. Any Viterbi fallback must still
    pass the independent frame and header checksums.
    Generator convention: newest input is register bit 0, shift left, emit
    parity(reg & 0x6d) then parity(reg & 0x4f), retain six state bits.
    """
    if len(bits) % 2:
        raise ValueError('odd convolutional symbol count')
    state = 0; out = []; violations = 0
    for i in range(0, len(bits), 2):
        bit = int(bits[i]) ^ (((state << 1) & 0x6d).bit_count() % 2)
        reg = (state << 1) | bit
        violations += ((reg & 0x4f).bit_count() % 2) != bits[i+1]
        out.append(bit); state = reg & 63
    return np.array(out, np.uint8), int(violations), state


def convolution_decode_viterbi(bits):
    """Hard-decision K=7 decoder with zero initial/terminal states.

    Returns decoded bits and the actual number of corrected coded symbols.
    A checksum remains mandatory; a trellis winner is not a validated frame.
    """
    bits = np.asarray(bits, np.uint8)
    if len(bits) % 2:
        raise ValueError('odd convolutional symbol count')
    states = np.arange(64)
    predecessors = np.stack((states >> 1, (states >> 1) | 32))
    registers = (predecessors << 1) | (states & 1)
    outputs = np.array([[[int(r & g).bit_count() & 1 for g in (0x6d, 0x4f)]
                         for r in row] for row in registers], np.uint8)
    metric = np.full(64, 10000, np.int32); metric[0] = 0
    history = []
    for pair in bits.reshape(-1, 2):
        cost = metric[predecessors] + np.sum(outputs != pair, axis=2)
        choice = np.argmin(cost, axis=0)
        history.append(predecessors[choice, states])
        metric = cost[choice, states]
    state = 0; decoded = []
    for previous in reversed(history):
        decoded.append(state & 1)
        state = int(previous[state])
    return np.array(decoded[::-1], np.uint8), int(metric[0])


def crc_bits(bits, width, poly, initial=0):
    value = initial; mask = (1 << width)-1
    for bit in bits:
        top = (value >> (width-1)) ^ int(bit)
        value = (value << 1) & mask
        if top:
            value ^= poly
    return value


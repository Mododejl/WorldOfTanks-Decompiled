# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/common/Lib/encodings/cp862.py
import codecs

class Codec(codecs.Codec):

    def encode(self, input, errors='strict'):
        return codecs.charmap_encode(input, errors, encoding_map)

    def decode(self, input, errors='strict'):
        return codecs.charmap_decode(input, errors, decoding_table)


class IncrementalEncoder(codecs.IncrementalEncoder):

    def encode(self, input, final=False):
        return codecs.charmap_encode(input, self.errors, encoding_map)[0]


class IncrementalDecoder(codecs.IncrementalDecoder):

    def decode(self, input, final=False):
        return codecs.charmap_decode(input, self.errors, decoding_table)[0]


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


def getregentry():
    return codecs.CodecInfo(name='cp862', encode=Codec().encode, decode=Codec().decode, incrementalencoder=IncrementalEncoder, incrementaldecoder=IncrementalDecoder, streamreader=StreamReader, streamwriter=StreamWriter)


decoding_map = codecs.make_identity_dict(range(256))
decoding_map.update({128: 1488,
 129: 1489,
 130: 1490,
 131: 1491,
 132: 1492,
 133: 1493,
 134: 1494,
 135: 1495,
 136: 1496,
 137: 1497,
 138: 1498,
 139: 1499,
 140: 1500,
 141: 1501,
 142: 1502,
 143: 1503,
 144: 1504,
 145: 1505,
 146: 1506,
 147: 1507,
 148: 1508,
 149: 1509,
 150: 1510,
 151: 1511,
 152: 1512,
 153: 1513,
 154: 1514,
 155: 162,
 156: 163,
 157: 165,
 158: 8359,
 159: 402,
 160: 225,
 161: 237,
 162: 243,
 163: 250,
 164: 241,
 165: 209,
 166: 170,
 167: 186,
 168: 191,
 169: 8976,
 170: 172,
 171: 189,
 172: 188,
 173: 161,
 174: 171,
 175: 187,
 176: 9617,
 177: 9618,
 178: 9619,
 179: 9474,
 180: 9508,
 181: 9569,
 182: 9570,
 183: 9558,
 184: 9557,
 185: 9571,
 186: 9553,
 187: 9559,
 188: 9565,
 189: 9564,
 190: 9563,
 191: 9488,
 192: 9492,
 193: 9524,
 194: 9516,
 195: 9500,
 196: 9472,
 197: 9532,
 198: 9566,
 199: 9567,
 200: 9562,
 201: 9556,
 202: 9577,
 203: 9574,
 204: 9568,
 205: 9552,
 206: 9580,
 207: 9575,
 208: 9576,
 209: 9572,
 210: 9573,
 211: 9561,
 212: 9560,
 213: 9554,
 214: 9555,
 215: 9579,
 216: 9578,
 217: 9496,
 218: 9484,
 219: 9608,
 220: 9604,
 221: 9612,
 222: 9616,
 223: 9600,
 224: 945,
 225: 223,
 226: 915,
 227: 960,
 228: 931,
 229: 963,
 230: 181,
 231: 964,
 232: 934,
 233: 920,
 234: 937,
 235: 948,
 236: 8734,
 237: 966,
 238: 949,
 239: 8745,
 240: 8801,
 241: 177,
 242: 8805,
 243: 8804,
 244: 8992,
 245: 8993,
 246: 247,
 247: 8776,
 248: 176,
 249: 8729,
 250: 183,
 251: 8730,
 252: 8319,
 253: 178,
 254: 9632,
 255: 160})
decoding_table = u'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\x7f\u05d0\u05d1\u05d2\u05d3\u05d4\u05d5\u05d6\u05d7\u05d8\u05d9\u05da\u05db\u05dc\u05dd\u05de\u05df\u05e0\u05e1\u05e2\u05e3\u05e4\u05e5\u05e6\u05e7\u05e8\u05e9\u05ea\xa2\xa3\xa5\u20a7\u0192\xe1\xed\xf3\xfa\xf1\xd1\xaa\xba\xbf\u2310\xac\xbd\xbc\xa1\xab\xbb\u2591\u2592\u2593\u2502\u2524\u2561\u2562\u2556\u2555\u2563\u2551\u2557\u255d\u255c\u255b\u2510\u2514\u2534\u252c\u251c\u2500\u253c\u255e\u255f\u255a\u2554\u2569\u2566\u2560\u2550\u256c\u2567\u2568\u2564\u2565\u2559\u2558\u2552\u2553\u256b\u256a\u2518\u250c\u2588\u2584\u258c\u2590\u2580\u03b1\xdf\u0393\u03c0\u03a3\u03c3\xb5\u03c4\u03a6\u0398\u03a9\u03b4\u221e\u03c6\u03b5\u2229\u2261\xb1\u2265\u2264\u2320\u2321\xf7\u2248\xb0\u2219\xb7\u221a\u207f\xb2\u25a0\xa0'
encoding_map = {0: 0,
 1: 1,
 2: 2,
 3: 3,
 4: 4,
 5: 5,
 6: 6,
 7: 7,
 8: 8,
 9: 9,
 10: 10,
 11: 11,
 12: 12,
 13: 13,
 14: 14,
 15: 15,
 16: 16,
 17: 17,
 18: 18,
 19: 19,
 20: 20,
 21: 21,
 22: 22,
 23: 23,
 24: 24,
 25: 25,
 26: 26,
 27: 27,
 28: 28,
 29: 29,
 30: 30,
 31: 31,
 32: 32,
 33: 33,
 34: 34,
 35: 35,
 36: 36,
 37: 37,
 38: 38,
 39: 39,
 40: 40,
 41: 41,
 42: 42,
 43: 43,
 44: 44,
 45: 45,
 46: 46,
 47: 47,
 48: 48,
 49: 49,
 50: 50,
 51: 51,
 52: 52,
 53: 53,
 54: 54,
 55: 55,
 56: 56,
 57: 57,
 58: 58,
 59: 59,
 60: 60,
 61: 61,
 62: 62,
 63: 63,
 64: 64,
 65: 65,
 66: 66,
 67: 67,
 68: 68,
 69: 69,
 70: 70,
 71: 71,
 72: 72,
 73: 73,
 74: 74,
 75: 75,
 76: 76,
 77: 77,
 78: 78,
 79: 79,
 80: 80,
 81: 81,
 82: 82,
 83: 83,
 84: 84,
 85: 85,
 86: 86,
 87: 87,
 88: 88,
 89: 89,
 90: 90,
 91: 91,
 92: 92,
 93: 93,
 94: 94,
 95: 95,
 96: 96,
 97: 97,
 98: 98,
 99: 99,
 100: 100,
 101: 101,
 102: 102,
 103: 103,
 104: 104,
 105: 105,
 106: 106,
 107: 107,
 108: 108,
 109: 109,
 110: 110,
 111: 111,
 112: 112,
 113: 113,
 114: 114,
 115: 115,
 116: 116,
 117: 117,
 118: 118,
 119: 119,
 120: 120,
 121: 121,
 122: 122,
 123: 123,
 124: 124,
 125: 125,
 126: 126,
 127: 127,
 160: 255,
 161: 173,
 162: 155,
 163: 156,
 165: 157,
 170: 166,
 171: 174,
 172: 170,
 176: 248,
 177: 241,
 178: 253,
 181: 230,
 183: 250,
 186: 167,
 187: 175,
 188: 172,
 189: 171,
 191: 168,
 209: 165,
 223: 225,
 225: 160,
 237: 161,
 241: 164,
 243: 162,
 247: 246,
 250: 163,
 402: 159,
 915: 226,
 920: 233,
 931: 228,
 934: 232,
 937: 234,
 945: 224,
 948: 235,
 949: 238,
 960: 227,
 963: 229,
 964: 231,
 966: 237,
 1488: 128,
 1489: 129,
 1490: 130,
 1491: 131,
 1492: 132,
 1493: 133,
 1494: 134,
 1495: 135,
 1496: 136,
 1497: 137,
 1498: 138,
 1499: 139,
 1500: 140,
 1501: 141,
 1502: 142,
 1503: 143,
 1504: 144,
 1505: 145,
 1506: 146,
 1507: 147,
 1508: 148,
 1509: 149,
 1510: 150,
 1511: 151,
 1512: 152,
 1513: 153,
 1514: 154,
 8319: 252,
 8359: 158,
 8729: 249,
 8730: 251,
 8734: 236,
 8745: 239,
 8776: 247,
 8801: 240,
 8804: 243,
 8805: 242,
 8976: 169,
 8992: 244,
 8993: 245,
 9472: 196,
 9474: 179,
 9484: 218,
 9488: 191,
 9492: 192,
 9496: 217,
 9500: 195,
 9508: 180,
 9516: 194,
 9524: 193,
 9532: 197,
 9552: 205,
 9553: 186,
 9554: 213,
 9555: 214,
 9556: 201,
 9557: 184,
 9558: 183,
 9559: 187,
 9560: 212,
 9561: 211,
 9562: 200,
 9563: 190,
 9564: 189,
 9565: 188,
 9566: 198,
 9567: 199,
 9568: 204,
 9569: 181,
 9570: 182,
 9571: 185,
 9572: 209,
 9573: 210,
 9574: 203,
 9575: 207,
 9576: 208,
 9577: 202,
 9578: 216,
 9579: 215,
 9580: 206,
 9600: 223,
 9604: 220,
 9608: 219,
 9612: 221,
 9616: 222,
 9617: 176,
 9618: 177,
 9619: 178,
 9632: 254}

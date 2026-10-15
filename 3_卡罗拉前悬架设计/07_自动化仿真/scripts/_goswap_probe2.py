import struct

p = r'C:/Users/dth15/Desktop/ANSYS/v3_run_GOSWAP/resG0.disp'
raw = open(p, 'rb').read()

start_guess = 108 + 44412 * 24
print("guess entity start:", start_guess)
for k in range(12):
    off = start_guess + k * 24
    vals = struct.unpack_from('<3d', raw, off)
    print(k, [round(v, 5) for v in vals])

print()
print("=== search for 1.0 doubles in tail region ===")
a = 108 + 44100 * 24
b = 108 + 44764 * 24
hits = []
off = a
while off < b:
    v = struct.unpack_from('<d', raw, off)[0]
    if abs(v - 1.0) < 1e-9:
        hits.append(off)
    off += 8
print("hits count:", len(hits))
for h in hits[:40]:
    print("  off", h, "pt_idx", round((h - 108) / 24.0, 3))

print()
print("=== dump first 20 rows of triple-doubles from entity start guess ===")
for k in range(20):
    off = start_guess + k * 24
    vals = struct.unpack_from('<3d', raw, off)
    print(k, [round(v, 4) for v in vals])

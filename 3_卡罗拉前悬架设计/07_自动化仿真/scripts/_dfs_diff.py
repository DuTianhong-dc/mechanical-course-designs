# -*- coding: utf-8 -*-
r"""对比 file_GOSWAP.dfs (22:16) vs file_GOSWAP_v2.dfs (22:40) 的字节差异"""
import io

A = r'C:/Users/dth15/Desktop/ANSYS/automation/outbox/file_GOSWAP.dfs'
B = r'C:/Users/dth15/Desktop/ANSYS/automation/outbox/file_GOSWAP_v2.dfs'

a = open(A, 'rb').read()
b = open(B, 'rb').read()
print("sizes:", len(a), len(b))

diffs = []
n = min(len(a), len(b))
for i in range(n):
    if a[i] != b[i]:
        diffs.append(i)

print("diff count:", len(diffs))

if diffs:
    ranges = []
    s = diffs[0]
    p = diffs[0]
    for x in diffs[1:]:
        if x - p <= 16:  # merge close diffs
            p = x
        else:
            ranges.append((s, p))
            s = x
            p = x
    ranges.append((s, p))
    print("n ranges (gap<=16):", len(ranges))
    for r in ranges[:40]:
        print("  offset %d..%d (len %d)" % (r[0], r[1], r[1] - r[0] + 1))

    i0 = diffs[0]
    lo = max(0, i0 - 30)
    print()
    print("first diff context A:", a[lo:i0 + 30])
    print("first diff context B:", b[lo:i0 + 30])
else:
    print("identical")

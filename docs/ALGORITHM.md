# Algorithm

The projection algorithm of the assignment, rewritten with the design decisions of the [SRS](SRS.md) (section 5).
Numbers in brackets, e.g. [D4], refer to those decisions.

## Input
- `M`: a 3D volume of size `sx * sy * sz`, accessed as `M[x][y][z]` (index coordinates [D6]).
- A valid plane (checked before the algorithm, [D9]):
  - triangle `a, b, c`, or
  - trapezoid `a', a'', b, c` with legs `a'->b` and `a''->c` [D10].

## Output
- `E`: a 2D image stored as `E[y][x]`; row 0 is the top (`a`), column 0 is the `b` side [D7].

## Helper functions
```
round_half_up(v) = floor(v + 0.5)                           # 2.5 -> 3 [D2]

sample(M, p):                                               # nearest neighbour [D1]
    (i, j, k) = (round_half_up(p.x), round_half_up(p.y), round_half_up(p.z))
    if 0 <= i < sx and 0 <= j < sy and 0 <= k < sz:
        return M[i][j][k]
    return 0                                                # outside M
```

## Algorithm
```
# 1. Start points of the two legs
if triangle:  start1 = a,   start2 = a
if trapezoid: start1 = a',  start2 = a''

# 2. Lengths and unit vectors
Dab  = dist(start1, b)                          # = dist(start2, c) within TOLERANCE [D9]
Dbc  = dist(b, c)
Dmax = max(Dbc, dist(start1, start2))           # longer parallel edge (0 for a triangle)
v_ab = (b - start1) / Dab
v_ac = (c - start2) / Dab

# 3. Output image
H = floor(Dab) + 1                              # rows: distances 0 .. floor(Dab) [D3, D4]
W = round_half_up(Dmax) + 1                     # columns [D2, D3]
E = H x W image filled with 0

# 4. Sweep the plane row by row
for y = 0 .. H - 1:
    a1  = start1 + y * v_ab                     # computed directly, no accumulated error
    a2  = start2 + y * v_ac                     # sample first, then step [D4]
    d12 = dist(a1, a2)

    if d12 < EPSILON:                           # single-point row, e.g. the apex [D5]
        E[y][round_half_up(Dmax / 2)] = sample(M, a1)
        continue

    dp = (a2 - a1) / d12                        # unit step along the row
    for x1 = 0 .. floor(d12):
        p = a1 + x1 * dp
        x = round_half_up(Dmax / 2 - d12 / 2 + x1)      # centre the row [D2]
        E[y][x] = sample(M, p)

return E
```

## Differences from the original algorithm
| Original | Here | Why |
|----------|------|-----|
| `M[p]` with non-integer `p` | `sample(M, p)`, nearest voxel, 0 outside `M` | [D1] |
| `x` not an integer | `round_half_up` | [D2] |
| size `Dab * Dbc` | `(floor(Dab) + 1) x (round(Dmax) + 1)` | [D3], fits every row |
| step, then sample (apex missing) | sample, then step (apex included) | [D4] |
| `dp = .../d12` with `d12 = 0` | single-point row | [D5] |
| `E[x][y]` | `E[y][x]` | [D7] |
| `a1 = a1 + v(ab)` repeated | `a1 = start1 + y * v_ab` | avoids accumulated floating-point error |
| width from `Dbc` | width from `Dmax` | a trapezoid whose top edge is longer than its base |

## Complexity
Every pixel of `E` is sampled once: `O(H * W)` per plane, independent of the size of `M`.
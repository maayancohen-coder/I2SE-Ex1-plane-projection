# Results

Machine: Windows 11, Intel64 Family 6 Model 154 Stepping 4, GenuineIntel, Python 3.15.0, numpy 2.5.4

100 sweep planes per volume (experiments/planes/), reference on the first 3.

| Volume | Size | Type | Fast fps | Reference fps | Speed-up | Trilinear fps | Mean diff (0-255) | PSNR (dB) | Ex0.py |
|---|---|---|---|---|---|---|---|---|---|
| biscuit_cake | 256x256x130 | uint16 | 295 | 12.86 | 23x | 113 | 1.83 | 34.9 | 404 fps |
| croissant | 500x500x500 | uint8 | 52 | 2.88 | 18x | 18 | 2.35 | 31.0 | 52 fps |
| MRHead | 256x256x130 | int16 | 507 | 12.70 | 40x | 140 | 3.10 | 31.5 | 331 fps |
| onion | 256x256x130 | uint8 | 564 | 12.29 | 46x | 134 | 2.58 | 32.5 | 336 fps |
| swiss_roll | 256x256x130 | uint32 | 533 | 12.57 | 42x | 119 | 2.54 | 31.2 | 340 fps |

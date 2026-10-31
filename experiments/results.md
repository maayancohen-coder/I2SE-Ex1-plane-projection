# Results

Machine: Windows 11, Intel64 Family 6 Model 154 Stepping 4, GenuineIntel, Python 3.15.0, numpy 2.5.4

100 sweep planes per volume (experiments/planes/), reference on the first 3.

| Volume | Size | Type | Fast fps | Reference fps | Speed-up | Trilinear fps | Mean diff (0-255) | PSNR (dB) | Ex0.py |
|---|---|---|---|---|---|---|---|---|---|
| biscuit_cake | 256x256x130 | uint16 | 410 | 8.84 | 46x | 127 | 1.83 | 34.9 | 406 fps |
| croissant | 500x500x500 | uint8 | 161 | 2.46 | 65x | 18 | 2.35 | 31.0 | 142 fps |
| MRHead | 256x256x130 | int16 | 649 | 11.62 | 56x | 197 | 3.10 | 31.5 | 414 fps |
| onion | 256x256x130 | uint8 | 662 | 12.66 | 52x | 188 | 2.58 | 32.5 | 429 fps |
| swiss_roll | 256x256x130 | uint32 | 637 | 11.78 | 54x | 178 | 2.54 | 31.2 | 397 fps |

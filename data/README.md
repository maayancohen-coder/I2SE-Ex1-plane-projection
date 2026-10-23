# Dataset

NRRD files are not committed (see `.gitignore`). Place them in this folder locally.
The course files (biscuit_cake, onion, croissant, swiss_roll) are available here: [course dataset](https://1drv.ms/f/c/c735514f37d70398/IgAEKwMnF60VQ5PbFmCLCiuQAVAnr5XcB54ssGT9yccdzog?e=T5XGS8).
MRHead is available from the 3D Slicer sample data.

| File | Size (voxels) | Type | Spacing | Source | Why |
|------|---------------|------|---------|--------|-----|
| `MRHead.nrrd` | 256 x 256 x 130 | int16 (short) | 1, 1, 1.3 | 3D Slicer sample data | the reference file of the assignment |
| `biscuit_cake.nrrd` | 256 x 256 x 130 | uint16 | 1, 1, 1.3 | Course dataset, prepared by Aviya Cohen at the lecturer's request | unsigned 16-bit values |
| `onion.nrrd` | 256 x 256 x 130 | uint8 | 0.55, 0.55, 0.715 | Course dataset, prepared by Aviya Cohen at the lecturer's request | non-uniform spacing |
| `croissant.nrrd` | 500 x 500 x 500 | uint8 | 0.37 | Course dataset, prepared by Aviya Cohen at the lecturer's request | performance benchmark (500^3) |
| `swiss_roll.nrrd` | 256 x 256 x 130 | uint32 | 1.1, 1.1, 1.43 | Course dataset, prepared by Aviya Cohen at the lecturer's request | unsigned 32-bit values |

Generate the phantom:

```
python data/make_phantom.py data/phantom_knot.nrrd 200
```

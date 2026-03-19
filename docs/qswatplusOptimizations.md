# QSWAT+ Performance Optimizations

Changes made to QSWAT+ plugin source code in `resources/QSWATPlus/` for the CoSWAT-Framework. These should be ported to the next QSWAT+ version.

## 1. Floodplain Calculation — Vectorized numpy (`floodplain.py`)

### `calcFloodPlain1Parallel` (line ~668)

**Before:** Python double-nested loop over every pixel, multiprocessing with per-pixel tuple results, per-pixel `self.floodplainRaster.write(row, col, value)`.

**After:** Reads ridge and valley arrays once with `ReadAsArray()`, computes slope position with vectorized numpy ops, writes entire result with `WriteArray()`. No loops, no multiprocessing overhead.

```python
# core computation — 3 lines replace ~50 lines of loops
valid       = (ridge_array != self.noData) & (valley_array != self.noData)
denominator = ridge_array + valley_array
sp          = numpy.where(valid & (denominator != 0), valley_array / denominator, 0.0)
result      = numpy.full(ridge_array.shape, self.noData, dtype=numpy.float64)
result[valid & (sp <= self.floodThresh)] = 1
self.floodplainRaster.band.WriteArray(result)
```

**Speedup:** ~100-1000x. Eliminates per-pixel Python overhead, process serialization, and per-pixel GDAL writes.

### `_compute_floodplain_chunk` (line ~47, top-level function)

**Before:** Python loops over rows/cols, returns list of `(row, col, value)` tuples.

**After:** Vectorized numpy, returns `(start_row, result_array, valid_mask)`. Kept for backward compatibility but no longer called from the main path since `calcFloodPlain1Parallel` now does everything in one shot.

---

## 2. Ridge Heights by Inversion — numpy Array Access (`floodplain.py`)

### `calcRidgeHeightsByInversion` (line ~302)

**Before:** Per-pixel `self.demRaster.read(row, col)`, `ridgepRaster.read(row, col)`, `ridgesRaster.read(row, col)` — each call goes through GDAL C API, Python object creation, type conversion. Called millions of times. Results written with per-pixel `self.ridgeHeightsRaster.write(row, col, value)`.

**After:** All three rasters read into numpy arrays upfront with `ReadAsArray()`. Path tracing loop uses `arr[row, col]` (nanosecond numpy indexing) instead of `raster.read(row, col)` (microsecond GDAL call). Skips already-computed pixels early. Results written in one `WriteArray()` call.

```python
# read once
demArr  = self.demRaster.band.ReadAsArray().astype(numpy.float64)
dirArr  = ridgepRaster.band.ReadAsArray().astype(numpy.float64)
accArr  = ridgesRaster.band.ReadAsArray().astype(numpy.float64)
heightsArr = numpy.full((numRows, numCols), -1.0, dtype=numpy.float64)

# trace paths using array indexing (fast)
for row in range(numRows):
    for col in range(numCols):
        if heightsArr[row, col] >= 0: continue  # already computed
        # ... trace path using arr[r, c] instead of raster.read(r, c) ...

# write once
self.ridgeHeightsRaster.band.WriteArray(heightsArr)
```

**Speedup:** ~10-50x. The path-tracing algorithm is inherently sequential (each pixel follows a flow path), so it can't be fully vectorized. But replacing per-pixel GDAL read/write with numpy array indexing eliminates the dominant overhead.

**Removed methods:** `valueAtNearest()` and `propagate()` are no longer called — their logic is inlined in the loop with direct array access.

---

## 3. TauDEM Skip Check (`delineation.py`)

### `runTauDEM` method

**Before:** All TauDEM steps (PitFill, D8FlowDir, DinfFlowDir, AreaD8, AreaDinf, GridNet, Threshold, StreamNet) always run regardless of existing outputs.

**After:** When `thresholdChanged = False` (set by `run-qswatplus.py` when DEM rasters are copied from a sibling subregion), TauDEM's own `mustRun` parameter allows each step to check if its outputs are up-to-date via `isUpToDate()` timestamp comparison. Steps with existing newer outputs skip execution.

**Note:** The QGIS layer loading (`removeLayer`/`getLayer`) still runs to keep layers registered in memory — only the TauDEM executables are skipped.

---

## 4. Subprocess stderr Suppression (`coswatFX.py`)

### `runSWATPlus` function

**Before:** `subprocess.Popen(executable_path, stdout=subprocess.PIPE)` — Fortran `forrtl` floating point errors printed to terminal.

**After:** `subprocess.Popen(executable_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)` — suppresses non-fatal Fortran warnings.

---

## 5. Subregion-Aware Parameter (`delineation.py`)

### `runTauDEM2` and `runTauDEM` methods

Added `subDir` parameter that flows through `runTauDEM2` → `runTauDEM` → `create-outlets.py --sr {subDir}`. Allows the delineation to pass subregion context to the outlet creation script.

---

## Files Modified

| File | Changes |
|------|---------|
| `floodplain.py` | Vectorized floodplain calc, numpy-based ridge heights, kept sequential fallback |
| `delineation.py` | `subDir` param, `thresholdChanged` skip support, `srcChannelFile` pre-definition |
| `coswatFX.py` | stderr suppression, `progressDict` for TUI support |

## Dependencies

All optimizations use only `numpy` and `gdal` (GDAL Python bindings) — both available in the Docker container. No additional packages required.

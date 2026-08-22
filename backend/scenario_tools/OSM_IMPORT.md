# OpenStreetMap (OSM) Real-World Network Import Guide

This guide walks you through exporting real-world road network data from OpenStreetMap (OSM) and converting it into a fully functional, loadable SUMO simulation scenario for NexRoute.

---

## Step 1: Export OpenStreetMap Data (.osm)

You can obtain a `.osm` raw XML network extract for any real-world area using any of the following methods:

### Option A: OpenStreetMap.org Export (Recommended for 1–3 km² urban areas)
1. Go to [OpenStreetMap.org](https://www.openstreetmap.org/).
2. Navigate to your desired city, neighborhood, or campus area.
3. Click the **Export** button in the top navigation bar.
4. (Optional) Click **Manually select a different area** to adjust the bounding box. For optimal simulation performance, select an area of approximately **1 to 3 km²** (e.g. a 1.5 km x 1.5 km downtown grid or university campus).
5. Click the blue **Export** button to download `map.osm`.

### Option B: Overpass API (Command-line download)
You can directly download an OSM XML bounding box extract using `curl` or Python.
Bounding box syntax: `bbox=south,west,north,east` (lat_min, lon_min, lat_max, lon_max).

Example for Downtown San Francisco (~1.5 km²):
```bash
curl -s "https://overpass-api.de/api/map?bbox=-122.410,37.785,-122.395,37.795" -o downtown_sf.osm
```

---

## Step 2: Run the Import Pipeline

Once you have saved your `.osm` file (e.g., `downtown_sf.osm`), run `import_osm_scenario.py` from the repository root:

```bash
python backend/scenario_tools/import_osm_scenario.py --osm-file path/to/downtown_sf.osm --scenario-name real_sf_downtown --demand-level moderate
```

### CLI Arguments

- `--osm-file PATH` *(required)*: Path to the downloaded `.osm` or `.osm.xml` file.
- `--scenario-name STR` *(optional)*: Target scenario name (defaults to `osm_<filename_stem>`).
- `--demand-level {light,moderate,heavy}` *(optional)*: Vehicle departure rate (`light` = 2.0s period, `moderate` = 1.0s period, `heavy` = 0.5s period). Default: `moderate`.
- `--output-dir PATH` *(optional)*: Output directory (defaults to `backend/scenarios/<scenario_name>/`).
- `--seed INT` *(optional)*: Random seed for reproducible trip demand generation.

---

## Step 3: What the Pipeline Does

1. **Pre-validation**: Checks that the `.osm` file exists and contains road data.
2. **Network Conversion (`netconvert`)**: Converts OSM ways/nodes into SUMO road edges, lanes, and junctions:
   - Removes redundant shape nodes (`--geometry.remove`).
   - Guesses motorway ramps (`--ramps.guess`).
   - Joins close intersections into complex traffic junctions (`--junctions.join`, `--tls.join`).
   - Guesses signal locations (`--tls.guess-signals`).
   - Removes isolated disconnected edges (`--remove-edges.isolated`).
3. **Post-validation**: Verifies that the generated `.net.xml` contains valid edges and junctions.
4. **Demand Generation (`randomTrips.py`)**: Populates the real road network with valid vehicle routes.
5. **Configuration Assembly**: Generates `osm.sumocfg` and `scenario.yaml`.

---

## Step 4: Run Simulation on the Imported Scenario

You can now launch interactive or batch simulations on your new real-world scenario:

### Run in Headless Batch Mode:
```bash
python backend/run.py --mode batch --scenario real_sf_downtown --seed 42 --headless --steps 500
```

### Run in Interactive GUI Mode:
```bash
python backend/run.py --mode batch --scenario real_sf_downtown --seed 42 --steps 500
```

---

## Version Control Note

> **[IMPORTANT]**
> Generated network and route XML files (`osm.net.xml`, `osm.rou.xml`, `osm.sumocfg`) in `backend/scenarios/` are ignored by git (`.gitignore`).
> Only your raw `.osm` data file, `import_osm_scenario.py`, documentation, and `scenario.yaml` are version-controlled.

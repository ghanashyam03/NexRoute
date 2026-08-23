# NexRoute Docker Environment Guide

This document provides complete instructions for building and running NexRoute inside a fully reproducible, containerized Docker environment with pre-configured SUMO tools and Python dependencies.

---

## 📌 Pinned Environment Specifications

- **Base Operating System**: Debian 12 (Bookworm)
- **Python Version**: `3.12` (`python:3.12-slim-bookworm`)
- **SUMO Engine Version**: `1.15.0` (`sumo` and `sumo-tools` package)
- **Environment Variables**:
  - `SUMO_HOME=/usr/share/sumo`
  - `PATH="/usr/share/sumo/tools:/usr/share/sumo/bin:${PATH}"`

---

## 🛠️ 1. Build the Docker Image

To build the container image locally:

```bash
docker build -t nexroute .
```

---

## 🧪 2. Run the Unit Test Suite

Run the full unit test suite (both backend and experiment pipelines) inside the container:

```bash
# Run all unit tests
docker run --rm nexroute pytest -v

# Run experiment pipeline tests specifically
docker run --rm nexroute pytest experiments/tests/ -v
```

---

## 🚗 3. Run a Single Headless Batch Simulation

Run a single batch simulation inside the container with host volume persistence:

```bash
# Windows (PowerShell)
docker run --rm -v ${PWD}/results:/app/results nexroute python backend/run.py --mode batch --scenario grid_3_light --seed 42 --steps 500 --headless

# Linux / macOS
docker run --rm -v $(pwd)/results:/app/results nexroute python backend/run.py --mode batch --scenario grid_3_light --seed 42 --steps 500 --headless
```

---

## 🔬 4. Run the Full Ablation Experiment Matrix Sweep

Execute the 5-condition ablation sweep across scenarios and seeds:

```bash
# Dry-run configuration inspection
docker run --rm nexroute python experiments/run_ablation_sweep.py --scenarios grid_3_light --seeds 1,2,3 --dry-run

# Run real sweep with output persisted to host filesystem
docker run --rm -v ${PWD}/experiments/results:/app/experiments/results nexroute python experiments/run_ablation_sweep.py --scenarios grid_3_light --seeds 1,2,3,4,5 --steps 500
```

---

## 📊 5. Run Results Aggregation, Statistical Analysis & Visualization

Run the downstream analysis and figure generation pipeline inside the container:

```bash
# 1. Aggregate JSONL manifest into Parquet & Preview CSV
docker run --rm -v ${PWD}/experiments/results:/app/experiments/results nexroute python experiments/aggregate_results.py

# 2. Perform seed-aligned paired hypothesis testing, effect sizes & FDR analysis
docker run --rm -v ${PWD}/experiments/results:/app/experiments/results nexroute python experiments/analyze_results.py

# 3. Generate publication-grade figures (.png, .pdf) and LaTeX summary table (.tex)
docker run --rm -v ${PWD}/experiments/results:/app/experiments/results nexroute python experiments/visualize_results.py
```

---

## 🐳 6. Docker Compose Shortcuts

Alternatively, use `docker-compose` service definitions:

```bash
# Run unit tests
docker compose run test

# Run single batch simulation
docker compose run batch

# Run full ablation sweep
docker compose run sweep

# Run full analysis & visualization pipeline
docker compose run analysis
```

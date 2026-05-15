from __future__ import annotations

import io
import json
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from shapely.geometry import Point

app = FastAPI(title="AquaCascade AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MappingResponse(BaseModel):
    warnings: list[str]
    metrics: dict[str, Any]
    layers: dict[str, Any]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def guess_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def read_csv_or_geojson(upload: UploadFile) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    name = upload.filename or ""
    suffix = name.lower().split(".")[-1]
    raw = upload.file.read()

    if suffix == "csv":
        try:
            df = pd.read_csv(io.BytesIO(raw))
            return normalize_columns(df), warnings
        except Exception:
            warnings.append(f"Could not parse {name} as CSV. Falling back to mock data.")
            return pd.DataFrame(), warnings

    if suffix in {"geojson", "json"}:
        try:
            obj = json.loads(raw.decode("utf-8"))
            features = obj.get("features", []) if isinstance(obj, dict) else []
            rows: list[dict[str, Any]] = []
            for feature in features:
                props = feature.get("properties", {}) or {}
                geom = feature.get("geometry", {}) or {}
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates", [None, None])
                    props["lon"] = coords[0]
                    props["lat"] = coords[1]
                rows.append(props)
            df = pd.DataFrame(rows)
            return normalize_columns(df), warnings
        except Exception:
            warnings.append(f"Could not parse {name} as GeoJSON. Falling back to mock data.")
            return pd.DataFrame(), warnings

    warnings.append(f"Unsupported format for {name}. Use CSV or GeoJSON. Falling back to mock data.")
    return pd.DataFrame(), warnings


def ensure_terrain(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if df.empty:
        return mock_terrain(), ["Terrain data unavailable, using mock terrain."]

    lat_col = guess_column(df, ["lat", "latitude", "y"])
    lon_col = guess_column(df, ["lon", "lng", "longitude", "x"])
    elev_col = guess_column(df, ["elevation", "elev", "z", "height"])

    if not (lat_col and lon_col and elev_col):
        warnings.append("Terrain columns not fully matched. Expected lat/lon/elevation. Using mock terrain.")
        return mock_terrain(), warnings

    out = pd.DataFrame({
        "lat": pd.to_numeric(df[lat_col], errors="coerce"),
        "lon": pd.to_numeric(df[lon_col], errors="coerce"),
        "elevation": pd.to_numeric(df[elev_col], errors="coerce"),
    }).dropna()

    if len(out) < 8:
        warnings.append("Terrain dataset too small/invalid after parsing. Using mock terrain.")
        return mock_terrain(), warnings

    return out, warnings


def ensure_groundwater(df: pd.DataFrame, terrain: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    if df.empty:
        return mock_groundwater(terrain), ["Groundwater data unavailable, using mock suitability."]

    lat_col = guess_column(df, ["lat", "latitude", "y"])
    lon_col = guess_column(df, ["lon", "lng", "longitude", "x"])
    suit_col = guess_column(df, ["suitability", "recharge", "score", "groundwater", "gw_score"])

    if not (lat_col and lon_col and suit_col):
        warnings.append("Groundwater columns not fully matched. Expected lat/lon/suitability. Using mock groundwater.")
        return mock_groundwater(terrain), warnings

    out = pd.DataFrame({
        "lat": pd.to_numeric(df[lat_col], errors="coerce"),
        "lon": pd.to_numeric(df[lon_col], errors="coerce"),
        "suitability": pd.to_numeric(df[suit_col], errors="coerce"),
    }).dropna()

    if len(out) < 8:
        warnings.append("Groundwater dataset too small/invalid after parsing. Using mock groundwater.")
        return mock_groundwater(terrain), warnings

    out["suitability"] = out["suitability"].clip(0, 1)
    return out, warnings


def mock_terrain(n: int = 80) -> pd.DataFrame:
    center_lat, center_lon = 12.9716, 77.5946
    rng = np.random.default_rng(42)
    lats = center_lat + rng.normal(0, 0.015, n)
    lons = center_lon + rng.normal(0, 0.015, n)
    elev = 930 + rng.normal(0, 12, n) + (lats - center_lat) * 200
    return pd.DataFrame({"lat": lats, "lon": lons, "elevation": elev})


def mock_groundwater(terrain: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    suitability = np.clip(0.6 + rng.normal(0, 0.2, len(terrain)), 0, 1)
    return pd.DataFrame({"lat": terrain["lat"], "lon": terrain["lon"], "suitability": suitability})


def nearest_suitability(row: pd.Series, gw: pd.DataFrame) -> float:
    d = (gw["lat"] - row["lat"]) ** 2 + (gw["lon"] - row["lon"]) ** 2
    idx = d.idxmin()
    return float(gw.loc[idx, "suitability"])


def build_layers(terrain: pd.DataFrame, gw: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = terrain.copy()
    merged["suitability"] = merged.apply(lambda r: nearest_suitability(r, gw), axis=1)
    elev_norm = (merged["elevation"] - merged["elevation"].min()) / (
        (merged["elevation"].max() - merged["elevation"].min()) or 1
    )
    merged["score"] = (1 - elev_norm) * 0.55 + merged["suitability"] * 0.45
    pits = merged.nlargest(min(12, len(merged)), "score").copy().reset_index(drop=True)
    pits["pit_id"] = [f"P{i+1}" for i in range(len(pits))]

    g = nx.DiGraph()
    for _, pit in pits.iterrows():
        g.add_node(pit["pit_id"], lat=pit["lat"], lon=pit["lon"], elevation=pit["elevation"], score=pit["score"])

    sorted_ids = pits.sort_values("elevation", ascending=False)["pit_id"].tolist()
    id_to_row = {r["pit_id"]: r for _, r in pits.iterrows()}
    edges = []
    for i in range(len(sorted_ids) - 1):
        src = sorted_ids[i]
        dst = sorted_ids[i + 1]
        g.add_edge(src, dst)
        edges.append({
            "from": src,
            "to": dst,
            "path": [
                [id_to_row[src]["lat"], id_to_row[src]["lon"]],
                [id_to_row[dst]["lat"], id_to_row[dst]["lon"]],
            ],
        })

    water_body = {
        "name": "Nearest Water Body",
        "lat": float(pits["lat"].min() - 0.005),
        "lon": float(pits["lon"].min() - 0.005),
    }

    if sorted_ids:
        last = sorted_ids[-1]
        edges.append({
            "from": last,
            "to": "WB1",
            "path": [
                [id_to_row[last]["lat"], id_to_row[last]["lon"]],
                [water_body["lat"], water_body["lon"]],
            ],
        })

    layers = {
        "terrain": merged[["lat", "lon", "elevation"]].to_dict(orient="records"),
        "groundwater": gw[["lat", "lon", "suitability"]].to_dict(orient="records"),
        "pits": pits[["pit_id", "lat", "lon", "elevation", "score", "suitability"]].to_dict(orient="records"),
        "edges": edges,
        "water_bodies": [water_body],
    }

    metrics = {
        "total_pits": int(len(pits)),
        "estimated_recharge_efficiency": round(float(pits["score"].mean() * 100), 1) if len(pits) else 0,
        "overflow_reduction_pct": round(min(95.0, 35.0 + len(edges) * 3.5), 1),
        "water_retained_kl": round(float(len(pits) * 14.2), 1),
        "recharge_score": round(float(pits["score"].sum()), 2),
        "connected_water_bodies": 1,
    }
    return layers, metrics


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/map", response_model=MappingResponse)
def map_data(terrain_file: UploadFile = File(...), groundwater_file: UploadFile = File(...)) -> MappingResponse:
    warnings: list[str] = []
    terrain_df, w1 = read_csv_or_geojson(terrain_file)
    groundwater_df, w2 = read_csv_or_geojson(groundwater_file)
    warnings.extend(w1)
    warnings.extend(w2)

    terrain, wt = ensure_terrain(terrain_df)
    gw, wg = ensure_groundwater(groundwater_df, terrain)
    warnings.extend(wt)
    warnings.extend(wg)

    layers, metrics = build_layers(terrain, gw)
    return MappingResponse(warnings=warnings, metrics=metrics, layers=layers)

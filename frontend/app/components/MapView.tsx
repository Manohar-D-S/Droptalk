"use client";

import "leaflet/dist/leaflet.css";
import { MapContainer, Marker, Polyline, Popup, TileLayer, CircleMarker } from "react-leaflet";

type Pit = { pit_id: string; lat: number; lon: number; score: number; elevation: number; suitability: number };
type Edge = { from: string; to: string; path: [number, number][] };
type WaterBody = { name: string; lat: number; lon: number };

export default function MapView({
  pits,
  edges,
  waterBodies,
}: {
  pits: Pit[];
  edges: Edge[];
  waterBodies: WaterBody[];
}) {
  const center: [number, number] = pits.length ? [pits[0].lat, pits[0].lon] : [12.9716, 77.5946];

  return (
    <MapContainer center={center} zoom={12} className="h-[70vh] w-full rounded-xl">
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {pits.map((pit) => (
        <CircleMarker key={pit.pit_id} center={[pit.lat, pit.lon]} radius={7} pathOptions={{ color: "#007C91", fillColor: "#00B8D9", fillOpacity: 0.9 }}>
          <Popup>
            <strong>{pit.pit_id}</strong>
            <br />Score: {(pit.score * 100).toFixed(1)}
            <br />Elevation: {pit.elevation.toFixed(2)}
            <br />Suitability: {(pit.suitability * 100).toFixed(1)}
          </Popup>
        </CircleMarker>
      ))}
      {edges.map((edge, idx) => (
        <Polyline key={`${edge.from}-${edge.to}-${idx}`} positions={edge.path} pathOptions={{ color: "#0B3C5D", weight: 3, dashArray: "7 6" }} />
      ))}
      {waterBodies.map((wb) => (
        <Marker key={wb.name} position={[wb.lat, wb.lon]}>
          <Popup>{wb.name}</Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

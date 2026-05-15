"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

const MapView = dynamic(() => import("./components/MapView"), { ssr: false });

type ApiResult = {
  warnings: string[];
  metrics: Record<string, string | number>;
  layers: {
    pits: any[];
    edges: any[];
    water_bodies: any[];
  };
};

export default function Page() {
  const [terrain, setTerrain] = useState<File | null>(null);
  const [groundwater, setGroundwater] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [phase, setPhase] = useState("Ready");
  const [result, setResult] = useState<ApiResult | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  const phases = useMemo(
    () => [
      "Reading terrain data",
      "Analyzing slope",
      "Detecting recharge zones",
      "Mapping overflow paths",
      "Generating cascading network",
    ],
    [],
  );

  const runMapping = async () => {
    if (!terrain || !groundwater) {
      setErrors(["Please upload both terrain and groundwater files."]);
      return;
    }
    setErrors([]);
    setProcessing(true);
    setResult(null);

    let i = 0;
    const timer = setInterval(() => {
      setPhase(phases[i % phases.length]);
      i += 1;
    }, 700);

    try {
      const formData = new FormData();
      formData.append("terrain_file", terrain);
      formData.append("groundwater_file", groundwater);
      const res = await fetch("http://127.0.0.1:8000/map", { method: "POST", body: formData });
      if (!res.ok) throw new Error("Backend processing failed.");
      const data = (await res.json()) as ApiResult;
      setResult(data);
      if (data.warnings.length) setErrors(data.warnings);
    } catch (e) {
      setErrors(["Unable to process data. Ensure backend is running on port 8000."]);
    } finally {
      clearInterval(timer);
      setProcessing(false);
      setPhase("Completed");
    }
  };

  return (
    <main className="min-h-screen p-6">
      <header className="mb-6 rounded-xl bg-deepBlue p-5 text-white">
        <h1 className="text-2xl font-bold">AquaCascade AI</h1>
        <p className="text-sm opacity-90">Cascading Groundwater Recharge Mapping System</p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <div className="card p-4">
            <h2 className="mb-3 text-lg font-semibold text-deepBlue">Upload Datasets</h2>
            <label className="mb-2 block text-sm">Terrain CSV/GeoJSON</label>
            <input type="file" accept=".csv,.geojson,.json" onChange={(e) => setTerrain(e.target.files?.[0] ?? null)} className="mb-3 w-full" />
            <label className="mb-2 block text-sm">Groundwater CSV/GeoJSON</label>
            <input type="file" accept=".csv,.geojson,.json" onChange={(e) => setGroundwater(e.target.files?.[0] ?? null)} className="mb-3 w-full" />
            <button onClick={runMapping} disabled={processing} className="w-full rounded-lg bg-teal px-3 py-2 font-semibold text-white hover:bg-cyanAccent disabled:opacity-70">
              {processing ? "Processing..." : "Start Mapping"}
            </button>
          </div>

          <div className="card p-4">
            <h3 className="font-semibold text-deepBlue">Layer Toggles</h3>
            <p className="text-sm text-slate-600">All MVP layers are enabled by default.</p>
          </div>

          {result && (
            <div className="card p-4">
              <h3 className="mb-2 font-semibold text-deepBlue">Stats</h3>
              <div className="space-y-1 text-sm">
                {Object.entries(result.metrics).map(([k, v]) => (
                  <p key={k}><span className="font-medium">{k.replaceAll("_", " ")}:</span> {String(v)}</p>
                ))}
              </div>
            </div>
          )}

          {errors.length > 0 && (
            <div className="card border-yellow-300 bg-yellow-50 p-4">
              <h3 className="mb-2 font-semibold text-yellow-800">Warnings</h3>
              <ul className="list-disc space-y-1 pl-4 text-sm text-yellow-900">
                {errors.map((e, idx) => <li key={idx}>{e}</li>)}
              </ul>
            </div>
          )}
        </aside>

        <section className="card p-4">
          {processing && (
            <div className="mb-3 rounded-lg border border-cyan-200 bg-cyan-50 p-3">
              <p className="font-medium text-teal">{phase}</p>
            </div>
          )}
          {result ? (
            <MapView pits={result.layers.pits} edges={result.layers.edges} waterBodies={result.layers.water_bodies} />
          ) : (
            <div className="flex h-[70vh] items-center justify-center rounded-xl border-2 border-dashed border-slate-300 text-slate-500">
              Upload both files and click Start Mapping to render the cascading network.
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

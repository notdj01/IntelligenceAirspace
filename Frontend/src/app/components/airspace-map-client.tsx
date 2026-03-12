import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { AirTarget, Classification } from "../../lib/airspace-data";
import { RISK_COLORS, NO_FLY_ZONE } from "../../lib/airspace-data";

interface AirspaceMapClientProps {
  targets: AirTarget[];
  selectedId: string | null;
  onSelectTarget: (target: AirTarget) => void;
  onDeselect: () => void;
}

export function AirspaceMapClient({
  targets,
  selectedId,
  onSelectTarget,
  onDeselect,
}: AirspaceMapClientProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.Marker>>(new Map());
  const polylinesRef = useRef<Map<string, L.Polyline>>(new Map());
  const predictionPolylinesRef = useRef<Map<string, L.Polyline>>(new Map());
   const predictionHeadsRef = useRef<Map<string, L.Marker>>(new Map());
  const onSelectTargetRef = useRef(onSelectTarget);
  const onDeselectRef = useRef(onDeselect);

  // Update callback refs
  useEffect(() => {
    onSelectTargetRef.current = onSelectTarget;
    onDeselectRef.current = onDeselect;
  }, [onSelectTarget, onDeselect]);

  // Initialize map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [19.0, 72.85],
      zoom: 12,
      zoomControl: false,
      attributionControl: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      className: "map-dark-tile",
    }).addTo(map);

    // Add zoom control
    L.control.zoom({ position: "topright" }).addTo(map);

    // Add No-Fly Zone polygon
    const nfzPolygon = L.polygon(NO_FLY_ZONE, {
      color: "#f43f5e",
      fillColor: "#f43f5e",
      fillOpacity: 0.12,
      weight: 2,
      dashArray: "6 4",
    }).addTo(map);

    nfzPolygon.bindTooltip(
      `<span style="font-family: monospace; color: #f43f5e; font-size: 11px; font-weight: bold;">NO-FLY ZONE 3</span>`,
      {
        permanent: true,
        direction: "center",
        className: "nfz-tooltip",
      }
    );

    // Click on empty map area deselects
    map.on("click", () => {
      onDeselectRef.current();
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markersRef.current.clear();
      polylinesRef.current.clear();
      predictionPolylinesRef.current.clear();
      predictionHeadsRef.current.clear();
    };
  }, []);

  // Update markers and polylines
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    targets.forEach((target) => {
      const history =
        target.trajectory.length > 0 ? target.trajectory : [target.coords];
      if (history.length === 0) return;

      // Current position always comes from backend coords to avoid
      // swapping front/back visuals.
      const currentCoords = target.coords;
      const isSelected = selectedId === target.id;
      const riskColor = RISK_COLORS[target.risk_level];

      // Update or create polyline
      let polyline = polylinesRef.current.get(target.id);
      if (!polyline) {
        polyline = L.polyline(history, {
          color: riskColor,
          weight: isSelected ? 2 : 1,
          opacity: isSelected ? 0.8 : 0.4,
          dashArray: "4 3",
        }).addTo(map);
        polylinesRef.current.set(target.id, polyline);
      } else {
        polyline.setLatLngs(history);
        polyline.setStyle({
          color: riskColor,
          weight: isSelected ? 2 : 1,
          opacity: isSelected ? 0.8 : 0.4,
        });
      }

      // Update or create marker
      let marker = markersRef.current.get(target.id);
      if (!marker) {
        const icon = createFlightIcon(
          target.classification,
          riskColor,
          isSelected
        );
        marker = L.marker(currentCoords, { icon }).addTo(map);

        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          onSelectTargetRef.current(target);
        });

        marker.bindTooltip(
          createTooltipContent(target, riskColor),
          { direction: "top", offset: [0, -10] }
        );

        markersRef.current.set(target.id, marker);
      } else {
        marker.setLatLng(currentCoords);
        const icon = createFlightIcon(
          target.classification,
          riskColor,
          isSelected
        );
        marker.setIcon(icon);
        marker.setTooltipContent(createTooltipContent(target, riskColor));
      }
      // Update or create predicted trajectory polyline (future path only)
      const predicted = target.predicted_trajectory ?? [];
      let predPolyline = predictionPolylinesRef.current.get(target.id);
      if (predicted.length > 0) {
        const predPoints: [number, number][] = [
          currentCoords,
          ...predicted,
        ];
        if (!predPolyline) {
          predPolyline = L.polyline(predPoints, {
            color: riskColor,
            weight: isSelected ? 3 : 2,
            opacity: 0.9,
            dashArray: "6 4",
          }).addTo(map);
          predictionPolylinesRef.current.set(target.id, predPolyline);
        } else {
          predPolyline.setLatLngs(predPoints);
          predPolyline.setStyle({
            color: riskColor,
            weight: isSelected ? 3 : 2,
            opacity: 0.9,
            dashArray: "6 4",
          });
        }

        // Add/update arrow marker at the end of the predicted path
        const arrowPos = predicted[predicted.length - 1];
        let headMarker = predictionHeadsRef.current.get(target.id);
        if (!headMarker) {
          headMarker = L.marker(arrowPos, {
            icon: createArrowIcon(riskColor),
            interactive: false,
          }).addTo(map);
          predictionHeadsRef.current.set(target.id, headMarker);
        } else {
          headMarker.setLatLng(arrowPos);
          headMarker.setIcon(createArrowIcon(riskColor));
        }
      } else if (predPolyline) {
        predPolyline.remove();
        predictionPolylinesRef.current.delete(target.id);
        const headMarker = predictionHeadsRef.current.get(target.id);
        if (headMarker) {
          headMarker.remove();
          predictionHeadsRef.current.delete(target.id);
        }
      }
    });

    // Remove old markers/polylines
    const currentIds = new Set(targets.map((t) => t.id));
    markersRef.current.forEach((marker, id) => {
      if (!currentIds.has(id)) {
        marker.remove();
        markersRef.current.delete(id);
      }
    });
    polylinesRef.current.forEach((polyline, id) => {
      if (!currentIds.has(id)) {
        polyline.remove();
        polylinesRef.current.delete(id);
      }
    });
    predictionPolylinesRef.current.forEach((polyline, id) => {
      if (!currentIds.has(id)) {
        polyline.remove();
        predictionPolylinesRef.current.delete(id);
      }
    });
    predictionHeadsRef.current.forEach((marker, id) => {
      if (!currentIds.has(id)) {
        marker.remove();
        predictionHeadsRef.current.delete(id);
      }
    });
  }, [targets, selectedId]);

  return (
    <div className="relative size-full rounded-lg overflow-hidden">
      {/* Map Container */}
      <div ref={mapContainerRef} className="size-full" />

      {/* Scan-line overlay - reduced opacity */}
      <div
        style={{
          background:
            "linear-gradient(to bottom, transparent 50%, rgba(34,211,238,0.008) 50%)",
          backgroundSize: "100% 4px",
          pointerEvents: "none",
        }}
        className="absolute inset-0 z-10"
      />

      {/* Corner brackets */}
      <div
        style={{ borderColor: "rgba(34,211,238,0.6)" }}
        className="absolute top-2 left-2 size-5 border-t-2 border-l-2 pointer-events-none z-20"
      />
      <div
        style={{ borderColor: "rgba(34,211,238,0.6)" }}
        className="absolute top-2 right-2 size-5 border-t-2 border-r-2 pointer-events-none z-20"
      />
      <div
        style={{ borderColor: "rgba(34,211,238,0.6)" }}
        className="absolute bottom-2 left-2 size-5 border-b-2 border-l-2 pointer-events-none z-20"
      />
      <div
        style={{ borderColor: "rgba(34,211,238,0.6)" }}
        className="absolute bottom-2 right-2 size-5 border-b-2 border-r-2 pointer-events-none z-20"
      />
    </div>
  );
}

function createFlightIcon(
  classification: Classification,
  riskColor: string,
  isSelected: boolean
): L.DivIcon {
  const size = isSelected ? 36 : 28;
  const shadow = isSelected
    ? `drop-shadow(0 0 6px ${riskColor})`
    : `drop-shadow(0 0 3px ${riskColor}88)`;

  let svgPath = "";

  if (classification === "Drone") {
    // Quadcopter top-down
    svgPath = `
      <circle cx="12" cy="12" r="3" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
      <circle cx="6" cy="6" r="2.5" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
      <circle cx="18" cy="6" r="2.5" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
      <circle cx="6" cy="18" r="2.5" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
      <circle cx="18" cy="18" r="2.5" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
      <line x1="12" y1="12" x2="6" y2="6" stroke="${riskColor}" stroke-width="1.5" />
      <line x1="12" y1="12" x2="18" y2="6" stroke="${riskColor}" stroke-width="1.5" />
      <line x1="12" y1="12" x2="6" y2="18" stroke="${riskColor}" stroke-width="1.5" />
      <line x1="12" y1="12" x2="18" y2="18" stroke="${riskColor}" stroke-width="1.5" />
    `;
  } else if (classification === "Bird") {
    // Bird wings
    svgPath = `
      <path d="M3 12 C6 8, 10 6, 12 8 C14 6, 18 8, 21 12" fill="none" stroke="${riskColor}" stroke-width="2" />
      <circle cx="12" cy="12" r="2" fill="${riskColor}" fill-opacity="0.5" />
    `;
  } else {
    // Aircraft / default - star/arrow shape
    svgPath = `
      <polygon points="12,2 15,9 22,9 16,14 18,21 12,17 6,21 8,14 2,9 9,9" fill="${riskColor}" fill-opacity="0.33" stroke="${riskColor}" stroke-width="1.5" />
    `;
  }

  const html = `
    <div style="width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center;">
      <svg width="24" height="24" viewBox="0 0 24 24" style="filter: ${shadow};">
        ${svgPath}
      </svg>
    </div>
  `;

  return L.divIcon({
    html,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createArrowIcon(riskColor: string): L.DivIcon {
  const size = 18;
  const html = `
    <div style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <polygon points="8,1 15,15 1,15" fill="${riskColor}" fill-opacity="0.9" />
      </svg>
    </div>
  `;

  return L.divIcon({
    html,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createTooltipContent(target: AirTarget, riskColor: string): string {
  const adsbColor = target.adsb ? "#4ade80" : "#f43f5e";
  return `
    <div style="background: rgba(13,20,32,0.95); padding: 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(12px);">
      <div style="font-family: monospace; font-size: 12px; font-weight: bold; color: ${riskColor}; margin-bottom: 4px;">
        ${target.id}
      </div>
      <div style="font-family: monospace; font-size: 10px; color: #94a3b8; margin-bottom: 2px;">
        ${target.classification} · ${target.speed} kts
      </div>
      <div style="font-family: monospace; font-size: 10px; color: ${adsbColor};">
        ADS-B: ${target.adsb ? "ON" : "OFF"}
      </div>
    </div>
  `;
}
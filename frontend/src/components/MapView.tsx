import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from 'react-leaflet';
import { Radio } from 'lucide-react';
import { Station, Section, RouteAnalysisResult } from '../types';
import { theme, cardStyle, getCoords } from '../theme';

function RecenterMap({ center }: { center: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (center && Number.isFinite(center[0]) && Number.isFinite(center[1])) {
      map.flyTo(center, Math.max(map.getZoom(), 6), { duration: 0.7 });
    }
  }, [center, map]);
  return null;
}

interface MapViewProps {
  stations: Station[];
  sections: Section[];
  selectedStation: Station | null;
  onSelectStation: (s: Station) => void;
  routeAnalysis: RouteAnalysisResult | null;
}

export function MapView({
  stations,
  sections,
  selectedStation,
  onSelectStation,
  routeAnalysis
}: MapViewProps) {
  const validStations = useMemo(() => stations.filter(s => getCoords(s)), [stations]);
  const stationMap = useMemo(() => new Map(validStations.map(s => [s.code, s])), [validStations]);

  // Section lines for map
  const sectionLines = useMemo(() => {
    return sections
      .map(sec => {
        const fromSt = stationMap.get(sec.station_from);
        const toSt = stationMap.get(sec.station_to);
        if (fromSt && toSt) {
          const c1 = getCoords(fromSt);
          const c2 = getCoords(toSt);
          if (c1 && c2) {
            return {
              id: sec.id,
              positions: [c1, c2] as [number, number][],
              from: fromSt,
              to: toSt,
              dist: sec.distance_km
            };
          }
        }
        return null;
      })
      .filter((s): s is { id: string; positions: [number, number][]; from: Station; to: Station; dist: number } => s !== null);
  }, [sections, stationMap]);

  const selectedCoords = useMemo(() => getCoords(selectedStation), [selectedStation]);

  const analyzedRouteLine = useMemo(() => {
    if (!routeAnalysis) return null;
    const cFrom = getCoords(routeAnalysis.from_station);
    const cTo = getCoords(routeAnalysis.to_station);
    if (cFrom && cTo) {
      return [cFrom, cTo] as [number, number][];
    }
    return null;
  }, [routeAnalysis]);

  return (
    <div style={{ ...cardStyle, padding: 0, overflow: 'hidden', height: 600, display: 'flex', flexDirection: 'column' }}>
      <div style={{
        padding: '12px 18px',
        background: theme.cardHeader,
        borderBottom: `1px solid ${theme.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 700 }}>
          <Radio size={16} color={theme.cyan} />
          Centralized Traffic Control (CTC) Corridor Display
        </div>
        <div style={{ fontSize: 11, color: theme.textDim }}>
          Click any station node to inspect assets & pending blocks
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>
        <MapContainer
          center={selectedCoords || [28.6423, 77.2200]}
          zoom={6}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%', background: '#f8fafc' }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors &copy; CARTO"
            url="https://{s}.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}{r}.png"
          />

          <RecenterMap center={selectedCoords} />

          {/* Corridor Section Polylines */}
          {sectionLines.map(sec => (
            <Polyline
              key={sec.id}
              positions={sec.positions}
              color="#2563eb"
              weight={3}
              opacity={0.65}
              dashArray="5, 8"
            >
              <Popup>
                <div style={{ color: '#0f172a', fontSize: 12 }}>
                  <strong>Corridor: {sec.id}</strong><br />
                  {sec.from.name} ({sec.from.code}) ↔ {sec.to.name} ({sec.to.code})<br />
                  Distance: {sec.dist} km
                </div>
              </Popup>
            </Polyline>
          ))}

          {/* Analyzed Route Polyline Highlight */}
          {analyzedRouteLine && (
            <Polyline
              positions={analyzedRouteLine}
              color={routeAnalysis?.block_required ? theme.red : theme.green}
              weight={6}
              opacity={0.9}
            >
              <Popup>
                <div style={{ color: '#0f172a', fontSize: 12 }}>
                  <strong>{routeAnalysis?.verdict}</strong><br />
                  {routeAnalysis?.summary}
                </div>
              </Popup>
            </Polyline>
          )}

          {/* Station Circle Markers */}
          {validStations.slice(0, 150).map(s => {
            const coords = getCoords(s);
            if (!coords) return null;
            const isSelected = selectedStation?.code === s.code;
            const isMajor = ['NDLS', 'MTJ', 'AGC', 'GWL', 'BVI', 'BCT', 'CNB', 'HWH'].includes(s.code);
            return (
              <CircleMarker
                key={s.code}
                center={coords}
                radius={isSelected ? 9 : isMajor ? 7 : 4}
                pathOptions={{
                  color: isSelected ? '#fbbf24' : isMajor ? theme.cyan : '#475569',
                  fillColor: isSelected ? '#f59e0b' : isMajor ? '#0284c7' : '#ffffff',
                  fillOpacity: 0.9,
                  weight: isSelected ? 3 : 1
                }}
                eventHandlers={{
                  click: () => onSelectStation(s)
                }}
              >
                <Popup>
                  <div style={{ color: '#0f172a', fontSize: 12 }}>
                    <strong>{s.name} ({s.code})</strong><br />
                    Lat: {s.lat.toFixed(4)}, Lon: {s.lon.toFixed(4)}<br />
                    <button
                      onClick={() => onSelectStation(s)}
                      style={{
                        marginTop: 6,
                        padding: '3px 8px',
                        background: '#2563eb',
                        color: '#fff',
                        border: 0,
                        borderRadius: 4,
                        cursor: 'pointer',
                        fontSize: 11
                      }}
                    >
                      Select Station
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

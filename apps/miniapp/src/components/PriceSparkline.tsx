import { useMemo, useState } from "react";

import type { PricePoint } from "../lib/api";

interface Props {
  points: PricePoint[];
}

const WIDTH = 280;
const HEIGHT = 80;
const PADDING = 4;

function formatPrice(price: number): string {
  return price < 0.01 ? price.toFixed(8) : price.toFixed(4);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export function PriceSparkline({ points }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const { path, areaPath, coords, min, max, isUp, changePct } = useMemo(() => {
    if (points.length < 2) {
      return {
        path: "",
        areaPath: "",
        coords: [] as [number, number][],
        min: 0,
        max: 0,
        isUp: true,
        changePct: 0,
      };
    }

    const prices = points.map((p) => p.price_usd);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;

    const coords: [number, number][] = points.map((p, i) => {
      const x = PADDING + (i / (points.length - 1)) * (WIDTH - PADDING * 2);
      const y = HEIGHT - PADDING - ((p.price_usd - min) / range) * (HEIGHT - PADDING * 2);
      return [x, y];
    });

    const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
    const areaPath = `${path} L${coords[coords.length - 1][0].toFixed(2)},${HEIGHT} L${coords[0][0].toFixed(2)},${HEIGHT} Z`;
    const first = prices[0];
    const last = prices[prices.length - 1];
    const isUp = last >= first;
    const changePct = first !== 0 ? ((last - first) / first) * 100 : 0;

    return { path, areaPath, coords, min, max, isUp, changePct };
  }, [points]);

  if (points.length < 2) {
    return <p className="pt-muted" style={{ fontSize: 13 }}>Sem histórico suficiente ainda para o gráfico.</p>;
  }

  const color = isUp ? "var(--pt-positive)" : "var(--pt-negative)";

  function handleMove(clientX: number, rect: DOMRect) {
    const relativeX = ((clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let bestDist = Infinity;
    coords.forEach(([x], i) => {
      const dist = Math.abs(x - relativeX);
      if (dist < bestDist) {
        bestDist = dist;
        nearest = i;
      }
    });
    setHoverIndex(nearest);
  }

  const hovered = hoverIndex != null ? points[hoverIndex] : null;
  const hoveredCoord = hoverIndex != null ? coords[hoverIndex] : null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 4 }}>
        <span style={{ color, fontWeight: 700 }} aria-hidden="true">
          {isUp ? "▲" : "▼"}
        </span>
        <span style={{ fontWeight: 700, fontSize: 13 }}>
          {isUp ? "alta" : "queda"} de {Math.abs(changePct).toFixed(2)}%
        </span>
        <span className="pt-muted" style={{ fontSize: 11 }}>
          nos últimos {points.length} pontos
        </span>
      </div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        width="100%"
        height={HEIGHT}
        onMouseMove={(e) => handleMove(e.clientX, e.currentTarget.getBoundingClientRect())}
        onMouseLeave={() => setHoverIndex(null)}
        onTouchMove={(e) => handleMove(e.touches[0].clientX, e.currentTarget.getBoundingClientRect())}
        onTouchEnd={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id="pt-spark-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.25" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#pt-spark-fill)" stroke="none" />
        <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {hoveredCoord && (
          <>
            <line
              x1={hoveredCoord[0]}
              y1={0}
              x2={hoveredCoord[0]}
              y2={HEIGHT}
              stroke="var(--pt-border)"
              strokeWidth="1"
            />
            <circle cx={hoveredCoord[0]} cy={hoveredCoord[1]} r="3" fill={color} />
          </>
        )}
      </svg>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }} className="pt-muted">
        <span>
          {hovered ? `${formatDate(hovered.timestamp)} · $${formatPrice(hovered.price_usd)}` : "Últimos dias"}
        </span>
        <span>
          Mín ${formatPrice(min)} · Máx ${formatPrice(max)}
        </span>
      </div>
    </div>
  );
}

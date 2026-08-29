"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import * as React from "react";
import * as THREE from "three";

type WebGLFieldProps = {
  accent?: string;
  className?: string;
  density?: number;
};

function SignalObject({ accent = "#b8f53d", density = 22 }: { accent?: string; density?: number }) {
  const group = React.useRef<THREE.Group>(null);
  const points = React.useMemo(() => {
    const positions = new Float32Array(density * 3);
    for (let index = 0; index < density; index += 1) {
      const phi = Math.acos(-1 + (2 * index) / density);
      const theta = Math.sqrt(density * Math.PI) * phi;
      positions[index * 3] = 2.25 * Math.cos(theta) * Math.sin(phi);
      positions[index * 3 + 1] = 2.25 * Math.sin(theta) * Math.sin(phi);
      positions[index * 3 + 2] = 2.25 * Math.cos(phi);
    }
    return positions;
  }, [density]);

  useFrame((state, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * 0.085;
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, state.pointer.y * 0.12, 0.025);
    group.current.rotation.z = THREE.MathUtils.lerp(group.current.rotation.z, -state.pointer.x * 0.08, 0.025);
  });

  return (
    <group ref={group}>
      <mesh>
        <icosahedronGeometry args={[1.72, 1]} />
        <meshBasicMaterial color={accent} wireframe transparent opacity={0.28} />
      </mesh>
      <mesh rotation={[0.5, 0.4, 0]}>
        <torusGeometry args={[2.15, 0.012, 8, 128]} />
        <meshBasicMaterial color={accent} transparent opacity={0.6} />
      </mesh>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[points, 3]} />
        </bufferGeometry>
        <pointsMaterial color={accent} size={0.055} transparent opacity={0.82} sizeAttenuation />
      </points>
    </group>
  );
}

class CanvasBoundary extends React.Component<{ children: React.ReactNode; fallback: React.ReactNode }, { failed: boolean }> {
  override state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  override render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function WebGLField({ accent, className, density }: WebGLFieldProps) {
  const [canRender, setCanRender] = React.useState(false);
  const [nearViewport, setNearViewport] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let webGlAvailable = false;
    try {
      const canvas = document.createElement("canvas");
      const webgl = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
      webGlAvailable = Boolean(webgl);
    } catch {
      webGlAvailable = false;
    }

    const syncMotionPreference = () => setCanRender(webGlAvailable && !motionPreference.matches);
    syncMotionPreference();
    motionPreference.addEventListener("change", syncMotionPreference);
    return () => motionPreference.removeEventListener("change", syncMotionPreference);
  }, []);

  React.useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    if (!("IntersectionObserver" in window)) {
      setNearViewport(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => setNearViewport(Boolean(entry?.isIntersecting)),
      { rootMargin: "320px 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const fallback = <div className="size-full webgl-static-fallback" />;

  return (
    <div ref={containerRef} className={className} aria-hidden="true">
      {canRender && nearViewport ? (
        <CanvasBoundary fallback={fallback}>
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 5.6], fov: 45 }} gl={{ alpha: true, antialias: true, powerPreference: "high-performance" }}>
          <SignalObject {...(accent ? { accent } : {})} {...(density !== undefined ? { density } : {})} />
        </Canvas>
        </CanvasBoundary>
      ) : fallback}
    </div>
  );
}

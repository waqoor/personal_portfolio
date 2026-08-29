"use client";

import { animate, useInView, useReducedMotion } from "motion/react";
import * as React from "react";

type CounterProps = {
  value: number;
  decimals?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
};

export function Counter({ className, decimals = 0, prefix = "", suffix = "", value }: CounterProps) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = React.useState(0);

  React.useEffect(() => {
    if (!inView) return;
    if (reduceMotion) {
      setDisplay(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: setDisplay,
    });
    return () => controls.stop();
  }, [inView, reduceMotion, value]);

  return <span ref={ref} className={className}>{prefix}{display.toFixed(decimals)}{suffix}</span>;
}

"use client";

import { motion, useReducedMotion, type HTMLMotionProps, type Variants } from "motion/react";
import * as React from "react";
import { motionTokens } from "./tokens";

export type MotionMode = "none" | "reveal" | "stagger";

const MotionModeContext = React.createContext<MotionMode>("reveal");

export function MotionModeProvider({
  children,
  mode,
}: {
  children: React.ReactNode;
  mode: MotionMode;
}) {
  return <MotionModeContext.Provider value={mode}>{children}</MotionModeContext.Provider>;
}

type RevealProps = HTMLMotionProps<"div"> & {
  delay?: number;
  distance?: number;
  once?: boolean;
};

export function Reveal({ children, delay = 0, distance = 20, once = true, ...props }: RevealProps) {
  const reduced = useReducedMotion();
  const mode = React.useContext(MotionModeContext);
  const animated = !reduced && mode !== "none";
  return (
    <motion.div
      initial={animated ? { opacity: 0, y: distance, filter: "blur(6px)" } : false}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once, amount: 0.18 }}
      transition={animated ? { delay, duration: motionTokens.duration.slow, ease: motionTokens.ease.expressive } : { duration: 0 }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

const containerVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.085, delayChildren: 0.04 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: motionTokens.duration.slow, ease: motionTokens.ease.expressive } },
};

export function Stagger({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduced = useReducedMotion();
  const mode = React.useContext(MotionModeContext);
  const animated = !reduced && mode === "stagger";
  return (
    <motion.div
      {...(className ? { className } : {})}
      initial={animated ? "hidden" : false}
      whileInView="visible"
      viewport={{ once: true, amount: 0.12 }}
      {...(mode === "stagger" ? { variants: containerVariants } : {})}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: React.ReactNode; className?: string }) {
  return <motion.div {...(className ? { className } : {})} variants={itemVariants}>{children}</motion.div>;
}

export function PageTransition({ children }: { children: React.ReactNode }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={reduced ? { duration: 0 } : { duration: motionTokens.duration.base, ease: motionTokens.ease.standard }}
    >
      {children}
    </motion.div>
  );
}

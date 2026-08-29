export const motionTokens = {
  duration: {
    quick: 0.18,
    base: 0.36,
    slow: 0.68,
  },
  ease: {
    standard: [0.22, 1, 0.36, 1],
    expressive: [0.16, 1, 0.3, 1],
  },
  distance: {
    subtle: 12,
    standard: 24,
  },
} as const;

"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import * as React from "react";

type GsapStoryProps = {
  children: React.ReactNode;
  className?: string;
  enabled?: boolean;
  pin?: boolean;
};

export function GsapStory({ children, className, enabled = true, pin = false }: GsapStoryProps) {
  const rootRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!enabled || !rootRef.current || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.registerPlugin(ScrollTrigger);
    const root = rootRef.current;
    const context = gsap.context(() => {
      gsap.fromTo(
        root.querySelectorAll<HTMLElement>("[data-story-item]"),
        { y: 36 },
        {
          y: 0,
          stagger: 0.12,
          ease: "power3.out",
          scrollTrigger: {
            trigger: root,
            start: "top 72%",
            end: "bottom 68%",
            scrub: 0.6,
          },
        },
      );

      if (pin && window.matchMedia("(min-width: 1024px)").matches) {
        const visual = root.querySelector<HTMLElement>("[data-story-visual]");
        if (visual) {
          ScrollTrigger.create({
            trigger: root,
            start: "top 12%",
            end: "bottom 72%",
            pin: visual,
            pinSpacing: false,
          });
        }
      }
    }, root);

    return () => context.revert();
  }, [enabled, pin]);

  return <div ref={rootRef} className={className}>{children}</div>;
}

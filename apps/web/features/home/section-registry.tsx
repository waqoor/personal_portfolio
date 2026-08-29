import type { HomePage, HomepageSection, HomepageSectionKind } from "@portfolio/api-client";
import { SECTION_DEFINITIONS } from "@portfolio/config";
import { MotionModeProvider } from "@portfolio/motion";
import type { ComponentType } from "react";
import { CategoriesSection, SectorsSection, TechnologyUniverseSection } from "./capability-sections";
import { CertificationsSection, EducationSection, ExperienceSection } from "./biography-sections";
import { MetricsSection, TestimonialsSection } from "./evidence-sections";
import { HeroSection } from "./hero-section";
import { OpenSourceSection, SponsorshipSection, WritingSection } from "./publishing-sections";
import {
  AssistantCtaSection,
  AvailabilitySection,
  ContactCtaSection,
  EditorialSection,
  ResumeSection,
  SocialLinksSection,
} from "./utility-sections";
import { SelectedWorkSection } from "./work-section";

type RegisteredSectionProps = {
  data: HomePage;
  section: HomepageSection;
};

const sectionRegistry: Record<HomepageSectionKind, ComponentType<RegisteredSectionProps> | null> = {
  hero: HeroSection,
  resume: ResumeSection,
  availability: AvailabilitySection,
  what_i_build: CategoriesSection,
  categories: CategoriesSection,
  selected_work: SelectedWorkSection,
  metrics: MetricsSection,
  testimonials: TestimonialsSection,
  sectors: SectorsSection,
  skills: TechnologyUniverseSection,
  experience: ExperienceSection,
  education: EducationSection,
  certifications: CertificationsSection,
  open_source: OpenSourceSection,
  sponsorship: SponsorshipSection,
  writing: WritingSection,
  assistant: AssistantCtaSection,
  contact: ContactCtaSection,
  social_links: SocialLinksSection,
  editorial: EditorialSection,
};

const sectionHasContent: Record<HomepageSectionKind, (data: HomePage) => boolean> = {
  hero: () => true,
  resume: (data) => Boolean(data.profile.resume),
  availability: () => true,
  what_i_build: (data) => data.categories.length > 0,
  categories: (data) => data.categories.length > 0,
  selected_work: (data) => data.featured_projects.length > 0,
  metrics: (data) => data.metrics.some((metric) => metric.verified),
  testimonials: (data) => data.testimonials.some((testimonial) => testimonial.verified),
  sectors: (data) => data.sectors.length > 0,
  skills: (data) => data.skills.length > 0,
  experience: (data) => data.experience.length > 0,
  education: (data) => data.education.length > 0,
  certifications: (data) => data.certifications.length > 0,
  open_source: (data) => data.open_source.length > 0,
  sponsorship: (data) => Boolean(data.sponsorship?.enabled),
  writing: (data) => data.articles.length > 0,
  assistant: () => true,
  contact: () => true,
  social_links: (data) => data.profile.socials.length > 0,
  editorial: (data) => data.editorial_blocks.length > 0,
};

export function resolveHomepageSections(data: HomePage): HomepageSection[] {
  return data.sections
    .filter((section) => {
      if (!section.enabled) return false;
      const featureKey = section.feature_key ?? SECTION_DEFINITIONS[section.kind].featureKey;
      const featureEnabled = !featureKey || data.feature_flags[featureKey] === true;
      return featureEnabled && sectionHasContent[section.kind](data);
    })
    .sort((left, right) => left.order - right.order);
}

export function HomepageSections({ data }: { data: HomePage }) {
  return resolveHomepageSections(data).map((section) => {
    const Component = sectionRegistry[section.kind];
    if (!Component) return null;
    return (
      <MotionModeProvider key={section.id} mode={section.animation_variant}>
        <Component data={data} section={section} />
      </MotionModeProvider>
    );
  });
}

import { Hero } from "@/components/landing/Hero";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { CsvGuide } from "@/components/landing/CsvGuide";
import { BrainLayers } from "@/components/landing/BrainLayers";
import { Features } from "@/components/landing/Features";
import { CallToAction } from "@/components/landing/CallToAction";

export default function LandingPage() {
  return (
    <>
      <Hero />
      <HowItWorks />
      <CsvGuide />
      <BrainLayers />
      <Features />
      <CallToAction />
    </>
  );
}

"use client";

import { MarketingNavbar } from "./marketing-navbar";
import { HeroSection } from "./hero-section";
import { SocialProofBar } from "./social-proof-bar";
import { FeaturesGrid } from "./features-grid";
import { HowItWorks } from "./how-it-works";
import { PricingSection } from "./pricing-section";
import { CtaFinal } from "./cta-final";
import { MarketingFooter } from "./marketing-footer";

export default function LandingPage() {
  return (
    <div className="noise-overlay min-h-screen bg-vault-bg text-vault-text">
      <MarketingNavbar />
      <HeroSection />
      <SocialProofBar />
      <FeaturesGrid />
      <HowItWorks />
      <PricingSection />
      <CtaFinal />
      <MarketingFooter />
    </div>
  );
}

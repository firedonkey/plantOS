export type EvtUseCaseCard = {
  id: string;
  title: string;
  description: string;
  icon: "enthusiasts" | "smart-home" | "education" | "manufacturing";
};

export const evtUseCaseCards: EvtUseCaseCard[] = [
  {
    id: "plant-enthusiasts",
    title: "Plant Enthusiasts",
    description: "Smarter care for passionate plant lovers.",
    icon: "enthusiasts",
  },
  {
    id: "smart-home",
    title: "Smart Home Users",
    description: "Seamless integration with your smart home.",
    icon: "smart-home",
  },
  {
    id: "stem-education",
    title: "STEM Education",
    description: "Real-world data for hands-on learning.",
    icon: "education",
  },
  {
    id: "manufacturers",
    title: "Manufacturers",
    description: "Reliable monitoring for better products.",
    icon: "manufacturing",
  },
];

export const evtCaseStats = [
  { id: "days", value: "30 Days", label: "Growth Window" },
  { id: "photos", value: "720 Photos", label: "Image History" },
  { id: "timelapse", value: "15s Timelapse", label: "Preview" },
] as const;

export const PERSONALITY_DIMENSIONS = [
  { id: "mind", label: "Mind", left: "Introverted (I)", right: "Extraverted (E)" },
  { id: "energy", label: "Energy", left: "Observant (S)", right: "Intuitive (N)" },
  { id: "nature", label: "Nature", left: "Thinking (T)", right: "Feeling (F)" },
  { id: "tactics", label: "Tactics", left: "Judging (J)", right: "Prospecting (P)" },
] as const;

export type PersonalityDimensionId = "mind" | "energy" | "nature" | "tactics";

export type PersonalityQuestion = {
  id: string;
  dimension: PersonalityDimensionId;
  text: string;
};

export const PERSONALITY_QUESTIONS: PersonalityQuestion[] = [
  { id: "mind_1", dimension: "mind", text: "You find it easy to introduce yourself to other people." },
  { id: "mind_2", dimension: "mind", text: "You often prefer to spend time with a small group of close friends rather than a large group." },
  { id: "mind_3", dimension: "mind", text: "You tend to be quiet and reserved in unfamiliar situations." },
  { id: "mind_4", dimension: "mind", text: "After a busy day, you recharge best by being around other people." },
  { id: "mind_5", dimension: "mind", text: "You usually think out loud and talk through ideas with others." },
  { id: "mind_6", dimension: "mind", text: "You prefer to work independently rather than in a lively group setting." },
  { id: "mind_7", dimension: "mind", text: "You feel energized by social events and networking." },
  { id: "mind_8", dimension: "mind", text: "You often need quiet time alone to think clearly." },
  { id: "mind_9", dimension: "mind", text: "You are comfortable being the center of attention." },
  { id: "mind_10", dimension: "mind", text: "You would rather observe a conversation than lead it." },
  { id: "energy_1", dimension: "energy", text: "You rely more on your experience than on your imagination when making decisions." },
  { id: "energy_2", dimension: "energy", text: "You enjoy thinking about possibilities and what could be, not just what is." },
  { id: "energy_3", dimension: "energy", text: "You focus on concrete facts and details rather than abstract theories." },
  { id: "energy_4", dimension: "energy", text: "You find it easy to think of new ways to do things." },
  { id: "energy_5", dimension: "energy", text: "You prefer sticking to proven methods over experimenting." },
  { id: "energy_6", dimension: "energy", text: "You often notice patterns and connections that others miss." },
  { id: "energy_7", dimension: "energy", text: "You are more practical than visionary." },
  { id: "energy_8", dimension: "energy", text: "You are drawn to big-picture thinking and future trends." },
  { id: "energy_9", dimension: "energy", text: "You trust established routines and procedures." },
  { id: "energy_10", dimension: "energy", text: "You enjoy brainstorming speculative ideas, even if they are not realistic." },
  { id: "nature_1", dimension: "nature", text: "You base your decisions more on logic than on how they affect people." },
  { id: "nature_2", dimension: "nature", text: "You find it important to acknowledge other people's feelings." },
  { id: "nature_3", dimension: "nature", text: "You would rather point out the truth than spare someone's feelings." },
  { id: "nature_4", dimension: "nature", text: "You value harmony in a team over being objectively right." },
  { id: "nature_5", dimension: "nature", text: "You tend to make decisions with your head rather than your heart." },
  { id: "nature_6", dimension: "nature", text: "You are quick to praise the efforts of others." },
  { id: "nature_7", dimension: "nature", text: "You find it easy to separate personal feelings from professional decisions." },
  { id: "nature_8", dimension: "nature", text: "You are moved by other people's stories and struggles." },
  { id: "nature_9", dimension: "nature", text: "You prefer direct, honest feedback even when it is harsh." },
  { id: "nature_10", dimension: "nature", text: "You consider team morale as important as results." },
  { id: "tactics_1", dimension: "tactics", text: "You like to have a clear plan before starting a project." },
  { id: "tactics_2", dimension: "tactics", text: "You are comfortable with last-minute changes to your schedule." },
  { id: "tactics_3", dimension: "tactics", text: "You tend to finish tasks well ahead of their deadlines." },
  { id: "tactics_4", dimension: "tactics", text: "You enjoy improvising rather than following a strict schedule." },
  { id: "tactics_5", dimension: "tactics", text: "You prefer your day to be structured and organized." },
  { id: "tactics_6", dimension: "tactics", text: "You are open to changing your plans at the last minute." },
  { id: "tactics_7", dimension: "tactics", text: "You create to-do lists and like to tick items off." },
  { id: "tactics_8", dimension: "tactics", text: "You like to keep your options open rather than commit early." },
  { id: "tactics_9", dimension: "tactics", text: "You find it stressful when plans keep changing." },
  { id: "tactics_10", dimension: "tactics", text: "You work best with freedom and flexibility rather than rigid rules." },
];

export type CompanyValue = { label: string; description: string };

export const COMPANY_VALUES: Record<string, CompanyValue> = {
  innovation: { label: "Innovation", description: "Creativity, new ideas, and continuous improvement" },
  integrity: { label: "Integrity", description: "Honesty, transparency, and ethical conduct" },
  collaboration: { label: "Collaboration", description: "Teamwork, inclusion, and mutual support" },
  customer_centricity: { label: "Customer centricity", description: "Putting customers and their needs first" },
  sustainability: { label: "Sustainability", description: "Environmental and social responsibility" },
  excellence: { label: "Excellence", description: "High quality standards and mastery" },
  autonomy: { label: "Autonomy", description: "Independence, freedom, and self-direction" },
  agility: { label: "Agility", description: "Flexibility, speed, and adaptiveness" },
  growth: { label: "Growth", description: "Learning, development, and progress" },
  security: { label: "Security", description: "Stability, safety, and predictability" },
  diversity: { label: "Diversity", description: "Valuing different backgrounds and perspectives" },
  work_life_balance: { label: "Work-life balance", description: "Well-being and balance between work and life" },
  impact: { label: "Impact", description: "Making a meaningful difference" },
  profitability: { label: "Profitability", description: "Financial performance and efficiency" },
};

export type ValueQuestion = {
  id: string;
  statement: string;
  values: string[];
};

export const VALUE_QUESTIONS: ValueQuestion[] = [
  { id: "value_1", statement: "I get the most satisfaction at work when I can put my creative ideas into practice.", values: ["innovation"] },
  { id: "value_2", statement: "I would rather work for a company that is honest and transparent than one that bends the rules.", values: ["integrity"] },
  { id: "value_3", statement: "I perform at my best when I am part of a supportive, inclusive team.", values: ["collaboration", "diversity"] },
  { id: "value_4", statement: "Understanding the customer deeply and serving their needs is what motivates me.", values: ["customer_centricity"] },
  { id: "value_5", statement: "Working for an organization that cares about the environment is important to me.", values: ["sustainability"] },
  { id: "value_6", statement: "I take pride in delivering work of the highest possible quality.", values: ["excellence"] },
  { id: "value_7", statement: "I thrive when I am given responsibility and the freedom to make my own decisions.", values: ["autonomy"] },
  { id: "value_8", statement: "I enjoy adapting quickly when priorities change and moving fast.", values: ["agility"] },
  { id: "value_9", statement: "Continuous learning and personal development are at the core of my career.", values: ["growth"] },
  { id: "value_10", statement: "I value a predictable, stable work environment where I feel secure.", values: ["security"] },
  { id: "value_11", statement: "I want my work to fit around my life and protect my well-being.", values: ["work_life_balance"] },
  { id: "value_12", statement: "I am driven by the desire to make a real difference in the world.", values: ["impact"] },
  { id: "value_13", statement: "I care about results and efficiency more than almost anything else.", values: ["profitability"] },
];

export type DimensionResult = {
  score: number;
  pole: "left" | "right";
  confidence: number;
};

export type PersonalityProfile = {
  dimensions: Record<PersonalityDimensionId, DimensionResult>;
  type_code: string;
};

export function computePersonalityProfile(responses: Record<string, number>): PersonalityProfile {
  const dims: Record<PersonalityDimensionId, number[]> = {
    mind: [],
    energy: [],
    nature: [],
    tactics: [],
  };
  for (const q of PERSONALITY_QUESTIONS) {
    const a = responses[q.id];
    if (a == null) continue;
    dims[q.dimension].push(a);
  }

  const dimensions = {} as Record<PersonalityDimensionId, DimensionResult>;
  const letterMap: Record<PersonalityDimensionId, [string, string]> = {
    mind: ["I", "E"],
    energy: ["S", "N"],
    nature: ["T", "F"],
    tactics: ["J", "P"],
  };
  let type_code = "";
  for (const dim of PERSONALITY_DIMENSIONS) {
    const vals = dims[dim.id];
    const score = vals.length ? Math.round(((vals.reduce((a, b) => a + b, 0) / vals.length - 1) / 6) * 1000) / 10 : 50;
    const pole = score >= 50 ? "right" : "left";
    const confidence = Math.round(Math.abs(score - 50) / 50 * 1000) / 10;
    dimensions[dim.id] = { score, pole, confidence };
    type_code += score >= 50 ? letterMap[dim.id][1] : letterMap[dim.id][0];
  }
  return { dimensions, type_code };
}

export type RankedValue = { value: string; label: string; score: number };

export function computeRankedValues(responses: Record<string, number>): RankedValue[] {
  const scores: Record<string, number> = {};
  const counts: Record<string, number> = {};
  for (const vid of Object.keys(COMPANY_VALUES)) {
    scores[vid] = 0;
    counts[vid] = 0;
  }
  for (const q of VALUE_QUESTIONS) {
    const a = responses[q.id];
    if (a == null) continue;
    const w = a / 5;
    for (const vid of q.values) {
      scores[vid] += w;
      counts[vid] += 1;
    }
  }
  const ranked: RankedValue[] = Object.keys(scores).map((vid) => {
    const n = counts[vid] || 1;
    return { value: vid, label: COMPANY_VALUES[vid].label, score: Math.round((scores[vid] / n) * 1000) / 10 };
  });
  return ranked.sort((a, b) => b.score - a.score);
}

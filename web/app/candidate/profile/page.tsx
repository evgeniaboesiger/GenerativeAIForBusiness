'use client';

import { useMemo, useState } from 'react';
import { PERSONALITY_DIMENSIONS } from '../../../lib/assessment';

type ReviewStatus = 'extracted' | 'needs_review' | 'candidate_confirmed';
type Provenance = {
  source: string;
  confidence: number;
  status: 'verified' | 'unverified' | 'needs_review';
};

type SkillItem = {
  name: string;
  level?: string;
  status: ReviewStatus;
  provenance: Provenance;
};

type WorkExperience = {
  company: string;
  title: string;
  start_date?: string;
  end_date?: string;
  status: ReviewStatus;
  provenance: Provenance;
};

type LanguageItem = {
  language: string;
  level?: string;
  status: ReviewStatus;
  provenance: Provenance;
};

type CandidateProfile = {
  name: string;
  skills: SkillItem[];
  work_experience: WorkExperience[];
  education: Array<{ degree: string; field: string; institution: string; status: ReviewStatus; provenance: Provenance }>;
  languages: LanguageItem[];
  preferred_employment_percentage?: number;
  preferred_locations?: string[];
  remote_preference?: string;
  salary_expectation?: { min: number; max: number; currency: string } | null;
  career_goals?: string[];
  availability?: string;
};

const initialProfile: CandidateProfile = {
  name: 'Anna Keller',
  skills: [
    { name: 'Python', level: 'advanced', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.96, status: 'verified' } },
    { name: 'AWS', level: 'advanced', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.9, status: 'verified' } },
    { name: 'digital transformation', status: 'needs_review', provenance: { source: 'cv', confidence: 0.42, status: 'needs_review' } },
  ],
  work_experience: [
    { company: 'Alpine Data AG', title: 'Senior Python Developer', start_date: '2020', end_date: '2023', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.92, status: 'verified' } },
    { company: 'Nova Analytics', title: 'Data Engineer', start_date: '2016', end_date: '2020', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.9, status: 'verified' } },
  ],
  education: [
    { degree: 'BSc', field: 'Computer Science', institution: 'ETH Zurich', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.88, status: 'verified' } },
  ],
  languages: [
    { language: 'German', level: 'C2', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.95, status: 'verified' } },
    { language: 'English', level: 'C1', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.94, status: 'verified' } },
    { language: 'French', level: 'B1', status: 'candidate_confirmed', provenance: { source: 'cv', confidence: 0.8, status: 'unverified' } },
  ],
  preferred_employment_percentage: 80,
  preferred_locations: ['Zurich', 'Basel'],
  remote_preference: 'yes',
  salary_expectation: { min: 110000, max: 130000, currency: 'CHF' },
  career_goals: ['Senior platform engineer'],
  availability: '2025-02-01',
};

const badgeStyles: Record<ReviewStatus, string> = {
  extracted: 'bg-slate-100 text-slate-700 border-slate-300',
  needs_review: 'bg-amber-100 text-amber-800 border-amber-300',
  candidate_confirmed: 'bg-emerald-100 text-emerald-800 border-emerald-300',
};

const labelForStatus = (status: ReviewStatus) => {
  if (status === 'candidate_confirmed') return 'Candidate confirmed';
  if (status === 'needs_review') return 'Needs review';
  return 'Extracted';
};

export default function CandidateProfilePage() {
  const [profile, setProfile] = useState<CandidateProfile>(initialProfile);

  const totalReviewItems = useMemo(() => {
    return profile.skills.length + profile.work_experience.length + profile.languages.length + profile.education.length;
  }, [profile]);

  const needsReviewCount = useMemo(() => {
    return profile.skills.filter((item) => item.status === 'needs_review').length
      + profile.work_experience.filter((item) => item.status === 'needs_review').length
      + profile.languages.filter((item) => item.status === 'needs_review').length
      + profile.education.filter((item) => item.status === 'needs_review').length;
  }, [profile]);

  function toggleItemStatus(itemStatus: ReviewStatus) {
    const nextStatus: ReviewStatus = itemStatus === 'candidate_confirmed' ? 'needs_review' : 'candidate_confirmed';
    setProfile((current) => ({
      ...current,
      skills: current.skills.map((item) => ({ ...item, status: item.status === itemStatus ? nextStatus : item.status })),
      work_experience: current.work_experience.map((item) => ({ ...item, status: item.status === itemStatus ? nextStatus : item.status })),
      languages: current.languages.map((item) => ({ ...item, status: item.status === itemStatus ? nextStatus : item.status })),
      education: current.education.map((item) => ({ ...item, status: item.status === itemStatus ? nextStatus : item.status })),
    }));
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-500">Candidate profile</p>
          <h1 className="text-3xl font-bold">{profile.name}</h1>
        </div>

        <div className="flex gap-2 text-sm">
          <span className="border rounded-full px-3 py-1 bg-slate-100 text-slate-700">Extracted</span>
          <span className="border rounded-full px-3 py-1 bg-amber-100 text-amber-800">Needs review</span>
          <span className="border rounded-full px-3 py-1 bg-emerald-100 text-emerald-800">Candidate confirmed</span>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <div className="rounded-xl border p-4 bg-white shadow-sm">
          <div className="text-sm text-slate-500">Fields reviewed</div>
          <div className="text-2xl font-bold">{totalReviewItems}</div>
        </div>
        <div className="rounded-xl border p-4 bg-white shadow-sm">
          <div className="text-sm text-slate-500">Needs review</div>
          <div className="text-2xl font-bold text-amber-700">{needsReviewCount}</div>
        </div>
        <div className="rounded-xl border p-4 bg-white shadow-sm">
          <div className="text-sm text-slate-500">Verification status</div>
          <div className="text-2xl font-bold">Unverified</div>
        </div>
      </div>

      <div className="space-y-6">
        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Summary</h2>
            <button
              className="text-sm border rounded px-3 py-1 hover:bg-slate-50"
              onClick={() => toggleItemStatus('candidate_confirmed')}
            >
              Toggle candidate review state
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div><span className="font-medium text-slate-600">Preferred employment:</span> {profile.preferred_employment_percentage}%</div>
            <div><span className="font-medium text-slate-600">Remote preference:</span> {profile.remote_preference ?? 'Unknown'}</div>
            <div><span className="font-medium text-slate-600">Preferred locations:</span> {profile.preferred_locations?.join(', ') ?? 'Unknown'}</div>
            <div><span className="font-medium text-slate-600">Availability:</span> {profile.availability ?? 'Unknown'}</div>
            <div className="md:col-span-2">
              <span className="font-medium text-slate-600">Salary expectation:</span> {profile.salary_expectation ? `${profile.salary_expectation.currency} ${profile.salary_expectation.min.toLocaleString()} - ${profile.salary_expectation.max.toLocaleString()}` : 'Unknown'}
            </div>
            <div className="md:col-span-2">
              <span className="font-medium text-slate-600">Career goals:</span> {profile.career_goals?.join(', ') ?? 'Unknown'}
            </div>
          </div>
        </section>

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Skills</h2>
          <div className="space-y-3">
            {profile.skills.map((skill, index) => (
              <div key={`${skill.name}-${index}`} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <div className="font-medium">{skill.name}</div>
                  <div className="text-xs text-slate-500">Source: {skill.provenance.source} · Confidence: {skill.provenance.confidence}</div>
                </div>
                <div className="flex items-center gap-2">
                  {skill.level ? <span className="text-xs bg-slate-100 rounded px-2 py-1">{skill.level}</span> : null}
                  <span className={`border rounded-full px-2 py-1 text-xs ${badgeStyles[skill.status]}`}>
                    {labelForStatus(skill.status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Work experience</h2>
          <div className="space-y-3">
            {profile.work_experience.map((item, index) => (
              <div key={`${item.company}-${index}`} className="rounded-lg border p-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-semibold">{item.title}</div>
                    <div className="text-sm text-slate-600">{item.company}</div>
                  </div>
                  <span className={`border rounded-full px-2 py-1 text-xs ${badgeStyles[item.status]}`}>
                    {labelForStatus(item.status)}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-2">
                  {item.start_date ?? 'Unknown'} - {item.end_date ?? 'Current'}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Education</h2>
          <div className="space-y-3">
            {profile.education.map((item, index) => (
              <div key={`${item.institution}-${index}`} className="rounded-lg border p-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium">{item.degree} in {item.field}</div>
                    <div className="text-sm text-slate-600">{item.institution}</div>
                  </div>
                  <span className={`border rounded-full px-2 py-1 text-xs ${badgeStyles[item.status]}`}>
                    {labelForStatus(item.status)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Languages</h2>
          <div className="flex flex-wrap gap-3">
            {profile.languages.map((language, index) => (
              <div key={`${language.language}-${index}`} className="border rounded-lg px-3 py-2 text-sm">
                <span className="font-medium">{language.language}</span>
                <span className="text-slate-500 ml-2">{language.level}</span>
                <span className={`ml-2 border rounded-full px-2 py-0.5 text-[10px] ${badgeStyles[language.status]}`}>
                  {labelForStatus(language.status)}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Personality &amp; Values</h2>
            <a href="/candidate/assessment" className="text-sm text-accent hover:underline">
              Take / update assessment
            </a>
          </div>
          <p className="text-sm text-slate-500 mb-4">
            Your personality type and top values are matched against the culture and values of every job offer.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="border rounded-lg p-4">
              <div className="text-sm text-slate-500 mb-2">Personality traits</div>
              <div className="space-y-2">
                {PERSONALITY_DIMENSIONS.map((dim) => (
                  <div key={dim.id} className="flex justify-between text-sm">
                    <span>{dim.label}</span>
                    <span className="text-slate-500">—</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="border rounded-lg p-4">
              <div className="text-sm text-slate-500 mb-2">Top values</div>
              <div className="space-y-2">
                {['—', '—', '—', '—', '—'].map((v, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span className="text-slate-400">Value {i + 1}</span>
                    <span className="text-slate-400">—</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

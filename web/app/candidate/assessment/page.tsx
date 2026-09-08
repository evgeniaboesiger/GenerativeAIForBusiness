'use client';

import { useMemo, useState } from 'react';
import {
  PERSONALITY_DIMENSIONS,
  PERSONALITY_QUESTIONS,
  VALUE_QUESTIONS,
  COMPANY_VALUES,
  computePersonalityProfile,
  computeRankedValues,
  type RankedValue,
} from '../../../lib/assessment';

type Step = 'personality' | 'values' | 'results';

const SCALE_LABELS_P = ['Strongly disagree', 'Disagree', 'Somewhat disagree', 'Neutral', 'Somewhat agree', 'Agree', 'Strongly agree'];
const SCALE_LABELS_V = ['Not important to me', 'Somewhat important', 'Important', 'Very important', 'Essential to me'];

export default function AssessmentPage() {
  const [step, setStep] = useState<Step>('personality');
  const [pResponses, setPResponses] = useState<Record<string, number>>({});
  const [vResponses, setVResponses] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);

  const pAnswered = PERSONALITY_QUESTIONS.filter((q) => pResponses[q.id]).length;
  const vAnswered = VALUE_QUESTIONS.filter((q) => vResponses[q.id]).length;
  const personalityProfile = useMemo(() => computePersonalityProfile(pResponses), [pResponses]);
  const rankedValues = useMemo(() => computeRankedValues(vResponses), [vResponses]);

  const questionsRemaining = PERSONALITY_QUESTIONS.length - pAnswered;

  function pChange(id: string, value: number) {
    setPResponses((cur) => ({ ...cur, [id]: value }));
  }
  function vChange(id: string, value: number) {
    setVResponses((cur) => ({ ...cur, [id]: value }));
  }

  async function submitAll() {
    setSubmitting(true);
    try {
      await Promise.all([
        fetch('/api/assessment/personality', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate_id: null, responses: pResponses }),
        }),
        fetch('/api/assessment/values', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate_id: null, responses: vResponses }),
        }),
      ]);
    } catch {
      // offline demo: still show local results
    } finally {
      setSubmitting(false);
    }
    setStep('results');
  }

  const progress =
    step === 'personality' ? pAnswered / PERSONALITY_QUESTIONS.length : vAnswered / VALUE_QUESTIONS.length;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-500">Candidate assessment</p>
          <h1 className="text-3xl font-bold text-navy">Personality &amp; Values</h1>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {(['personality', 'values', 'results'] as Step[]).map((s) => (
          <button
            key={s}
            onClick={() => setStep(s)}
            disabled={s === 'results' && pAnswered < PERSONALITY_QUESTIONS.length}
            className={`text-sm px-4 py-2 rounded-full border capitalize ${
              step === s ? 'bg-accent text-white border-accent' : 'bg-white text-slate-600 border-slate-300'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {step === 'personality' ? (
        <div>
          <div className="mb-4">
            <div className="flex justify-between text-sm text-slate-500 mb-1">
              <span>{pAnswered} / {PERSONALITY_QUESTIONS.length} answered</span>
              {questionsRemaining > 0 && <span>{questionsRemaining} remaining</span>}
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-accent transition-all" style={{ width: `${progress * 100}%` }} />
            </div>
          </div>

          {PERSONALITY_DIMENSIONS.map((dim) => {
            const questions = PERSONALITY_QUESTIONS.filter((q) => q.dimension === dim.id);
            return (
              <section key={dim.id} className="card mb-6">
                <div className="border-b pb-2 mb-4">
                  <h2 className="text-xl font-semibold text-navy">{dim.label}</h2>
                  <p className="text-sm text-slate-500">{dim.left} &mdash; {dim.right}</p>
                </div>
                <div className="space-y-5">
                  {questions.map((q) => (
                    <div key={q.id}>
                      <p className="font-medium text-navy mb-2">{q.text}</p>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-500 w-24 pr-2">{dim.left.replace(/ \(.\)$/, '')}</span>
                        <div className="flex flex-1 gap-1">
                          {SCALE_LABELS_P.map((label, i) => {
                            const value = i + 1;
                            const selected = pResponses[q.id] === value;
                            return (
                              <button
                                key={value}
                                onClick={() => pChange(q.id, value)}
                                title={label}
                                className={`flex-1 h-12 rounded-md border text-xs transition-all ${
                                  selected
                                    ? 'bg-accent border-accent text-white'
                                    : 'bg-white border-slate-300 text-slate-500 hover:border-accent'
                                }`}
                              >
                                {value}
                              </button>
                            );
                          })}
                        </div>
                        <span className="text-xs text-slate-500 w-24 pl-2">{dim.right.replace(/ \(.\)$/, '')}</span>
                      </div>
                      <p className="text-[10px] text-slate-400 text-center mt-1">{SCALE_LABELS_P[pResponses[q.id] ? pResponses[q.id] - 1 : 3]}</p>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}

          <div className="flex justify-end">
            <button
              onClick={() => setStep('values')}
              disabled={pAnswered < PERSONALITY_QUESTIONS.length}
              className="px-5 py-2 bg-accent text-white rounded-lg disabled:opacity-40"
            >
              Continue to Values →
            </button>
          </div>
        </div>
      ) : null}

      {step === 'values' ? (
        <div>
          <div className="mb-4">
            <div className="flex justify-between text-sm text-slate-500 mb-1">
              <span>{vAnswered} / {VALUE_QUESTIONS.length} answered</span>
              {vAnswered < VALUE_QUESTIONS.length && <span>{VALUE_QUESTIONS.length - vAnswered} remaining</span>}
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-accent transition-all" style={{ width: `${progress * 100}%` }} />
            </div>
          </div>
          <p className="text-sm text-slate-600 mb-6">
            Rate how important each statement is to you. Your answers reveal which values matter most in a workplace,
            and we match them against the values of companies offering jobs.
          </p>

          <section className="card">
            <div className="space-y-6">
              {VALUE_QUESTIONS.map((q) => (
                <div key={q.id}>
                  <p className="font-medium text-navy mb-2">{q.statement}</p>
                  <div className="flex gap-2">
                    {SCALE_LABELS_V.map((label, i) => {
                      const value = i + 1;
                      const selected = vResponses[q.id] === value;
                      return (
                        <button
                          key={value}
                          onClick={() => vChange(q.id, value)}
                          className={`flex-1 h-20 rounded-lg border text-center text-xs px-1 transition-all ${
                            selected
                              ? 'bg-accent border-accent text-white'
                              : 'bg-white border-slate-300 text-slate-600 hover:border-accent'
                          }`}
                        >
                          <span className="block text-base font-bold">{value}</span>
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="flex justify-between mt-6">
            <button onClick={() => setStep('personality')} className="px-5 py-2 border rounded-lg text-slate-600">
              ← Back
            </button>
            <button
              onClick={submitAll}
              disabled={vAnswered < VALUE_QUESTIONS.length || submitting}
              className="px-5 py-2 bg-accent text-white rounded-lg disabled:opacity-40"
            >
              {submitting ? 'Saving…' : 'See my results →'}
            </button>
          </div>
        </div>
      ) : null}

      {step === 'results' ? (
        <div className="space-y-6">
          <section className="card">
            <h2 className="text-xl font-semibold text-navy mb-2">Your personality type</h2>
            <p className="text-5xl font-bold text-accent mb-4">{personalityProfile.type_code}</p>
            <div className="grid md:grid-cols-2 gap-4">
              {PERSONALITY_DIMENSIONS.map((dim) => {
                const r = personalityProfile.dimensions[dim.id];
                const pct = r.pole === 'right' ? r.score : 100 - r.score;
                return (
                  <div key={dim.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-medium">{dim.label}</span>
                      <span className="text-sm text-slate-500">
                        {r.pole === 'right' ? dim.right : dim.left} ({pct.toFixed(0)}%)
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full">
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${pct}%`, marginLeft: r.pole === 'left' ? 'auto' : 0 }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-sm text-slate-500 mt-3">
              This type helps us suggest suitable work cultures — it is used only for alignment, never to filter you out unfairly.
            </p>
          </section>

          <section className="card">
            <h2 className="text-xl font-semibold text-navy mb-2">Your top values</h2>
            <div className="space-y-2">
              {rankedValues.slice(0, 5).map((v: RankedValue, i) => (
                <div key={v.value} className="flex items-center gap-3 border rounded-lg p-3">
                  <span className="w-7 h-7 rounded-full bg-accent text-white flex items-center justify-center text-sm font-semibold">
                    {i + 1}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium">{v.label}</div>
                    <div className="text-xs text-slate-500">{COMPANY_VALUES[v.value].description}</div>
                  </div>
                  <span className="text-sm text-slate-500">{v.score.toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <p className="text-sm text-slate-500 mt-3">
              These are compared against the values each company declares to measure how well you align.
            </p>
          </section>

          <div className="flex justify-between">
            <button onClick={() => setStep('values')} className="px-5 py-2 border rounded-lg text-slate-600">
              ← Edit answers
            </button>
            <a href="/candidate/dashboard" className="px-5 py-2 bg-accent text-white rounded-lg">
              Go to dashboard
            </a>
          </div>
        </div>
      ) : null}
    </div>
  );
}

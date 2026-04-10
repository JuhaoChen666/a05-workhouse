export type InterviewMode = 'text' | 'avatar';
export type InterviewDifficulty = 'easy' | 'medium' | 'hard';

export interface InterviewSetupDraft {
  mode: InterviewMode;
  avatarId?: string;
  useResume: boolean;
  resumeId?: number;
  resumeName?: string;
  resumeType?: string;
  positionName: string;
  positionDetail: string;
  difficulty: InterviewDifficulty;
  enableFollowup: boolean;
  maxRounds: number;
}

const STORAGE_KEY = 'interview_setup_draft_v1';

export const defaultInterviewSetupDraft: InterviewSetupDraft = {
  mode: 'text',
  avatarId: '110592024',
  useResume: false,
  positionName: '',
  positionDetail: '',
  difficulty: 'medium',
  enableFollowup: true,
  maxRounds: 8,
};

export function loadInterviewSetupDraft(): InterviewSetupDraft {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...defaultInterviewSetupDraft };
    const obj = JSON.parse(raw) as Partial<InterviewSetupDraft>;
    return { ...defaultInterviewSetupDraft, ...obj };
  } catch {
    return { ...defaultInterviewSetupDraft };
  }
}

export function saveInterviewSetupDraft(patch: Partial<InterviewSetupDraft>) {
  const next = { ...loadInterviewSetupDraft(), ...patch };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}


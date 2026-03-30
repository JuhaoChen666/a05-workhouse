import request from './request';

export interface AbilityBarItem {
  name: string;
  value: number;
}

export interface AbilityRadarItem {
  name: string;
  value: number;
  max?: number;
}

export interface AbilityAnalysis {
  bar: AbilityBarItem[];
  radar: AbilityRadarItem[];
}

export function getAbilityAnalysisApi() {
  return request.get<AbilityAnalysis>('/user/ability-analysis');
}

/** 后端在追问流中下发的占位提示文案（用于识别为「追问提示」气泡，无复制按钮） */
const NORMALIZED_FOLLOWUP_PLACEHOLDER = '回答不够深入，准备追问...'.replace(/\s+/g, '');

export function isFollowupProgressPlaceholderMessage(message: string): boolean {
  return String(message || '').replace(/\s+/g, '') === NORMALIZED_FOLLOWUP_PLACEHOLDER;
}

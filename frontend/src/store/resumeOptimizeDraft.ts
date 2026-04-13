import { defineStore } from 'pinia';

export type ResumeOptimizePreviewKind = 'pdf' | 'text';

interface State {
  /** 已在弹窗中确认并进入预览区 */
  hasPreview: boolean;
  /** 提交给优化 import 接口的文件 */
  payloadFile: File | null;
  /** 用户原始简历文件名，用于保存「我的简历」时生成「原名（优化版）」 */
  originalFilename: string;
  previewKind: ResumeOptimizePreviewKind;
  previewPdfObjectUrl: string;
  previewText: string;
}

export const useResumeOptimizeDraftStore = defineStore('resumeOptimizeDraft', {
  state: (): State => ({
    hasPreview: false,
    payloadFile: null,
    originalFilename: '',
    previewKind: 'pdf',
    previewPdfObjectUrl: '',
    previewText: '',
  }),
  actions: {
    revokePdfPreviewUrl() {
      if (this.previewPdfObjectUrl) {
        URL.revokeObjectURL(this.previewPdfObjectUrl);
        this.previewPdfObjectUrl = '';
      }
    },
    reset() {
      this.revokePdfPreviewUrl();
      this.hasPreview = false;
      this.payloadFile = null;
      this.originalFilename = '';
      this.previewKind = 'pdf';
      this.previewText = '';
    },
    setFromPdfFile(file: File, originalFilenameOverride?: string) {
      this.revokePdfPreviewUrl();
      this.payloadFile = file;
      this.originalFilename = (originalFilenameOverride || file.name).trim() || file.name;
      this.previewKind = 'pdf';
      this.previewPdfObjectUrl = URL.createObjectURL(file);
      this.previewText = '';
      this.hasPreview = true;
    },
    setFromLibraryFile(file: File, listDisplayName: string) {
      this.revokePdfPreviewUrl();
      this.payloadFile = file;
      this.originalFilename = listDisplayName.trim() || file.name;
      this.previewKind = 'pdf';
      this.previewPdfObjectUrl = URL.createObjectURL(file);
      this.previewText = '';
      this.hasPreview = true;
    },
    /** 从运行页返回预览时若已 revoke 过 blob URL，则按 payloadFile 重建 */
    ensurePdfPreviewUrl() {
      if (this.hasPreview && this.previewKind === 'pdf' && this.payloadFile && !this.previewPdfObjectUrl) {
        this.previewPdfObjectUrl = URL.createObjectURL(this.payloadFile);
      }
    },
  },
});

declare module 'mammoth/mammoth.browser' {
  export interface ConvertResult {
    value: string;
    messages?: Array<unknown>;
  }
  export interface MammothBrowser {
    convertToHtml(input: { arrayBuffer: ArrayBuffer }): Promise<ConvertResult>;
    extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<ConvertResult>;
  }
  const mammoth: MammothBrowser;
  export default mammoth;
}

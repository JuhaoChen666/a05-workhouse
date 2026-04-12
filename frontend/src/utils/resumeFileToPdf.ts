import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import mammoth from 'mammoth/mammoth.browser';

/** 与 A4 比例接近的内容区宽度（px），便于 html2canvas */
const WRAPPER_WIDTH_PX = 794;

function filenameStem(name: string): string {
  const base = name.trim().split(/[/\\]/).pop() || 'resume';
  const i = base.lastIndexOf('.');
  const stem = i > 0 ? base.slice(0, i) : base;
  return stem.replace(/[^\w\u4e00-\u9fa5\-_.\s]/g, '_').trim() || 'resume';
}

async function nodeToPdfFile(wrapper: HTMLElement, outName: string): Promise<File> {
  document.body.appendChild(wrapper);
  try {
    const canvas = await html2canvas(wrapper, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
    });
    const imgData = canvas.toDataURL('image/png', 1);
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = pdfWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = 0;
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pdfHeight;

    while (heightLeft > 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pdfHeight;
    }

    const blob = pdf.output('blob');
    const safeName = outName.toLowerCase().endsWith('.pdf') ? outName : `${outName}.pdf`;
    return new File([blob], safeName, { type: 'application/pdf' });
  } finally {
    document.body.removeChild(wrapper);
  }
}

function createTextWrapper(text: string): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.style.cssText = [
    `position:fixed`,
    `left:-12000px`,
    `top:0`,
    `width:${WRAPPER_WIDTH_PX}px`,
    `box-sizing:border-box`,
    `padding:48px 56px`,
    `background:#fff`,
    `color:#111827`,
    `font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif`,
    `font-size:14px`,
    `line-height:1.75`,
    `white-space:pre-wrap`,
    `word-break:break-word`,
  ].join(';');
  wrapper.textContent = text;
  return wrapper;
}

function createHtmlWrapper(html: string): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'resume-docx-html';
  wrapper.style.cssText = [
    `position:fixed`,
    `left:-12000px`,
    `top:0`,
    `width:${WRAPPER_WIDTH_PX}px`,
    `box-sizing:border-box`,
    `padding:48px 56px`,
    `background:#fff`,
    `color:#111827`,
    `font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif`,
    `font-size:14px`,
    `line-height:1.6`,
    `word-break:break-word`,
  ].join(';');
  const style = document.createElement('style');
  style.textContent = `
    .resume-docx-html p { margin: 0.45em 0; }
    .resume-docx-html h1,.resume-docx-html h2,.resume-docx-html h3 { margin: 0.6em 0 0.35em; font-weight: 700; }
    .resume-docx-html table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
    .resume-docx-html td,.resume-docx-html th { border: 1px solid #e5e7eb; padding: 6px 8px; vertical-align: top; }
    .resume-docx-html ul,.resume-docx-html ol { margin: 0.35em 0; padding-left: 1.4em; }
  `;
  wrapper.appendChild(style);
  const inner = document.createElement('div');
  inner.innerHTML = html;
  wrapper.appendChild(inner);
  return wrapper;
}

/** 纯文本 → PDF（用于 txt、文字简历） */
export async function plainTextResumeToPdfFile(text: string, titleStem: string): Promise<File> {
  const stem = titleStem.trim() || '简历';
  const wrapper = createTextWrapper(text.trim() || ' ');
  return nodeToPdfFile(wrapper, `${stem}.pdf`);
}

/** Word HTML → PDF */
export async function wordHtmlToPdfFile(html: string, titleStem: string): Promise<File> {
  const stem = titleStem.trim() || '简历';
  const wrapper = createHtmlWrapper(html);
  return nodeToPdfFile(wrapper, `${stem}.pdf`);
}

/**
 * 将用户上传的简历文件转为 PDF（已是 PDF 则原样返回）。
 * 支持：pdf、txt、docx（Word）；旧版 .doc 可能解析失败。
 */
export async function resumeUploadToPdfFile(file: File): Promise<File> {
  const name = file.name || 'resume';
  const lower = name.toLowerCase();
  const stem = filenameStem(name);

  if (lower.endsWith('.pdf') || file.type === 'application/pdf') {
    return file;
  }

  if (lower.endsWith('.txt') || file.type === 'text/plain') {
    const text = await file.text();
    return plainTextResumeToPdfFile(text, stem);
  }

  if (
    lower.endsWith('.docx') ||
    file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ) {
    const ab = await file.arrayBuffer();
    const { value: html } = await mammoth.convertToHtml({ arrayBuffer: ab });
    return wordHtmlToPdfFile(html, stem);
  }

  if (lower.endsWith('.doc') || file.type === 'application/msword') {
    const ab = await file.arrayBuffer();
    try {
      const { value: html } = await mammoth.convertToHtml({ arrayBuffer: ab });
      if (!html || !html.trim()) {
        throw new Error('empty');
      }
      return wordHtmlToPdfFile(html, stem);
    } catch {
      throw new Error('无法解析 .doc 文件，请将简历另存为 .docx 或 PDF 后再上传');
    }
  }

  throw new Error('不支持的格式，请上传 PDF、Word（docx）或 txt');
}

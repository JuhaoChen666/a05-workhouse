/**
 * 节流：在 wait 毫秒内最多执行一次（首次触发立即执行）
 * 用于按钮提交、滚动等，防止短时间内重复触发
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  wait: number
): (...args: Parameters<T>) => void {
  let last = 0;
  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    if (now - last >= wait) {
      last = now;
      fn.apply(this, args);
    }
  };
}

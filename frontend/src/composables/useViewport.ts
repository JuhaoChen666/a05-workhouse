import { ref, onMounted, onBeforeUnmount } from 'vue';
import { MOBILE_MAX_WIDTH_PX } from '@/constants/breakpoints';

function getIsMobileMatch(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia(`(max-width: ${MOBILE_MAX_WIDTH_PX}px)`).matches;
}

/**
 * 视口是否为移动端宽度（与 MOBILE_MAX_WIDTH_PX 一致）。
 * 用于需在模板中 v-if 切换结构时（如侧栏抽屉）；纯样式优先用 @media。
 */
export function useViewport() {
  const isMobile = ref(getIsMobileMatch());

  let mql: MediaQueryList | null = null;
  const onChange = (e: MediaQueryListEvent) => {
    isMobile.value = e.matches;
  };

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    mql = window.matchMedia(`(max-width: ${MOBILE_MAX_WIDTH_PX}px)`);
    isMobile.value = mql.matches;
    mql.addEventListener('change', onChange);
  });

  onBeforeUnmount(() => {
    mql?.removeEventListener('change', onChange);
  });

  return { isMobile };
}

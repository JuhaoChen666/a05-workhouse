type ThumbnailJob = { cancelled: boolean; run: () => Promise<void> };

const pendingJobs: ThumbnailJob[] = [];
let activeJobs = 0;
const maxConcurrentJobs = 3;

export function queueResumeThumbnail(run: () => Promise<void>) {
  const job: ThumbnailJob = { cancelled: false, run };
  pendingJobs.push(job);
  const pump = () => {
    while (activeJobs < maxConcurrentJobs && pendingJobs.length) {
      const next = pendingJobs.shift()!;
      if (next.cancelled) continue;
      activeJobs++;
      void next.run().finally(() => { activeJobs--; pump(); });
    }
  };
  pump();
  return () => {
    job.cancelled = true;
    const index = pendingJobs.indexOf(job);
    if (index >= 0) pendingJobs.splice(index, 1);
  };
}

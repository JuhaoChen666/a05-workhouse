"""Opt-in test child: real worker/container with a deliberately nonterminating TeX fixture."""
import asyncio
from app.services.resume_worker import run_once
from app.services import resume_generation_service as generation

original_render = generation.render_snapshot


def render_loop(*args, **kwargs):
    rendered = original_render(*args, **kwargs)
    source = rendered.latex_source.replace(r"\end{document}", r"\loop\iftrue\repeat\end{document}")
    return rendered.model_copy(update={"latex_source": source})


generation.render_snapshot = render_loop
asyncio.run(run_once())

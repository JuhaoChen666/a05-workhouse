FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 texlive-xetex texlive-latex-extra texlive-lang-chinese fonts-noto-cjk && apt-get clean \
    && test -n "$(kpsewhich xeCJK.sty)" \
    && fc-match --format='%{family}\n' 'Noto Serif CJK SC' | grep -q 'Noto Serif CJK SC'
COPY compile_resume.py /opt/compile_resume.py
USER 65532:65532
WORKDIR /work

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 texlive-xetex texlive-latex-extra fonts-noto-cjk && apt-get clean
COPY compile_resume.py /opt/compile_resume.py
USER 65532:65532
WORKDIR /work

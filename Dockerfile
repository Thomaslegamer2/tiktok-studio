FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY tiktok_studio.py studio_web.py studio_mobile.html ./

EXPOSE 8765
CMD ["python", "-u", "studio_web.py"]

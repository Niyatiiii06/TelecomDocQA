# TelecomDocQA's FastAPI service as a Docker image.
# The image contains the code, the prebuilt search index and both models,
# so the container starts without downloading anything. Only the LLM is
# called over the network, with the API key passed in as LLM_API_KEY.
#
#   docker build -t telecomdocqa .
#   docker run -p 7860:7860 --env-file .env telecomdocqa

FROM python:3.12-slim

# Run as a normal user, not root (safer, and what most hosts expect).
RUN useradd --create-home --uid 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# 1. Dependencies first: Docker caches this layer, so changing the code
#    later doesn't reinstall everything. No PyTorch: the models run on ONNX Runtime.
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 2. The prebuilt index (from the Hugging Face dataset) and both models.
ARG INDEX_REPO=Niyawwtiiii/telecomdocqa-index
ENV INDEX_REPO=${INDEX_REPO}
COPY --chown=user telecomdocqa/__init__.py telecomdocqa/config.py telecomdocqa/remote_index.py telecomdocqa/
COPY --chown=user data/manifest.json data/
RUN python -m telecomdocqa.remote_index \
 && python -c "from fastembed import TextEmbedding; \
from fastembed.rerank.cross_encoder import TextCrossEncoder; \
from telecomdocqa import config; \
TextEmbedding(config.EMBEDDING_MODEL, cache_dir=str(config.MODEL_CACHE_DIR)); \
TextCrossEncoder(config.RERANKER_MODEL, cache_dir=str(config.MODEL_CACHE_DIR))"

# 3. The rest of the code (changes most often, so it comes last).
COPY --chown=user telecomdocqa/ telecomdocqa/

# Port 7860 by default; hosts that assign a port set $PORT.
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn telecomdocqa.api:app --host 0.0.0.0 --port ${PORT}"]

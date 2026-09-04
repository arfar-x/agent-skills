# Build context MUST be the repo root, not mcp-server/ -- the image needs
# ../skills/ as a sibling directory (see AGENT_SKILLS_REPO_ROOT below).
#
#   docker build -f mcp-server/Dockerfile -t agent-skills-mcp .
#
# TOOLSETS selects which toolsets' own requirements.txt get installed
# alongside mcp-server's -- e.g. --build-arg TOOLSETS="jira confluence".
# Internal skills (metadata.internal: true, e.g. telegram) are deliberately
# never started via --include-internal in CMD: their write-gates assume a
# controlling terminal a headless server doesn't have.
FROM python:3.12-slim

ARG TOOLSETS="jira"

WORKDIR /opt/repo

# Dependencies first, so source-only edits don't invalidate the pip layer.
COPY mcp-server/requirements.txt mcp-server/requirements.txt
COPY skills/ skills/
RUN pip install --no-cache-dir -r mcp-server/requirements.txt \
 && for t in ${TOOLSETS}; do \
      if [ -f "skills/$t/requirements.txt" ]; then \
        pip install --no-cache-dir -r "skills/$t/requirements.txt"; \
      fi; \
    done

COPY . .

ENV AGENT_SKILLS_REPO_ROOT=/opt/repo
USER nobody
EXPOSE 8321
CMD ["python3", "mcp-server/server.py", \
     "--transport", "http", "--host", "0.0.0.0", "--port", "8321"]

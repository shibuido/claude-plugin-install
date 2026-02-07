FROM python:3.10-slim

# Install git (needed for git root detection), tmux (for interactive tests)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git tmux && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up fake home directory structure Claude Code expects
RUN mkdir -p /root/.claude/plugins && \
    echo '{}' > /root/.claude/plugins/installed_plugins.json

WORKDIR /workspace

# Copy the tool and create a python3 wrapper (script has uv shebang, but
# we run it with python3 directly since it has zero dependencies)
COPY claude-plugin-install /usr/local/lib/claude-plugin-install.py
RUN printf '#!/bin/sh\nexec python3 /usr/local/lib/claude-plugin-install.py "$@"\n' \
    > /usr/local/bin/claude-plugin-install && \
    chmod +x /usr/local/bin/claude-plugin-install

# Copy test infrastructure
COPY testing/ /workspace/testing/

# Git init for tests that need a git root
RUN git config --global user.email "test@test.com" && \
    git config --global user.name "Test" && \
    git config --global init.defaultBranch main

ENTRYPOINT ["/bin/bash"]

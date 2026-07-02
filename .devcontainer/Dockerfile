FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LANGUAGE=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git openssh-client procps psmisc \
    less nano vim-tiny make patch sudo \
    ripgrep grep sed gawk findutils fd-find fzf diffutils \
    coreutils file tree xxd tar unzip zip gzip bzip2 xz-utils \
    jq bat libffi-dev libssl-dev \
    dnsutils iputils-ping netcat-openbsd \
    build-essential \
    python3 python3-pip python3-dev python3-venv \
    sqlite3 \
    bubblewrap \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) \
      signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
      https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y --no-install-recommends gh \
 && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/fdfind /usr/local/bin/fd \
 && ln -sf /usr/bin/batcat /usr/local/bin/bat

# --- Пакеты конкретного проекта: добавляй сюда при переиспользовании шаблона ---
# RUN apt-get update && apt-get install -y --no-install-recommends <пакеты> \
#  && rm -rf /var/lib/apt/lists/*
#
# Python/Node-зависимости сюда не добавлять — они ставятся автоматически из
# pyproject.toml / package.json проекта через postCreateCommand (uv sync / npm install).

RUN useradd -ms /bin/bash dev \
 && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev

USER dev
WORKDIR /workspace
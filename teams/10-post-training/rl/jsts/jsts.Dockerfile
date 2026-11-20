# Sandbox image for the JavaScript and TypeScript verifier (jsts_verifier.py). Build once, with network:
#   docker build -f teams/10-post-training/rl/jsts/jsts.Dockerfile -t g10-jsts-rl:1 teams/10-post-training/rl/jsts
# Runs use --network=none. jest 29 with babel-jest; TypeScript is stripped by babel (types are not checked).
FROM node:22-slim
WORKDIR /work
RUN npm init -y >/dev/null \
    && npm install --no-audit --no-fund --save-dev jest@29.7.0 babel-jest@29.7.0 @babel/core@7.26.0 \
       @babel/preset-env@7.26.0 @babel/preset-typescript@7.26.0
COPY babel.config.cjs jest.config.cjs /work/
RUN useradd --create-home runner && mkdir -p /work/run && chown -R runner /work/run
USER runner

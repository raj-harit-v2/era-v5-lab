# Image for the JS verifier (js_verifier.py --sandbox docker):
#   docker build -f teams/10-post-training/rl/js/js.Dockerfile -t g10-js-rl:1 teams/10-post-training/rl/js
# Node.js 26 Active LTS (released 5 May 2026, LTS since 28 Oct 2026, EOL April 2029).
# No build step: the candidate's JS runs directly; no baked cache is needed.
# Pin the base image by digest before real training runs.
FROM node:26-alpine
ENV NODE_ENV=production
# Smoke-test the worker_threads module that the runner uses.
RUN node -e "require('worker_threads'); process.exit(0)"

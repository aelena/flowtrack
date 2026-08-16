FROM node:20-alpine

WORKDIR /app

# npm ci with the committed lockfile: reproducible installs. `npm install`
# resolved fresh versions on every build.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV PORT=3000
EXPOSE 3000

CMD ["node", "build"]

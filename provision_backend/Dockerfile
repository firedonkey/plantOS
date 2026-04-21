FROM node:22-slim

ENV NODE_ENV=production
ENV PORT=8080

WORKDIR /app

COPY package.json ./package.json
RUN npm install --omit=dev

COPY src ./src

EXPOSE 8080

CMD ["node", "src/app.js"]

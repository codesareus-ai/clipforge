# Frontend: Next.js + Remotion. `npm install` runs at build so Remotion can render.
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "dev"]

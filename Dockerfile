# Stage 1: Build
FROM node:22-alpine AS builder

# Build arguments for environment variables
ARG PUBLIC_GA_ID
ARG PUBLIC_ADSENSE_ID
ENV PUBLIC_GA_ID=$PUBLIC_GA_ID
ENV PUBLIC_ADSENSE_ID=$PUBLIC_ADSENSE_ID

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY . .

# Build Astro site (PUBLIC_ env vars are injected at build time)
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Cloud Run requires port 8080
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

# frontend/Dockerfile
FROM node:22-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy source code
# We will mount over this, but it's good practice
COPY . .

# Expose the React dev server port
EXPOSE 3000

# Start the dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
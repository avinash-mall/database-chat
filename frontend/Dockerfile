# Simple development server for frontend
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

EXPOSE 5173

# Run vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Use Rust official image
FROM rust:1.75 AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy project files
COPY . .

# Build the Rust application
RUN cargo build --release

# Create a smaller runtime image
FROM debian:bullseye-slim

# Install required dependencies
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the built binary from the builder stage
COPY --from=builder /app/target/release/automata-backend .

# Expose the port the application runs on
EXPOSE 8080

# Run the application
CMD ["./automata-backend"]

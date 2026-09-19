FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN go build -o /out/bot ./cmd/bot

FROM alpine:3.20
COPY --from=build /out/bot /usr/local/bin/bot
CMD ["bot"]

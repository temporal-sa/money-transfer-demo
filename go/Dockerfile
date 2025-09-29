FROM golang AS builder
ENV CGO_ENABLED=0
ENV GOOS=linux
ENV GOCACHE=/go/.cache
USER 1000
WORKDIR /go/app
COPY --chown=1000:1000 . .
RUN go build \
    -ldflags \
    "-w -s" \
    -o /go/bin/app ./worker
COPY --from=cosmtrek/air /go/bin/air /go/bin/air
ENTRYPOINT [ "air" ]
CMD [ "--build.cmd", "go build -o ./tmp/main ./worker" ]

FROM scratch
WORKDIR /app
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=builder /go/bin/app /app
ENTRYPOINT [ "/app/app" ]

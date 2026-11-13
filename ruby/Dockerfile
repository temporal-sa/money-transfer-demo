FROM ruby:3.4.12-alpine AS builder

RUN apk add --update \
  ruby-dev \
  build-base \
  openssl-dev

WORKDIR /app

COPY worker.rb ./
COPY activities ./activities
COPY models ./models
COPY security ./security
COPY workflows ./workflows
COPY Gemfile .

RUN bundle config set --global path ./gems
RUN bundle install

FROM ruby:3.4.12-alpine AS runner
WORKDIR /app

COPY --from=builder /app /app
RUN bundle config set --global path ./gems

ENV TEMPORAL_ADDRESS=temporal:7233
ENTRYPOINT [ "bundle", "exec", "ruby", "worker.rb" ]

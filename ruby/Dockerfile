FROM ruby:3.4.12-trixie
WORKDIR /app

COPY worker.rb ./
COPY activities ./activities
COPY models ./models
COPY security ./security
COPY workflows ./workflows
COPY Gemfile .

RUN bundle install

ENV TEMPORAL_ADDRESS=temporal:7233
ENTRYPOINT [ "bundle", "exec", "ruby", "worker.rb" ]

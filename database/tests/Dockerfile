FROM postgres:18-bookworm
ARG TARGETARCH
ADD https://github.com/supabase/pg_jsonschema/releases/download/v0.3.4/pg_jsonschema-v0.3.4-pg18-${TARGETARCH}-linux-gnu.deb /tmp/pg_jsonschema.deb
RUN dpkg -i /tmp/pg_jsonschema.deb && rm /tmp/pg_jsonschema.deb

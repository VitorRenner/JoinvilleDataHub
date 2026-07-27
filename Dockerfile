FROM ubuntu:latest
LABEL authors="vitaorenner"

ENTRYPOINT ["top", "-b"]
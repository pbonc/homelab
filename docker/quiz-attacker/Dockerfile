FROM curlimages/curl:8.16.0@sha256:5a91ea0c9c3ee27b4abe657b68cf6bf0676afa13b236b3bda34283cb3924d4f6

USER root
RUN apk add --no-cache bind-tools nmap
USER curl_user

ENTRYPOINT ["/bin/sh"]


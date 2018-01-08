# CloudFront serving S3 contents over HTTPS

## Create Bucket

    - Use non-URL name, e.g. `docs-futurice-com`

## Create distribution: Web
    - Origin Domain Name: *bucket*
    - Restrict Bucket Access: **Yes**
        - Create a New Identity
        - Yes, Update Bucket Policy
    - Redirect HTTP to HTTPS
    - GET, HEAD, OPTIONS
    - Cached HTTP Methods: OPTIONS
    - Alternate Domain Names (CNAMEs): *domain.futurice.com*
    - Custom SSL certificate
        - Request or Import a Certificate with ACM
        - When creating use Email validation
        - Wait for confirmation mail, click the link
    - Default Root Object: index.html

## Update DNS
